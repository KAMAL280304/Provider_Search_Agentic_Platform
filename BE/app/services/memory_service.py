"""
Memory Service — parses member conversation logs to build structured
cross-session context for the agent.

Reads from:
  logs/conversation/txt/  — conversation turns
  logs/conversation/txt/<member_id>_appointments.txt — confirmed bookings

Returns a context_block string the agent injects into its system prompt.
"""

import os
import re
from pathlib import Path

_CONV_DIR  = Path("logs/conversation/txt")
_APPT_SUFFIX = "_appointments.txt"


def load_member_memory(member_id: str) -> dict:
    """
    Parse all conversation logs for a member into structured context.
    Returns context_block (injected into agent prompt) + structured fields.
    """
    empty = {
        "has_history":        False,
        "context_block":      "",
        "appointments":       [],
        "specialties":        [],
        "symptoms":           [],
        "doctors_seen":       [],
        "dependents_treated": [],
        "last_session":       None,
        "total_sessions":     0,
    }

    # Collect all log files for this member
    if not _CONV_DIR.exists():
        return empty

    log_files = sorted(_CONV_DIR.glob(f"conv_{member_id}_*.txt"))
    appt_file = _CONV_DIR / f"{member_id}{_APPT_SUFFIX}"

    content = ""
    for f in log_files:
        try:
            content += f.read_text(encoding="utf-8") + "\n"
        except Exception:
            pass

    # Also read dedicated appointments log
    appt_content = ""
    if appt_file.exists():
        try:
            appt_content = appt_file.read_text(encoding="utf-8")
        except Exception:
            pass

    if not content.strip() and not appt_content.strip():
        return empty

    # ── Extract confirmed appointments ────────────────────────────────────────
    appointments = []
    seen_appts   = set()

    # From dedicated appointments log: "BOOKING CONFIRMED: Your In-Person appointment with Dr. X on May 1, 2026, from 10:30 AM PST"
    for m in re.finditer(
        r"BOOKING CONFIRMED: Your\s+\w+\s+appointment\s+with\s+(Dr\.[\w\s]+?)\s+on\s+"
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}),?\s+from\s+(\d{1,2}:\d{2}\s*(?:AM|PM))",
        appt_content, re.IGNORECASE
    ):
        doctor = m.group(1).strip().rstrip(".,")
        date   = m.group(2).strip()
        time   = m.group(3).strip()
        key    = f"{doctor}|{date}"
        if key not in seen_appts:
            seen_appts.add(key)
            appointments.append({"doctor": doctor, "date": date, "time": time})

    # From conversation logs: "Your In-Person appointment with Dr. X on May 1, 2026, from 10:30 AM"
    for m in re.finditer(
        r"Your\s+\w+\s+appointment\s+with\s+(Dr\.[\w\s]+?)\s+on\s+"
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}).*?(?:from\s+|at\s+)(\d{1,2}:\d{2}\s*(?:AM|PM))",
        content, re.IGNORECASE | re.DOTALL
    ):
        doctor = m.group(1).strip().rstrip(".,")
        date   = m.group(2).strip()
        time   = m.group(3).strip()
        key    = f"{doctor}|{date}"
        if key not in seen_appts:
            seen_appts.add(key)
            appointments.append({"doctor": doctor, "date": date, "time": time})

    # ── Extract specialties searched ──────────────────────────────────────────
    specialties = []
    seen_specs  = set()
    for m in re.finditer(
        r"(?:routed to|specialist for|searching for|found.*?specialist|"
        r"right specialist.*?is|specialty.*?is)\s+\*?\*?([A-Za-z\s&]+?)\*?\*?"
        r"(?:\s+specialist|\s+providers|\s+doctors|\.|,)",
        content, re.IGNORECASE
    ):
        spec = m.group(1).strip()
        if len(spec) > 3 and spec.lower() not in seen_specs:
            seen_specs.add(spec.lower())
            specialties.append(spec)

    # ── Extract symptoms from assistant messages ──────────────────────────────
    symptoms      = []
    seen_symptoms = set()
    symptom_kws   = [
        "headache", "head pain", "stomach pain", "stomach ache", "eye", "vision",
        "skin rash", "rash", "nerve pain", "back pain", "chest pain", "hand pain",
        "leg pain", "fever", "cough", "breathing", "heart", "ear", "throat",
        "knee", "shoulder", "joint", "anxiety", "depression", "diabetes",
        "blood pressure", "allergy", "asthma", "cancer", "tumor", "dizzy",
        "dizziness", "nausea", "fatigue", "swelling", "pain", "ache", "sore",
        "numbness", "tingling", "blurred", "itching", "redness", "vomiting",
        "insomnia", "sleep", "weight",
    ]
    # Extract from Patient lines in conversation logs
    for line in re.findall(r"Patient:\s*(.+)", content):
        line_lower = line.lower()
        for kw in symptom_kws:
            if kw in line_lower and kw not in seen_symptoms:
                seen_symptoms.add(kw)
                symptoms.append(kw)

    # ── Extract doctors shown in results ─────────────────────────────────────
    doctors_seen = []
    seen_docs    = set()
    for m in re.finditer(r"\*\*(Dr\.[\w][\w\s\-,.]+?)\*\*", content, re.MULTILINE):
        name = m.group(1).strip().rstrip(",.")
        name = re.sub(r",?\s+(?:MD|DO|FRCPC|DDS|NP|PA|RN|PhD)[\s,]*$", "", name, flags=re.IGNORECASE).strip()
        if name.lower() not in seen_docs and len(name) > 4:
            seen_docs.add(name.lower())
            doctors_seen.append(name)

    # ── Extract dependents treated ────────────────────────────────────────────
    dependents_treated = []
    seen_deps          = set()
    skip_words         = {"The", "You", "Any", "All", "Our", "Your", "This", "That",
                          "Here", "There", "Today", "Now", "Both", "Each", "Some"}
    for pat in [
        r"(?:help you find a doctor for|appointment for|found.*?for|search for)\s+([A-Z][a-z]{2,15})\b",
        r"Patient:\s+([A-Z][a-z]{2,15})\s+[A-Z]",
    ]:
        for m in re.finditer(pat, content, re.IGNORECASE):
            name = m.group(1).strip()
            if name not in skip_words and name.lower() not in seen_deps and len(name) > 2:
                seen_deps.add(name.lower())
                dependents_treated.append(name)

    # ── Session count ─────────────────────────────────────────────────────────
    session_dates = re.findall(r"SESSION START: (\d{4}-\d{2}-\d{2})", content)
    last_session  = session_dates[-1] if session_dates else None
    total_sessions = len(session_dates)

    # ── Build context block ───────────────────────────────────────────────────
    lines = []

    if appointments:
        lines.append("PAST APPOINTMENTS BOOKED:")
        for a in appointments[-5:]:
            lines.append(f"  - {a['doctor']} | {a['date']} at {a['time']}")

    if specialties:
        lines.append(f"SPECIALTIES SEARCHED BEFORE: {', '.join(specialties[:5])}")

    if symptoms:
        lines.append(f"SYMPTOMS/CONDITIONS MENTIONED BEFORE: {', '.join(symptoms[:10])}")

    if doctors_seen:
        lines.append(f"DOCTORS SHOWN IN SEARCH RESULTS: {', '.join(doctors_seen[:8])}")

    if dependents_treated:
        lines.append(f"DEPENDENTS TREATED: {', '.join(set(dependents_treated))}")

    if last_session:
        lines.append(f"LAST SESSION: {last_session} | TOTAL SESSIONS: {total_sessions}")

    context_block = "\n".join(lines) if lines else ""

    return {
        "has_history":        bool(lines),
        "context_block":      context_block,
        "appointments":       appointments,
        "specialties":        specialties,
        "symptoms":           symptoms,
        "doctors_seen":       doctors_seen,
        "dependents_treated": dependents_treated,
        "last_session":       last_session,
        "total_sessions":     total_sessions,
    }
