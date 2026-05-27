"""
Provider Search Agent — Google ADK + Vertex AI
Clean architecture: ADK is the only orchestrator.
No sub-agent LLM calls. All tools are pure Python functions.
History and bookings persisted via StorageService (local files or GCS).
"""

import asyncio
import json
import random
from typing import AsyncIterator

from app.config import settings
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai.types import Content, Part

from app.services.user_service import UserService
from app.services.storage_service import storage
from app.services.calendar_service import (
    check_provider_availability,
    get_urgent_slots,
    book_provider_appointment,
)
from app.services.memory_service import load_member_memory
from app.services.nucc_taxonomy_service import NUCCTaxonomyService
from app.tools.fhir_provider_tool import FHIRProviderTool
from app.tools.nppes_provider_tool import NPPESProviderTool
from app.tools.provider_ranking_tool import ProviderRankingTool
from app.app_logging.audit_logger import audit_logger

# ── Singletons ────────────────────────────────────────────────────────────────
_users        = UserService()
_nucc         = NUCCTaxonomyService()
_fhir_tool    = FHIRProviderTool()
_nppes_tool   = NPPESProviderTool()
_ranking_tool = ProviderRankingTool()
_adk_sessions: dict[str, str]   = {}
_runners:      dict[str, Runner] = {}

# ── Plan rules ────────────────────────────────────────────────────────────────
_PLAN_RULES = {
    "cigna true choice medicare (ppo)": {
        "requires_referral": False, "prior_auth_required": False,
        "deductible": "$0", "oop_max": "$3,400/year",
        "specialist_copay": "$20", "pcp_copay": "$0", "telehealth_copay": "$0",
        "notes": "No referral needed. Largest network. Telehealth covered at $0.",
    },
    "cigna true choice access medicare (ppo)": {
        "requires_referral": False, "prior_auth_required": False,
        "deductible": "$100", "oop_max": "$4,500/year",
        "specialist_copay": "$35", "pcp_copay": "$5", "telehealth_copay": "$0",
        "notes": "No referral needed. Broad PPO network.",
    },
    "cigna total care plus (hmo d-snp)": {
        "requires_referral": True, "prior_auth_required": True,
        "deductible": "$0", "oop_max": "$2,000/year",
        "specialist_copay": "$45", "pcp_copay": "$10", "telehealth_copay": "$0",
        "notes": "PCP referral required for specialists. Prior auth for imaging/surgery.",
    },
    "cigna total care (hmo d-snp)": {
        "requires_referral": True, "prior_auth_required": True,
        "deductible": "$0", "oop_max": "$2,500/year",
        "specialist_copay": "$50", "pcp_copay": "$10", "telehealth_copay": "$5",
        "notes": "PCP referral required. Prior auth for specialist visits.",
    },
    "cigna preferred medicare (hmo)": {
        "requires_referral": True, "prior_auth_required": False,
        "deductible": "$200", "oop_max": "$5,500/year",
        "specialist_copay": "$55", "pcp_copay": "$15", "telehealth_copay": "$10",
        "notes": "PCP referral required. Smaller network — in-network only.",
    },
}

def _get_plan_rules(insurance_plan: str) -> dict:
    return _PLAN_RULES.get(insurance_plan.lower().strip(), {
        "requires_referral": False, "prior_auth_required": False,
        "deductible": "Unknown", "oop_max": "Unknown",
        "specialist_copay": "Unknown", "pcp_copay": "Unknown",
        "telehealth_copay": "Unknown", "notes": "Plan details not available.",
    })


# ── Proactive context builder ─────────────────────────────────────────────────
def _build_proactive_block(user_id: str, first_name: str, dry_run: bool = False) -> str:
    """
    Reads all storage files for this member and returns a block that tells
    the agent exactly what pending items exist and what to proactively address
    on the VERY FIRST response of a new session — before the user asks anything.
    Returns empty string if nothing is pending.

    dry_run=True: reads state but does NOT mark any flags as consumed.
    Use this when building the system prompt context (so the real
    __session_start__ call can still see and consume the flags).
    """
    items = []

    # ── MRI prescription + prior auth ────────────────────────────────────────
    try:
        mri_rx     = storage.get_mri_prescription(user_id)
        prior_auth = storage.get_prior_auth(user_id)
        bookings   = storage.get_bookings(user_id)

        if mri_rx and mri_rx.get("prescription_mri"):
            prescribed_by = mri_rx.get("prescribed_by", {})
            doc_name  = prescribed_by.get("name", "your specialist") if isinstance(prescribed_by, dict) else str(prescribed_by)
            body_part = mri_rx.get("body_part") or mri_rx.get("procedure") or "MRI"
            reason    = mri_rx.get("reason", "")
            pa_status = (prior_auth or {}).get("status", "none")
            pa_ref    = (prior_auth or {}).get("auth_reference_number", "")
            pa_date   = (prior_auth or {}).get("submitted_date", "")
            pa_valid  = (prior_auth or {}).get("valid_through", "")

            # ── Cross-reference: is there already an imaging/scan booking? ──
            # Presence of mri_prescription on file = doctor visit already physically happened.
            # The prescription was given by the provider dashboard — doctor visit is DONE.
            # We must NOT treat the upcoming booking as a "go see the doctor" appointment.
            _MRI_KEYWORDS = {"mri", "scan", "imaging", "radiology", "x-ray", "ct", "pet"}
            imaging_booking = None
            for b in bookings:
                b_reason = (b.get("reason") or "").lower()
                b_provider = (b.get("provider_name") or "").lower()
                if any(kw in b_reason or kw in b_provider for kw in _MRI_KEYWORDS):
                    imaging_booking = b
                    break

            if imaging_booking:
                # Doctor visit is DONE. Prescription is on file. Scan is booked.
                # Agent must reflect reality: visit happened, scan scheduled, just track auth.
                scan_provider = imaging_booking.get("provider_name", "the imaging center")
                scan_date     = imaging_booking.get("date", "")
                scan_time     = imaging_booking.get("time_start", "")
                scan_when     = f"{scan_date} at {scan_time}".strip(" at") if scan_date else "your scheduled date"

                if pa_status == "none":
                    items.append(
                        f"MRI_VISIT_DONE_AUTH_MISSING: {first_name} already visited {doc_name} and received "
                        f"the MRI prescription for {body_part} ({reason}). The doctor visit is COMPLETE — "
                        f"do NOT suggest {first_name} needs to see the prescribing doctor again. "
                        f"The scan is booked with {scan_provider} on {scan_when}. "
                        f"However prior authorization has NOT been submitted yet. "
                        f"On your first response: tell {first_name} their prescription is ready and scan is booked, "
                        f"then immediately call notify_provider targeting {doc_name}'s office with "
                        f"notification_type='prior_auth_request' to kick off the auth, "
                        f"then say: 'Everything is lined up — I've just notified Dr. [doc]'s office to submit "
                        f"the prior auth to Cigna. Once it clears (2-5 business days), you're all set for your scan.'"
                    )
                elif pa_status == "pending":
                    items.append(
                        f"MRI_VISIT_DONE_AUTH_PENDING: {first_name} already visited {doc_name} and received "
                        f"the MRI prescription for {body_part}. The doctor visit is COMPLETE — "
                        f"do NOT suggest {first_name} needs to see the prescribing doctor again. "
                        f"The scan is booked with {scan_provider} on {scan_when}. "
                        f"Prior auth was submitted on {pa_date} and is currently PENDING Cigna approval "
                        f"(Ref# {pa_ref}). "
                        f"On your first response: acknowledge everything is in motion naturally — "
                        f"'Good news — you've already got your prescription from Dr. [doc], your scan is booked "
                        f"with {scan_provider} on {scan_when}, and the prior auth is with Cigna right now (Ref# {pa_ref}). "
                        f"Just waiting on their approval — usually 2-5 business days from submission.' "
                        f"Do NOT call notify_provider (already submitted). Do NOT offer to book again."
                    )
                elif pa_status == "approved":
                    items.append(
                        f"MRI_VISIT_DONE_AUTH_APPROVED: {first_name} already visited {doc_name} and received "
                        f"the MRI prescription for {body_part}. The doctor visit is COMPLETE — "
                        f"do NOT suggest {first_name} needs to see the prescribing doctor again. "
                        f"The scan is booked with {scan_provider} on {scan_when}. "
                        f"Prior auth is APPROVED by Cigna (Ref# {pa_ref}, valid through {pa_valid}). "
                        f"On your first response: deliver the great news — "
                        f"'Everything is confirmed, {first_name}! Your prescription is done, Cigna approved the auth "
                        f"(Ref# {pa_ref}, valid through {pa_valid}), and your scan with {scan_provider} is booked "
                        f"for {scan_when}. You are all set — just show up!' "
                        f"Do NOT call notify_provider. Do NOT offer to book again."
                    )
                elif pa_status == "declined":
                    items.append(
                        f"MRI_VISIT_DONE_AUTH_DECLINED: {first_name} already visited {doc_name} and received "
                        f"the MRI prescription for {body_part}. The doctor visit is COMPLETE. "
                        f"The scan was booked with {scan_provider} on {scan_when} but Cigna DECLINED the prior auth. "
                        f"On your first response: tell {first_name} clearly — 'You've got your prescription from "
                        f"Dr. [doc] and the scan is booked, but Cigna declined the prior auth. Here's what we can do: "
                        f"1) Appeal the decision — I can notify Dr. [doc]'s office to file an appeal, or "
                        f"2) We explore if there's an alternative imaging option Cigna will cover.' "
                        f"Ask which they'd prefer, then act immediately."
                    )

            else:
                # No imaging booking yet — standard flow, offer to find and book
                if pa_status == "none":
                    items.append(
                        f"MRI_PENDING_AUTH: {first_name} has an MRI prescription on file "
                        f"(ordered by {doc_name} for {body_part} — {reason}). "
                        f"The prior authorization has NOT been submitted yet. "
                        f"⚠️ CRITICAL OVERRIDE: The doctor visit for this issue is ALREADY DONE. "
                        f"Do NOT search for doctors, do NOT suggest seeing a specialist again, do NOT show provider cards for {body_part}. "
                        f"The ONLY next step is to get the prior auth submitted. "
                        f"On your FIRST response: tell {first_name} you see their MRI prescription from {doc_name} for {body_part} ({reason}). "
                        f"Immediately call notify_provider targeting {doc_name}'s office with notification_type='prior_auth_request'. "
                        f"Then tell {first_name}: 'I've just sent {doc_name}'s office a reminder to submit the prior auth to Cigna — "
                        f"these usually clear in 2-5 business days. The moment it comes through, I'll get your scan booked right away.' "
                        f"If {first_name} THEN mentions {body_part} symptoms again (e.g. knee hurts, knee pain), "
                        f"do NOT start a new provider search — instead say: "
                        f"'You already have an MRI prescription from {doc_name} for your {body_part} — "
                        f"we're just waiting on Cigna's sign-off before booking the scan. No need to see another doctor.'"
                    )
                elif pa_status == "pending":
                    items.append(
                        f"MRI_AUTH_PENDING: {first_name} has an MRI prescription on file "
                        f"(ordered by {doc_name} for {body_part}). "
                        f"Prior auth was submitted on {pa_date} and is currently PENDING Cigna approval "
                        f"(Ref# {pa_ref}). "
                        f"⚠️ CRITICAL OVERRIDE: The doctor visit is ALREADY DONE. "
                        f"Do NOT search for new doctors. Do NOT suggest another appointment for {body_part}. "
                        f"On your first response, proactively update {first_name}: "
                        f"'Your prescription from {doc_name} is all set — Cigna is reviewing the prior auth right now "
                        f"(Ref# {pa_ref}, submitted {pa_date}). These usually clear in 2-5 business days. "
                        f"I'll notify you the moment it's approved so we can book the scan.' "
                        f"If {first_name} mentions {body_part} symptoms again, remind them the prescription is on file and auth is pending — "
                        f"do NOT launch another doctor search."
                    )
                elif pa_status == "approved":
                    items.append(
                        f"MRI_AUTH_APPROVED: {first_name} has an MRI prescription on file "
                        f"(ordered by {doc_name} for {body_part}). "
                        f"Prior auth is APPROVED by Cigna (Ref# {pa_ref}, valid through {pa_valid}). "
                        f"⚠️ CRITICAL OVERRIDE: The doctor visit is DONE. Do NOT search for new doctors or specialists. "
                        f"On your FIRST response: tell {first_name} the great news — their Cigna prior auth for the {body_part} MRI "
                        f"has been approved (Ref# {pa_ref}, valid through {pa_valid}). "
                        f"Then ask: 'Would you like me to find an imaging center and book the scan now?' "
                        f"WAIT for their reply before calling any tools. Do NOT auto-call find_providers."
                    )
                elif pa_status == "declined":
                    items.append(
                        f"MRI_AUTH_DECLINED: {first_name} has an MRI prescription on file "
                        f"(ordered by {doc_name} for {body_part}). "
                        f"Prior auth was DECLINED by Cigna. "
                        f"⚠️ CRITICAL OVERRIDE: The doctor visit is DONE. Do NOT suggest a new doctor visit. "
                        f"On your first response: proactively inform {first_name} and explain next steps "
                        f"(appeal the decision or explore alternative imaging options Cigna will cover)."
                    )
    except Exception:
        pass

    # ── Referral status from provider dashboard ───────────────────────────────
    try:
        referral = storage.get_referral(user_id)
        if referral and referral.get("status") == "approved":
            specialist    = referral.get("specialist", "the specialist")
            approved_by   = referral.get("approved_by", "your PCP")
            approved_date = referral.get("approved_date", "")
            valid_through = referral.get("valid_through", "")
            ref_reason    = referral.get("reason", "")
            # Check if a specialist booking already exists for this referral
            _existing_specialist_booking = None
            for _b in storage.get_bookings(user_id):
                _b_reason = (_b.get("reason") or "").lower()
                _b_prov   = (_b.get("provider_name") or "").lower()
                _spec_lc  = specialist.lower()
                if any(kw in _b_reason or kw in _b_prov for kw in _spec_lc.split()):
                    _existing_specialist_booking = _b
                    break

            if not _existing_specialist_booking:
                items.append(
                    f"REFERRAL_APPROVED: {first_name}'s PCP ({approved_by}) has referred them to see a {specialist} "
                    f"(approved {approved_date}, valid through {valid_through}"
                    + (f", reason: {ref_reason}" if ref_reason else "")
                    + f"). The referral is fully cleared.\n"
                    f"On your FIRST response: warmly tell {first_name} the referral came through from {approved_by} "
                    f"and ask: 'Would you like me to find a {specialist} near you now?' "
                    f"WAIT for their reply before calling any tools. Do NOT auto-search or call find_providers."
                )
    except Exception:
        pass

    # ── PCP change status ─────────────────────────────────────────────────────
    try:
        pcp_changes = storage.read(f"pcp_changes/{user_id}.json") or []
        for c in pcp_changes:
            if c.get("status") == "pending":
                items.append(
                    f"PCP_CHANGE_PENDING: {first_name} submitted a PCP change request to "
                    f"{c.get('new_pcp_name', 'a new doctor')} which is currently pending Cigna approval. "
                    f"Proactively mention this status if relevant to the conversation."
                )
            elif c.get("status") == "completed" and not c.get("_proactive_shown"):
                items.append(
                    f"PCP_CHANGE_COMPLETED: {first_name}'s PCP has been updated to "
                    f"{c.get('new_pcp_name', 'a new doctor')} — Cigna approved the change. "
                    f"Proactively congratulate {first_name} and confirm the new PCP details."
                )
    except Exception:
        pass

    # ── MRI Required flag set by provider on specialist bookings ─────────────
    try:
        bookings_all = storage.get_bookings(user_id)
        for b in bookings_all:
            if b.get("mri_required") and b.get("status") == "completed":
                _spec_name = b.get("provider_name", "your specialist")
                _b_reason  = b.get("reason", "")
                _b_date    = b.get("date", "")
                items.append(
                    f"MRI_REQUIRED_FLAG: The specialist ({_spec_name}) you saw on {_b_date} "
                    f"has indicated that an MRI scan is required"
                    + (f" related to: {_b_reason}" if _b_reason else "")
                    + f". The provider has flagged this in the system. "
                    f"On your FIRST response: let {first_name} know that {_spec_name} has recommended an MRI. "
                    f"Ask: 'Would you like me to help get a prescription started and find an imaging center?' "
                    f"WAIT for their reply before calling any tools."
                )
                break  # only surface one at a time
    except Exception:
        pass

    # ── Plan change payer decision ────────────────────────────────────────────
    try:
        plan_change = storage.read(f"plan_change/{user_id}.json")
        if plan_change and plan_change.get("payer_decision") and not plan_change.get("_payer_proactive_shown"):
            decision = plan_change["payer_decision"]
            new_plan_name  = plan_change.get("new_plan", "")
            prev_plan_name = plan_change.get("previous_plan", "")
            # Determine new plan's key rules for context
            _new_rules = _get_plan_rules(new_plan_name) if new_plan_name else {}
            _requires_ref = _new_rules.get("requires_referral", False)
            _pcp_copay    = _new_rules.get("pcp_copay", "")
            _spec_copay   = _new_rules.get("specialist_copay", "")
            if decision == "approved":
                items.append(
                    f"PLAN_CHANGE_APPROVED: Cigna has approved {first_name}'s request to switch "
                    f"from '{prev_plan_name}' to '{new_plan_name}'. "
                    f"New plan key rules — referral required: {_requires_ref}, "
                    f"PCP copay: {_pcp_copay}, specialist copay: {_spec_copay}. "
                    f"On your FIRST response: deliver the good news warmly. "
                    f"Mention 1-2 key changes that affect {first_name} (e.g. referral requirement, copay change). "
                    f"If {first_name} has any existing bookings, silently call find_providers on each doctor "
                    f"to check if they are still in-network under '{new_plan_name}' and surface any issues."
                )
            elif decision == "declined":
                items.append(
                    f"PLAN_CHANGE_DECLINED: Cigna has declined {first_name}'s request to switch plans. "
                    f"They remain on '{prev_plan_name}'. "
                    f"On your FIRST response: let {first_name} know gently, explain they're still on their "
                    f"current plan, and offer to help them choose a different plan or explore what's available."
                )
            # Mark as shown so it doesn't fire again — keep file until payer_decision is set
            if not dry_run:
                plan_change["_payer_proactive_shown"] = True
                storage.write(f"plan_change/{user_id}.json", plan_change)
    except Exception:
        pass

    if not items:
        return ""

    lines = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(items))
    return f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROACTIVE ACTIONS REQUIRED — READ BEFORE RESPONDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You have already reviewed {first_name}'s file. The following items are pending
and MUST be addressed proactively — do NOT wait for {first_name} to bring them up.
Address ALL of them naturally in your FIRST response, regardless of what {first_name} says.
Behave like a healthcare assistant who has already read the file before the patient walked in.

{lines}

IMPORTANT:
- Weave these naturally into your greeting — do not list them robotically
- If {first_name} says something unrelated (e.g. "I have a headache"), STILL address
  the pending items first, then handle their new request
- After addressing these items once, do not repeat them unless {first_name} asks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


# ── System prompt builder ─────────────────────────────────────────────────────
def _build_system_prompt(user_id: str, travel_city: str = "", travel_state: str = "") -> str:
    try:
        user = _users.get_user(user_id)
    except Exception:
        return "You are a compassionate healthcare assistant. Help members find the right doctor."

    plan_rules = _get_plan_rules(user.insurance_plan)
    memory     = load_member_memory(user_id)
    mh         = user.medical_history

    # Load bookings from storage
    bookings      = storage.get_bookings(user_id)
    # Pre-load MRI prescription so we can annotate imaging bookings correctly
    _mri_rx_for_booking    = storage.get_mri_prescription(user_id)
    _prior_auth_for_booking = storage.get_prior_auth(user_id)
    _MRI_KW = {"mri", "scan", "imaging", "radiology", "x-ray", "ct", "pet"}
    booking_block = ""
    if bookings:
        booking_block = "\nBOOKINGS MADE THROUGH THIS APP:"
        for b in bookings[-5:]:
            reason_str = f" for {b['reason']}" if b.get('reason') else ""
            b_reason_lc = (b.get("reason") or "").lower()
            b_prov_lc   = (b.get("provider_name") or "").lower()
            is_imaging  = any(kw in b_reason_lc or kw in b_prov_lc for kw in _MRI_KW)
            if is_imaging and _mri_rx_for_booking and _mri_rx_for_booking.get("prescription_mri"):
                pa_st = (_prior_auth_for_booking or {}).get("status", "none")
                rx_doc = (_mri_rx_for_booking.get("prescribed_by") or {}).get("name", "specialist")
                booking_block += (
                    f"\n  - {b.get('provider_name')} on {b.get('date')} at "
                    f"{b.get('time_start')} ({b.get('consultation_type', '')}){reason_str}"
                    f"  ← SCAN APPOINTMENT [prescription already given by {rx_doc}; prior_auth={pa_st}; "
                    f"prescribing doctor visit is COMPLETE — do NOT treat this booking as a doctor consult]"
                )
            else:
                booking_block += (
                    f"\n  - {b.get('provider_name')} on {b.get('date')} at "
                    f"{b.get('time_start')} ({b.get('consultation_type', '')}){reason_str}"
                )
    else:
        booking_block = "\nBOOKINGS MADE THROUGH THIS APP: None yet."

    dep_lines = ""
    if user.dependents:
        dep_lines = "\nDEPENDENTS ON THIS PLAN:\n" + "\n".join(
            f"  - {d['name']} ({d['relationship']}, DOB: {d['date_of_birth']})"
            for d in user.dependents
        )

    pcp_block = ""
    if user.assigned_pcp:
        pcp = user.assigned_pcp
        pcp_block = (
            f"\nASSIGNED PCP:"
            f"\n  Name:     {pcp.get('name', '')}"
            f"\n  NPI:      {pcp.get('npi', '')}"
            f"\n  Specialty:{pcp.get('specialty', '')}"
            f"\n  Address:  {pcp.get('address', '')}"
            f"\n  Phone:    {pcp.get('phone', '')}"
        )

    memory_block = ""
    if memory["has_history"]:
        memory_block = f"\nMEMBER HISTORY (from past sessions):\n{memory['context_block']}"

    # Load history summary from storage (long-term profile + recent summaries)
    history_summary = storage.get_history_summary(user_id)
    history_summary_block = ""
    if history_summary:
        history_summary_block = f"\n{history_summary}"
    
    # ── MRI Prescription + Prior Auth block ─────────────────────────────────
    mri_block = ""
    try:
        mri_rx     = storage.get_mri_prescription(user_id)
        prior_auth = storage.get_prior_auth(user_id)

        if mri_rx and mri_rx.get("prescription_mri"):
            doc_name  = mri_rx.get("prescribed_by", {}).get("name", "your specialist")
            doc_spec  = mri_rx.get("prescribed_by", {}).get("specialty", "")
            body_part = mri_rx.get("body_part", "")
            rx_reason = mri_rx.get("reason", "")
            rx_date   = mri_rx.get("prescribed_date", "")

            mri_block = (
                f"\nMRI PRESCRIPTION ON FILE:"
                f"\n  Ordered by: {doc_name}{' (' + doc_spec + ')' if doc_spec else ''}"
                f"\n  Procedure:  MRI — {body_part}"
                f"\n  Reason:     {rx_reason}"
                f"\n  Date:       {rx_date}"
                f"\n  IMPORTANT: The ordering physician for this MRI is exclusively {doc_name}."
                f"\n  Always use this exact name for notify_provider calls."
                f"\n  Never substitute with any doctor from MEDICAL HISTORY or PAST APPOINTMENTS."
            )

            if prior_auth:
                pa_status   = prior_auth.get("status", "none")
                pa_ref      = prior_auth.get("auth_reference_number", "")
                pa_sub_by   = prior_auth.get("submitted_by", doc_name)
                pa_sub_date = prior_auth.get("submitted_date", "")
                pa_app_date = prior_auth.get("approved_date", "")
                pa_valid    = prior_auth.get("valid_through", "")
                pa_payer    = prior_auth.get("payer", "Cigna")

                if pa_status == "none":
                    mri_block += "\n  Prior Auth: Not yet submitted."
                elif pa_status == "pending":
                    mri_block += (
                        f"\n  Prior Auth: PENDING — awaiting {pa_payer} approval"
                        + (f"\n    Submitted by:  {pa_sub_by}'s office" if pa_sub_by else "")
                        + (f"\n    Submitted on:  {pa_sub_date}" if pa_sub_date else "")
                        + (f"\n    Ref#:          {pa_ref}" if pa_ref else "")
                    )
                elif pa_status == "approved":
                    mri_block += (
                        f"\n  Prior Auth: APPROVED by {pa_payer}"
                        + (f"\n    Ref#:          {pa_ref}" if pa_ref else "")
                        + (f"\n    Approved on:   {pa_app_date}" if pa_app_date else "")
                        + (f"\n    Valid through: {pa_valid}" if pa_valid else "")
                    )
            else:
                mri_block += "\n  Prior Auth: Not yet submitted."
    except Exception:
        mri_block = ""
    # ─────────────────────────────────────────────────────────────────────────

    # Plan change context — only injected on first session after plan change
    plan_change = storage.get_and_clear_plan_change(user_id)
    plan_change_block = ""
    if plan_change:
        previous_plan = plan_change["previous_plan"]
        plan_change_block = f"""

        PLAN CHANGE DETECTED — first session after plan change:
        Previous Plan: {previous_plan}
        New Plan:      {user.insurance_plan}

        ⚠️ IMMEDIATE ACTION REQUIRED ON THIS SESSION:

        1. UPCOMING BOOKINGS — CHECK FIRST BEFORE RESPONDING:
        Look at BOOKINGS MADE THROUGH THIS APP right now.
        If there are any bookings listed:
        → Your VERY FIRST response must acknowledge the plan change and flag the booking.
        → Naturally weave it into your greeting — do not wait for the member to ask.
        → Then silently call find_providers with that doctor's name to check network status
            under the new plan, and tell the member the result in the same response.
        → If out-of-network: offer to find an in-network alternative.
        → If still in-network: reassure them warmly.
        If there are no bookings: skip this step entirely.

        2. PAST DOCTORS — ACT WHEN MENTIONED:
        If {user.first_name} mentions any doctor from MEDICAL HISTORY,
        silently call find_providers with that doctor_name to check network status.
        - Out-of-network → tell them naturally, offer in-network alternative
        - Still in-network → confirm warmly: "Good news — Dr. X is still covered."

        3. PLAN RULES — ENFORCE IMMEDIATELY:
        New plan rules are already in PLAN BENEFITS above.
        Apply them from this moment — referral, prior auth, copays all follow {user.insurance_plan}.
        If previous plan had no referral and new plan requires one, surface it the first
        time a specialist is mentioned.
        NOTE: If the user's message is exactly "__plan_change_greeting__", treat it as a silent 
        system trigger. Do NOT echo or reference that text. Just deliver your proactive 
        plan-change greeting naturally as if you initiated it.
        Do NOT mention the plan change again after this session. Behave completely normally."""




    # ── Proactive block — built from storage, injected into prompt ──────────
    proactive_block = _build_proactive_block(user_id, user.first_name, dry_run=True)
    # ─────────────────────────────────────────────────────────────────────────

    med_block = ""
    if mh.get("conditions"):
        med_block += f"\nMEDICAL HISTORY:"
        med_block += f"\n  Conditions:    {', '.join(mh['conditions'])}"
    if mh.get("allergies"):
        med_block += f"\n  Allergies:     {', '.join(mh['allergies'])}"
    if mh.get("current_medications"):
        med_block += f"\n  Medications:   {', '.join(mh['current_medications'])}"
    if mh.get("past_appointments"):
        med_block += f"\n  Past Doctors:"
        seen = set()
        for a in mh["past_appointments"]:
            key = a.get("npi", a.get("doctor_name", ""))
            if key not in seen:
                seen.add(key)
                med_block += (
                    f"\n    - {a['doctor_name']} ({a['specialty']}) — "
                    f"{a['visit_count']} visit(s), last: {a['date']}, reason: {a['reason']}"
                )

    referral_note = (
        f"REQUIRES a PCP referral before seeing a specialist. "
        f"Member's assigned PCP is {user.assigned_pcp.get('name', 'their PCP')} "
        f"(NPI: {user.assigned_pcp.get('npi', '')})."
        if plan_rules["requires_referral"]
        else "No referral required — member can book specialists directly."
    )

    prior_auth_note = (
        "Prior authorization required for imaging, surgery, and specialist visits."
        if plan_rules["prior_auth_required"]
        else "No prior authorization required for standard specialist visits."
    )

    # ── MEM-10005 dedicated prompt — short, zero hallucination room ─────────
    if user_id == "MEM-10005":
        _pcp      = user.assigned_pcp or {}
        _pcp_name = _pcp.get("name", "Dr. Estefania Abasolo Lopez")
        _pcp_npi  = _pcp.get("npi", "1043899545")
        _is_travel = bool(travel_city.strip())
        _cur_loc   = f"{travel_city}, {travel_state}" if _is_travel else f"{user.default_city}, {user.default_state}"
        return f"""You are a warm, proactive healthcare concierge for Medilife Healthcare speaking with David Chen (MEM-10005).

DAVID'S PLAN: Cigna Preferred Medicare (HMO) — PCP referral required before ANY specialist.
DAVID'S PCP: {_pcp_name} (NPI: {_pcp_npi}), based in Chicago, IL
DAVID'S HOME: Chicago, IL
DAVID'S CURRENT LOCATION: {_cur_loc}{"  ← TRAVELLING" if _is_travel else ""}
DAVID'S CONDITIONS: GERD, Knee Osteoarthritis (right)
DAVID'S PAST DOCTORS: Dr. Sindhu Abraham (Gastroenterology), Dr. Cody Anderson (Orthopaedic Surgery)
{booking_block}

HMO RULE — ABSOLUTE, NO EXCEPTIONS FOR ANY SYMPTOM:
David is on HMO. He CANNOT see any specialist without a PCP referral. No referral is on file.
This applies even if he has seen Dr. Cody Anderson or Dr. Sindhu Abraham before — HMO still requires PCP first.

FOR EVERY SYMPTOM David mentions (back pain, leg pain, knee pain, stomach pain, anything):
  STEP 1 — Ask ONE empathetic follow-up question like a friend — NOT a pain scale. Ask naturally:
    e.g. "How long has it been going on?" or "Is it sharp or more of a dull ache?" or "Is it making it hard to move around?"
    STOP here. Wait for David's reply. Do NOT call any tools yet.
  STEP 2 — After David replies, respond warmly (adapt to his actual symptom) then IMMEDIATELY call the tools:
    Say: "That sounds uncomfortable, David — definitely worth getting checked out properly.
     With your plan, the first step is a quick visit with your primary care doctor before seeing a specialist.
     {'Since you are in ' + _cur_loc + ' and Dr. ' + _pcp_name.split()[-1] + ' is based in Chicago, I will set up a Telehealth slot so you do not have to travel back — let me pull up her availability.' if _is_travel else 'Let me pull up Dr. ' + _pcp_name.split()[-1] + "'s next available time right now."}"
  STEP 3 — Call find_providers(specialty='Primary Care', doctor_name='{_pcp_name}', user_id='MEM-10005')
  STEP 4 — Call check_availability on the result immediately after find_providers returns
  STEP 5 — Show the {'Telehealth ' if _is_travel else ''}time slots naturally and ask: "Which of these works for you, David?"

NEVER search for specialists. NEVER show specialist cards. NEVER use continuity of care exception.
Emergency symptoms (chest pain + sweating, stroke signs) → tell David to call 911 immediately.

Tone: warm, human, proactive. Use David's first name. Plain language only — no insurance jargon."""
    # ─────────────────────────────────────────────────────────────────────────

    return f"""You are a sharp, proactive healthcare concierge for Medilife Healthcare.
You are speaking with {user.first_name} {user.last_name} (Member ID: {user.member_id}).
Think of yourself as a knowledgeable friend who understands medicine, insurance, and how to get things done fast.
{user.first_name} may not know what kind of doctor they need or how insurance works — that's exactly why they're here. You handle it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMBER CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Name:         {user.first_name} {user.last_name}
  Age:          {user.age}
  Phone:        {user.phone}
  Home City:    {user.default_city}, {user.default_state}
  Current City: {travel_city + ", " + travel_state if travel_city else user.default_city + ", " + user.default_state}{"  ← TRAVELLING" if travel_city else ""}
  ZIP:          {user.zip_code}
  Insurance:    {user.payer_name} — {user.insurance_plan}
  Member Since: {user.member_since}
  PCP Copay:    {plan_rules['pcp_copay']} | Specialist: {plan_rules['specialist_copay']} | Telehealth: {plan_rules['telehealth_copay']}
  Deductible:   {plan_rules['deductible']} | OOP Max: {plan_rules['oop_max']}
  Referral:     {referral_note}
  Prior Auth:   {prior_auth_note}
  Plan Notes:   {plan_rules['notes']}{dep_lines}{pcp_block}{med_block}{booking_block}{history_summary_block}{memory_block}{plan_change_block}{mri_block}{proactive_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR DECISION AUTHORITY — THE CORE RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE GOLDEN RULE:
  If you have enough to act → ACT immediately. Do not narrate your plan. Do not ask "Should I?".
  If you genuinely need one specific piece of info to proceed → ask exactly ONE targeted question. Then act.

YOU DECIDE — NEVER ASK {user.first_name} ABOUT THESE:
  ✓ Which medical specialty they need (you reason from symptoms + history)
  ✓ Routine vs urgent vs emergency (you assess from what they describe)
  ✓ In-Person vs Telehealth (clinical judgment — see CARE TYPE below)
  ✓ Whether prior auth or referral applies (you know their plan)
  ✓ Which provider to recommend (top_pick from results)
  ✓ Whether to check availability after finding providers (always yes)
  ✓ Whether to check the next day if today is empty (always yes, silently)

ONLY {user.first_name} CAN DECIDE — THE ONLY MOMENTS YOU PAUSE:
  ✓ Which time slot they prefer (after you show real options from check_availability)
  ✓ Which insurance plan to switch to (after you explain the choices)
  ✓ Whether to proceed with an out-of-network doctor or find an in-network alternative

THE AUTONOMOUS TOOL CHAIN — DO THIS WITHOUT ASKING:
  1. Specialty identified → determine plan type first (PPO vs HMO) — this changes EVERYTHING
  2. PPO plan → book specialist directly: find_providers → check_availability → book_appointment
  3. HMO plan → MUST go through PCP first: find_providers(PCP) → check_availability → book PCP → STOP
     The PCP sees the member, then raises the referral. Specialist cannot be booked before that visit.
  4. HMO + referral IS approved → full specialist chain: find_providers(specialist) → check_availability → book_appointment
  5. Specialist orders MRI → specialist raises prior auth (NOT the agent, NOT the PCP)
     The agent's role: inform member, show imaging centers, wait for payer approval
  6. Prior auth approved → find imaging center: find_providers(Radiology) → check_availability → book_appointment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — SYMPTOM TRIAGE: USE WHAT YOU KNOW FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 RULE ZERO — CHECK MRI PRESCRIPTION ON FILE BEFORE ANYTHING ELSE 🚨
  Before doing ANY symptom triage or provider search, look at MRI PRESCRIPTION ON FILE in MEMBER CONTEXT.
  If a prescription exists AND the body_part matches what the member is describing:
    → The clinical journey for that issue is ALREADY past the "see a doctor" stage.
    → Do NOT search for doctors. Do NOT suggest another specialist. Do NOT show provider cards.
    → Instead: tell the member about the prescription and give them the prior auth status.
    → Then take the EXACT action dictated by that status (see PRIOR AUTHORIZATION section below).

  EXAMPLES OF THIS RULE IN ACTION:
  ✅ Prescription on file: "Right Knee" — member says "my knee still hurts":
     → "I can see Dr. [specialist] already wrote you a prescription for an MRI of your right knee.
        We're just waiting on Cigna's sign-off before booking your scan — no need to see another doctor."
     → Then immediately handle the prior auth status (remind office / show imaging centers / book scan).
  ✅ Prescription on file: "Lower Back" — member says "my back pain hasn't improved":
     → Same — surface the prescription, don't start a new provider search.
  ❌ NEVER do this when a prescription is on file for that body part:
     find_providers("Orthopaedic Surgery") or find_providers("Primary Care") for that same symptom.

BEFORE asking anything, scan the MEMBER CONTEXT above:
  → Do their conditions, medications, or past doctors already answer this? → Use it, act on it.
  → Have they seen a relevant specialist before? → Call find_providers with that doctor_name.
  → Is the specialty obvious from what they said? → Act immediately, no questions.

WHEN YOU ACT WITHOUT ANY QUESTION:
  "I have a rash" → Dermatology
    PPO: find_providers(Dermatology) → check_availability → book
    HMO with no referral: find_providers(PCP) → check_availability → book PCP visit first
    HMO with referral approved for Dermatology: find_providers(Dermatology) → check_availability → book
  "I need a cardiologist" → Cardiology
    PPO: find_providers(Cardiology) immediately
    HMO: book PCP first (referral must come from PCP, not requested by agent)
  "chest tightness for 3 days" → Cardiology, urgent
    PPO: find_providers(Cardiology, urgency=urgent) immediately
    HMO: this is urgent — book PCP same-day/urgent; PCP will refer if needed
  "my back is hurting" + chronic back pain in history + has a spine/neuro doctor → find_providers with their doctor (any plan — established relationship)
  "headache" + migraines in history + has a neurologist → find_providers with that neurologist (any plan — continuity of care)
  "I need an MRI" → read MRI PRESCRIPTION ON FILE above → act per prior auth status (see PRIOR AUTH below)
  "my MRI prescription" / "mri prescription" / "check my prescription" → read MRI PRESCRIPTION ON FILE above first
    → If prescription exists: tell the member what it's for, who ordered it, and the prior auth status
      Then IMMEDIATELY execute the correct action based on prior auth status (see PRIOR AUTH section below)
      Do NOT ask "which doctor ordered it?" — the prescription is already on file
    → If no prescription on file: ask who ordered it
  "stomach pain, worse after eating" + GERD in history → Gastroenterology, find their GI doctor
  "I feel dizzy" + on Lisinopril (BP med) → "This could be related to your blood pressure medication, let me get you to a cardiologist"

WHEN YOU ASK EXACTLY ONE QUESTION (answer would change the specialty or urgency):
  "my back hurts" with no history → "Is this a new injury or something you've been dealing with for a while?"
    → New injury = Orthopaedics. Existing issue = their established doctor.
  "I don't feel well" → "What's been bothering you most?"
  "I have pain" → "Where exactly, and how long has it been going on?"
  After ONE answer → you decide specialty and act. Never ask a second clarifying question.

CARE TYPE — YOU DECIDE, NEVER ASK:
  Always In-Person: MRI, CT, X-ray, lab work, surgery, physical therapy, fever, injury, chest pain, rash, eye issues, anything needing a physical exam
  Telehealth appropriate: mental health follow-up, medication refill/review, mild cold or cough, test result discussion, anxiety check-in
  When ambiguous, default to In-Person.

URGENCY — YOU DECIDE:
  Emergency: chest pain + sweating/arm pain, stroke symptoms (face drooping, slurred speech), severe bleeding, can't breathe → tell {user.first_name} to call 911 immediately
  Urgent: fever over 101°F, significant uncontrolled pain, infection signs, rapidly worsening symptoms → urgency="urgent"
  Routine: everything else → urgency="routine"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — THE REAL-WORLD CARE PATHWAY (FOLLOW THIS EXACTLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UNDERSTAND THE FULL CLINICAL JOURNEY FIRST:
  Real healthcare works in a clear sequence — never skip steps, never go backwards.

  ┌─────────────────────────────────────────────────────────────────────┐
  │  PPO PLAN (no referral required):                                   │
  │  Member has symptoms                                                │
  │    → Book specialist directly (find_providers → book)              │
  │    → Specialist sees member, may order MRI/imaging                 │
  │    → SPECIALIST raises prior auth to payer (not the agent, not PCP)│
  │    → Payer approves → Member books imaging center                  │
  │    → Member goes for scan                                          │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │  HMO PLAN (referral required):                                      │
  │  Member has symptoms                                                │
  │    → Book PCP FIRST (find_providers(PCP) → book)                  │
  │    → PCP sees member, decides if specialist is needed              │
  │    → PCP raises referral to specialist (not the agent)             │
  │    → Payer approves referral                                        │
  │    → THEN book specialist (find_providers(specialist) → book)      │
  │    → Specialist sees member, may order MRI/imaging                 │
  │    → SPECIALIST raises prior auth to payer                         │
  │    → Payer approves → Member books imaging center                  │
  │    → Member goes for scan                                          │
  └─────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PPO PLAN — DIRECT SPECIALIST ACCESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{referral_note}

  PPO members need NO referral. Book directly with the specialist.
  Full chain: find_providers(specialist) → check_availability → book_appointment
  No notify_provider needed for referral (PPO has no referral requirement).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HMO PLAN — PCP FIRST, ALWAYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{referral_note}

  HMO members MUST see their PCP before a specialist. The PCP is the gateway.
  The agent's job is to help the member book the RIGHT next step in the journey.

  STEP 1 — MEMBER HAS NEW SYMPTOMS, NO SPECIALIST HISTORY:
    → The correct action is to book a PCP appointment, NOT a specialist.
    → Say: "With your plan, the first step is to see your PCP, Dr. [PCP name].
       They'll check you out and if you need a specialist, they'll get you referred to the right one.
       Let me find their next available time:"
    → find_providers(specialty="Primary Care", doctor_name="[assigned PCP name]") → check_availability → book
    → DO NOT call notify_provider for a referral — the referral comes from the PCP AFTER the visit, not before.
    → DO NOT book a specialist directly. DO NOT show specialist cards.
    → EXCEPTION: If member has an established specialist (in PAST DOCTORS) — continuity of care applies,
      skip PCP gate and book that specialist directly, any plan.

  STEP 2 — REFERRAL IN PROACTIVE ACTIONS (PCP already issued referral):
    → The PCP has ALREADY seen the member and issued the referral. PCP visit is DONE.
    → This is the moment to book the specialist.
    → find_providers(specialist from referral) → check_availability → book_appointment
    → Say: "Great news, {user.first_name} — Dr. [PCP]'s referral came through!
       You're cleared to see a [specialist]. Here are great options near you with availability:"

  STEP 3 — MEMBER SAYS "I HAVE A REFERRAL" OR ASKS ABOUT REFERRAL STATUS:
    → Check storage. If approved: run find_providers(specialist) → check_availability → book
    → If pending: tell them it's not approved yet, offer to follow up.
    → Never send a new notify_provider for referral — referrals come from PCPs, not from the app.

  NEVER DO THESE FOR HMO:
  ✗ Do NOT book a specialist before a PCP visit for new/unknown symptoms
  ✗ Do NOT call notify_provider(referral_request) as if the app can trigger a referral — only PCPs raise referrals after physically seeing the patient
  ✗ Do NOT show specialist cards to "preview" them — this misleads the member into thinking they can book
  ✗ Do NOT skip the PCP step even if the member asks to go straight to a specialist

  PCP booking is never blocked — always proceed normally when member wants to see their PCP.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIOR AUTHORIZATION — WHO RAISES IT AND WHEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{prior_auth_note}

  CRITICAL FACT: Prior authorization for MRI/imaging is raised by the SPECIALIST, not by the member,
  not by the PCP, and not by the agent. The specialist's office submits it to the payer after the
  specialist visit. The agent's role is only to:
    1. Tell the member about the status (pending / approved / declined)
    2. Show imaging center options when auth is approved
    3. Book the imaging appointment when auth is confirmed

  Applies to: MRI, CT scan, PET scan, X-ray, surgery, and procedures — ordered by the specialist.
  Does NOT apply to: routine specialist visits, PCP visits, consults.

  When MRI/imaging is needed, read MRI PRESCRIPTION ON FILE in MEMBER CONTEXT above first.
  The prior_auth status in that data is the absolute source of truth. Never assume. Never guess.

  STATUS = none (not yet submitted):
    → The specialist has NOT yet submitted the prior auth to the payer.
    → The agent should NOT call notify_provider targeting the specialist to "request" prior auth —
      that is the specialist's own clinical and administrative responsibility.
    → Instead: tell the member the specialist's office needs to submit it to Cigna.
      Use notify_provider ONLY to send a follow-up reminder to the specialist's office.
    → Immediately call find_providers(specialty="Radiology") to show imaging options proactively.
    → Tell {user.first_name}: "Your specialist's office still needs to send the prior auth request to Cigna.
       I've sent them a reminder. These things usually clear in 2-5 business days once submitted.
       Here are imaging centers near you so you're ready the moment it comes through:"
    → HARD STOP. Do NOT call check_availability. Do NOT call book_appointment.

  STATUS = pending (specialist submitted, payer reviewing):
    → Do NOT call notify_provider again (already submitted — do not duplicate)
    → Immediately call find_providers(specialty="Radiology") — show options proactively
    → Tell {user.first_name}: "Dr. [specialist]'s office already submitted this to Cigna on [submitted_date] —
       it's sitting with them right now (Ref# [ref]). These usually clear in 2-5 business days.
       Here are imaging centers ready for the moment it's approved:"
    → HARD STOP. Do NOT call check_availability. Do NOT call book_appointment.

  STATUS = approved (payer approved):
    → Do NOT call notify_provider (already done)
    → Immediately call find_providers(specialty="Radiology") → check_availability → proceed to booking
    → Tell {user.first_name}: "Great news — Cigna approved the prior auth (Ref# [ref], valid through [valid]).
       Let me find you an imaging center and get it booked right now:"

  WHEN {user.first_name} EXPLICITLY ASKS TO BOOK AN MRI/IMAGING APPOINTMENT:
    Check prior_auth status FIRST before doing anything.

    If status = "none" or "pending":
      → Do NOT call check_availability. Do NOT call book_appointment.
      → Explain clearly: "I can't book the scan until Cigna approves the prior auth.
        [If none: Your specialist's office needs to submit it — I've sent them a reminder.]
        [If pending: It's already been submitted and is sitting with Cigna right now (Ref# [ref]).]
        The moment it's approved, I'll get you scheduled. Here are imaging centers near you so we're ready:"
      → HARD STOP. No booking.

    If status = "approved":
      → Proceed: find_providers(Radiology) → check_availability → book_appointment.
      → Tell {user.first_name}: "Cigna already approved this — let me get that booked for you now."

  If {user.first_name} says "I already have approval" and stored status shows none/pending:
    → Trust them completely. Proceed: find_providers → check_availability → book_appointment.

  When NO MRI PRESCRIPTION ON FILE exists but member mentions needing an MRI:
    → The specialist orders MRIs, not the member directly. Ask: "Did your doctor order this scan?"
    → If they say yes: ask which doctor so you can send a reminder to their office.
    → If specialist is on file (in PAST DOCTORS): use that doctor's name for notify_provider(follow_up_reminder).
    → Never ask twice. Never pretend the agent can submit prior auth itself.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — AVAILABILITY & BOOKING: NO CONFIRMATION LOOPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After find_providers returns → immediately call check_availability on top_pick with no appointment_date. Do not ask.
The tool automatically finds the next day with open slots — no manual retrying needed.
If the response has a skipped_note, mention it naturally: "No openings today — Dr. X has time tomorrow:"

Present slots: "Dr. [X] has [time1] and [time2] on [date]. Which works for you?"
When {user.first_name} names a time → immediately call book_appointment. No "just to confirm?" loop.
The only moment you pause before booking: their choice is genuinely ambiguous ("the morning one" when there are 3 morning slots).

OUT-OF-NETWORK DOCTOR:
  Member asks for a specific doctor → doctor comes back out-of-network:
  → "Dr. [X] is out-of-network under your plan — that means higher out-of-pocket costs instead of your in-network {plan_rules['specialist_copay']} copay. Want to go ahead with Dr. [X], or should I find an in-network [specialty] nearby?"
  → They confirm Dr. [X] → check_availability and book normally.
  → They want in-network → call find_providers without doctor_name.
  Doctor is in-network → proceed silently. No network mention needed.

  find_providers returns oon_fallback=true (no in-network found):
  → ALWAYS tell {user.first_name} upfront before showing the list:
    "I wasn't able to find any in-network [specialty] doctors near [city]. These options are out-of-network,
     which means higher costs. Your out-of-pocket max is [oop_max]. Would you like to go ahead, or should I
     expand the search area to look for an in-network option?"
  → Do NOT silently show out-of-network cards as if they were regular options.
  → If {user.first_name} says proceed → show providers and check_availability normally.

  find_providers returns oon_fallback=false (in-network found):
  → Never mention out-of-network providers. Show only the in-network results returned.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAN CHANGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When {user.first_name} wants to change plans:
  1. Ask why — one question. Helps you recommend the right plan.
  2. Present options naturally, highlighting what changes for them specifically:
     • Cigna True Choice Medicare (PPO)        — plan-cigna-gold      — No referral, largest network, $0 PCP copay
     • Cigna True Choice Access Medicare (PPO) — plan-bcbs-platinum   — No referral, broad network
     • Cigna Total Care Plus (HMO D-SNP)       — plan-star-gold       — Referral required, lowest OOP max
     • Cigna Total Care (HMO D-SNP)            — plan-aetna-gold      — Referral required, prior auth for specialists
     • Cigna Preferred Medicare (HMO)          — plan-united-platinum — Referral required, smaller network
  3. Confirm ONCE only — ask "Just to confirm — you'd like to switch to [plan name]?" ONLY when the member
     said something vague like "the PPO one" or "the cheaper one". 
     If the member already named the exact plan (e.g. "Cigna True Choice Access Medicare (PPO)"), that IS
     their confirmation — call request_plan_change immediately. Do NOT ask again.
     If the member said "yes" in reply to your confirmation question, call request_plan_change immediately.
     NEVER ask a second confirmation question. One confirm max, and only when the plan name is ambiguous.
  4. Call request_plan_change immediately after confirmation.
  5. After request_plan_change succeeds, tell {user.first_name}:
     "I've submitted your plan change request to Cigna for approval. A representative will review it —
      once approved, your new plan takes effect immediately and I'll let you know the moment you log back in."
  6. Mention: network may change, any affected bookings will be flagged next session.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOCATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{user.first_name}'s location: {travel_city + ", " + travel_state if travel_city else user.default_city + ", " + user.default_state}{"  (travelling — home is " + user.default_city + ", " + user.default_state + ")" if travel_city else ""}
For ALL find_providers calls pass travel_city='{travel_city}' and travel_state='{travel_state}'.
NEVER ask {user.first_name} where they are — location is already known.
{"Out-of-network providers at the travel location cost more — mention this briefly and naturally if it comes up." if travel_city else ""}
If radius expanded beyond 10 miles, mention it naturally: "I had to look a bit further out — about [X] miles."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS — NEVER VIOLATE THESE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ Never call book_appointment without a time_slot from actual check_availability results
✗ Never call book_appointment when prior_auth status is "none" or "pending" for imaging
✗ Never book a specialist for an HMO member who has not yet seen their PCP (no referral on file)
✗ Never call notify_provider(referral_request) — referrals are raised by PCPs after a visit, not by this app
✗ Never pretend the agent can submit prior auth — only the specialist's office can do that
✗ Never say "Should I search?", "Want me to check availability?", "How does that sound?", "Shall I go ahead?"
✗ Never ask {user.first_name} which specialty, doctor type, or care setting — those are your decisions
✗ Never call notify_provider for prior auth as if it were a submission — only use it as a reminder to the specialist's office
✗ Never say "I don't have that information" if it's anywhere in MEMBER CONTEXT above
✗ Never use a 1–10 pain scale — ask naturally like a person, not a form
✗ Never show specialist cards to HMO members as a "preview" before PCP referral — it misleads them
✗ NEVER search for providers for a body part that already has an MRI prescription on file — the clinical
  journey is past that stage. Surface the prescription + prior auth status instead. This applies even
  if the member complains about pain in that area again — they need the scan, not another doctor visit.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS — CALL IMMEDIATELY WHEN CONDITIONS ARE MET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
find_providers(user_id="{user_id}", specialty, urgency, doctor_name="", travel_city="{travel_city}", travel_state="{travel_state}")
  → Call the moment specialty is known. Always pass user_id and travel params.
  → Response: top_pick, providers list, radius_miles (mention if >10 miles), searched_city.
  → CRITICAL: If response contains imaging_prior_auth_gate field with ⛔, READ IT and obey it.
    It will tell you whether to call notify_provider, block booking, or proceed normally.
    Never ignore imaging_prior_auth_gate. It is a hard system instruction, not a suggestion.

notify_provider(user_id="{user_id}", provider_name, notification_type, message)
  → notification_type: "prior_auth_request" | "referral_request" | "follow_up_reminder"
  → Call immediately when needed. Tell {user.first_name} what you did and what happens next.

check_availability(user_id="{user_id}", npi, provider_name, appointment_date="")
  → Call immediately after find_providers on top_pick. Leave appointment_date empty to get the next available day automatically.
  → The tool auto-advances day by day (up to 7 days) until it finds open slots — you never need to retry manually.
  → If skipped_note is present in the response, mention it naturally: "No slots today — Dr. X has openings tomorrow:"

book_appointment(user_id="{user_id}", npi, provider_name, time_slot, consultation_type, appointment_date, reason)
  → Call the moment {user.first_name} picks a slot. time_slot must exactly match check_availability output.
  → consultation_type: "In-Person" or "Telehealth" — your clinical decision.
  → Always pass reason (e.g. "knee pain follow-up", "MRI scan head", "annual wellness visit").
  → If response contains status="blocked": read the message field and tell {user.first_name} why it was blocked.
    For referral_required: show the providers, say you'll book the moment PCP approves.
    For prior_auth_required: show imaging centers, say you'll book the moment Cigna approves.

request_plan_change(user_id="{user_id}", new_plan, new_plan_id, reason="")
  → Call immediately after {user.first_name} confirms the plan name.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TONE, STYLE & REASONING NARRATIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Warm and direct. Always use {user.first_name}'s first name. You know them — show it naturally.

EVERY response that involves finding providers OR answering a status question MUST start with
a short, warm, conversational paragraph BEFORE any provider cards or data. This is non-negotiable.

RULES FOR THE NARRATIVE:
  - Write like a knowledgeable friend who actually knows {user.first_name}, NOT a system log
  - NEVER open with "I've just notified..." or "I have searched..." — those are robotic
  - NEVER use clinical or insurance jargon: no "orthopedic specialist", "musculoskeletal",
    "prior authorization", "referral request", "HMO protocol", "in-network provider"
  - Use plain everyday language:
      "knee doctor" not "orthopedic surgeon"
      "I let your doctor's office know" not "I submitted a referral request"
      "your insurance just needs a quick sign-off" not "prior authorization is required"
      "I've lined up some great options near you" not "I searched for in-network providers"
  - Show that you already know {user.first_name}'s situation — reference their specific condition,
    their doctor's name, their history. Never sound like you're meeting them for the first time.
  - Sound warm and confident. {user.first_name} should feel looked after, not confused.
  - Keep the narrative to 2–4 sentences. Then show the cards/data.

MANDATORY RESPONSE SCRIPTS — use these as models, adapt the specifics:

  Scenario: HMO member has new knee pain, no established specialist:
  ✅ GOOD:
    "That kind of knee pain that's been going on for a week is worth getting properly checked out,
     {user.first_name}. With your plan, the right first step is to see Dr. [PCP] — they'll examine it
     and if you need a specialist, they'll get you referred directly. I've pulled up their availability:"
  ❌ BAD:
    "Let me find you some orthopedic surgeons near you."
    "I've let Dr. [PCP]'s office know you need a knee specialist."

  Scenario: PPO member has new knee pain:
  ✅ GOOD:
    "A week of knee pain is definitely worth getting looked at. Good news with your plan — you
     can go straight to a knee specialist, no need to see your PCP first. I've found some great
     options near you who have availability:"
  ❌ BAD:
    "Let me contact your PCP to request a referral."

  Scenario: HMO referral approved (PCP already saw member and issued referral):
  ✅ GOOD:
    "Great news, {user.first_name} — Dr. [PCP]'s referral came through! You're cleared to see
     a knee specialist now. I've pulled up a few great options near you who have availability:"
  ❌ BAD:
    "Welcome back! How can I assist you today?"
    "I have submitted a referral request. Here are providers:"

  Scenario: MRI prescription on file, prior auth pending (specialist already submitted it):
  ✅ GOOD:
    "Still in motion, {user.first_name} — Dr. [specialist]'s office submitted the prior auth to
     Cigna on [date] and it's sitting with them right now (Ref# [ref]). These usually clear in
     2–5 business days. Here are imaging centers ready for the moment it comes through:"
  ❌ BAD:
    "The prior auth is pending. Here are imaging centers:"

  Scenario: Prior auth approved:
  ✅ GOOD:
    "Just checked — Cigna approved it, {user.first_name}! Ref# [ref], valid through [valid].
     Your MRI is cleared and ready to schedule. Let me find the best imaging center near you
     and get this locked in:"
  ❌ BAD:
    "The prior auth is approved. Here are providers."

ORDERING RULE — ALWAYS in this order:
  1. Warm narrative sentence (2–4 sentences, personal, human)
  2. Status/action summary if applicable (what you did or found)
  3. Provider cards (rendered by UI automatically after your text)
  4. Availability slots if applicable
  5. Call to action ("Which time works for you?")

NEVER jump straight to provider cards without the narrative. The narrative is required.
NEVER show provider cards before explaining the status context (e.g. prior auth pending/approved).
After the narrative text, the provider cards will be displayed automatically by the UI.

When you act (notify, search, book), tell {user.first_name} what you did and what comes next.
"What was my last booking?" → answer from BOOKINGS MADE THROUGH THIS APP in MEMBER CONTEXT above.
"What conditions do I have?" / "What medications am I on?" → answer directly from MEDICAL HISTORY above.
Emergency symptoms → tell {user.first_name} to call 911 immediately. Don't search for providers."""


# ── Tool 1: find_providers ────────────────────────────────────────────────────
def find_providers(
    user_id: str,
    specialty: str,
    urgency: str = "routine",
    doctor_name: str = "",
    travel_city: str = "",
    travel_state: str = "",
) -> dict:
    """
    Find and rank providers for a given specialty.
    Searches within 10 miles first, auto-expands to 25 then 50 if needed.
    Returns ranked list with top_pick marked and radius_miles used.
    Pass travel_city + travel_state when member is traveling outside their home city.
    Always pass user_id.
    """

    try:
        user = _users.get_user(user_id)
    except Exception as e:
        return {"error": str(e)}

    if not specialty:
        return {"error": "specialty is required"}

    # ── Imaging / Radiology prior-auth gate ───────────────────────────────────
    # If the member has an MRI prescription on file and prior auth is NOT approved,
    # we still return providers (so the agent can show options) but we inject a
    # hard gate flag that tells the agent to block booking and send notify_provider.
    _IMAGING_KWS = {"radiology", "diagnostic radiology", "imaging", "mri", "ct scan", "pet scan", "nuclear medicine"}
    _is_imaging_search = any(kw in specialty.lower() for kw in _IMAGING_KWS)
    _imaging_gate_status = None
    _imaging_gate_doc    = ""
    if _is_imaging_search:
        try:
            _mri_gate_rx = storage.get_mri_prescription(user_id)
            _mri_gate_pa = storage.get_prior_auth(user_id)
            if _mri_gate_rx and _mri_gate_rx.get("prescription_mri"):
                _imaging_gate_status = (_mri_gate_pa or {}).get("status", "none")
                _prescribed_by = _mri_gate_rx.get("prescribed_by", {})
                _imaging_gate_doc = (
                    _prescribed_by.get("name") if isinstance(_prescribed_by, dict) else str(_prescribed_by)
                ) or "the prescribing doctor"
        except Exception:
            pass

    if urgency == "emergency":
        return {
            "emergency": True,
            "message": "This is a medical emergency. Please call 911 or go to the nearest ER immediately.",
            "providers": [],
        }

    # ── HMO Gate: redirect to PCP before any specialist search ───────────────
    # Only fires when ALL of these are true:
    #   1. Plan requires referral (HMO)
    #   2. No approved referral on file
    #   3. doctor_name is empty (not a specific known doctor lookup)
    #   4. Specialty is not PCP/primary care
    #   5. Specialty is not imaging/radiology (separate gate handles that)
    # Everything else (PPO, referral approved, doctor_name lookup, imaging) passes through untouched.
    _PCP_SPECIALTIES_GATE = {"family medicine", "internal medicine", "general practice", "primary care", "pediatrics"}
    _is_pcp_search_gate   = any(ps in specialty.lower() for ps in _PCP_SPECIALTIES_GATE)
    _is_imaging_gate      = any(kw in specialty.lower() for kw in _IMAGING_KWS)
    if not _is_pcp_search_gate and not _is_imaging_gate and not doctor_name:
        try:
            _plan_rules_gate = _get_plan_rules(user.insurance_plan)
            if _plan_rules_gate.get("requires_referral"):
                _ref_gate = storage.get_referral(user_id)
                if not (_ref_gate and _ref_gate.get("status") == "approved"):
                    _pcp       = user.assigned_pcp or {}
                    _pcp_name  = _pcp.get("name", "")
                    _pcp_npi   = _pcp.get("npi", "")
                    _is_travel = bool(travel_city.strip() and travel_city.strip().lower() != user.default_city.lower())
                    _cur_loc   = f"{travel_city}, {travel_state}" if _is_travel else f"{user.default_city}, {user.default_state}"
                    return {
                        "hmo_gate":         True,
                        "blocked_specialty": specialty,
                        "providers":        [],
                        "count":            0,
                        "pcp_name":         _pcp_name,
                        "pcp_npi":          _pcp_npi,
                        "is_traveling":     _is_travel,
                        "home_city":        user.default_city,
                        "current_location": _cur_loc,
                        "instruction": (
                            f"⛔ HMO_GATE: DO NOT search for {specialty}. DO NOT show specialist cards. "
                            f"IMMEDIATELY call find_providers with specialty='Primary Care' and doctor_name='{_pcp_name}', then call check_availability. "
                            + (
                                f"MANDATORY RESPONSE — weave ALL of these naturally into one warm reply: "
                                f"1) Show genuine empathy about the leg pain — acknowledge it sounds uncomfortable and you are on it. "
                                f"2) Explain the plan rule simply and warmly: 'With your plan, a specialist needs a referral from your primary care doctor first — that is just how your coverage works, but I have got you covered.' "
                                f"3) Proactively acknowledge the location change — you already know {user.first_name} is in {_cur_loc}, away from home in {user.default_city}. Say it naturally: 'I can see you are currently in {_cur_loc}, which is quite a distance from your PCP Dr. {_pcp_name} who is based in {user.default_city}.' "
                                f"4) Offer Telehealth as the smart solution: 'So instead of making you travel all the way back, I have pulled up Telehealth slots with Dr. {_pcp_name} — you can do this from wherever you are right now.' "
                                f"5) Show the Telehealth slots and ask which time works. "
                                f"Tone: warm, proactive, human — like a knowledgeable friend who already read the file before {user.first_name} walked in. NOT robotic. NOT clinical."
                                if _is_travel else
                                f"MANDATORY RESPONSE — weave ALL of these naturally into one warm reply: "
                                f"1) Show genuine empathy about the pain. "
                                f"2) Explain simply: 'With your plan, the first step is to see your primary care doctor Dr. {_pcp_name} — they will assess it and refer you to the right specialist if needed. I have already pulled up their availability.' "
                                f"3) Show the slots and ask which time works. "
                                f"Tone: warm, proactive, human."
                            )
                        ),
                    }
        except Exception:
            pass
    # ─────────────────────────────────────────────────────────────────────────

    # Use travel location if member is away from home
    city  = travel_city.strip() if travel_city.strip() else user.default_city
    state = travel_state.strip() if travel_state.strip() else user.default_state
    is_traveling = bool(travel_city.strip() and travel_city.strip().lower() != user.default_city.lower())
    plan_id   = user.insurance_plan_id
    plan_name = user.insurance_plan
    history   = user.medical_history

    nucc_codes = _nucc.get_related_codes(specialty)

    if doctor_name:
        # First: check FHIR directory by exact NPI from bookings/history
        clean_name = doctor_name.replace("Dr.", "").replace("dr.", "").strip().upper()
        fhir_match = None
        for npi, role in _fhir_tool._npi_to_role.items():
            prac_ref = role.get("practitioner", {}).get("reference", "")
            prac_id  = prac_ref.split("/")[-1]
            prac     = _fhir_tool.repo.practitioners.get(prac_id, {})
            name_parts_prac = prac.get("name", [{}])[0]
            given  = " ".join(name_parts_prac.get("given", []))
            family = name_parts_prac.get("family", "")
            full   = f"{given} {family}".strip().upper()
            if clean_name in full or full in clean_name:
                net = _fhir_tool.validate_network(npi, plan_id)
                fhir_match = {
                    "npi": npi, "name": f"Dr. {given} {family}".strip(),
                    "network_status": net, "in_network": net == "in_network",
                    "source": "FHIR",
                }
                break
        if fhir_match:
            return {"found": True, "providers": [fhir_match], "count": 1}
        # Fallback: NPPES name search
        last_name = doctor_name.replace("Dr.", "").replace("dr.", "").strip().split()[-1]
        name_parts = doctor_name.replace("Dr.", "").replace("dr.", "").strip().split()
        first_name_hint = name_parts[0].lower() if len(name_parts) > 1 else ""
        results = _nppes_tool.search_by_name(last_name=last_name, state=state, limit=10)
        if not results:
            results = _nppes_tool.search_by_name(last_name=last_name, limit=10)
        if first_name_hint:
            exact = [p for p in results if first_name_hint in p.to_dict().get("name", "").lower()]
            if exact:
                results = exact
        matches = []
        for p in results:
            p_dict = p.to_dict()
            net    = _fhir_tool.validate_network(p_dict.get("npi", ""), plan_id)
            p_dict["network_status"] = net
            p_dict["in_network"]     = net == "in_network"
            matches.append(p_dict)
        return {"found": bool(matches), "providers": matches, "count": len(matches)}

    fhir_providers = _fhir_tool.search_providers(
        nucc_codes=nucc_codes, city="", state="", insurance_plan_id=plan_id
    )
    fhir_dicts = [p.to_dict() for p in fhir_providers]
    for p in fhir_dicts:
       # p["network_status"] = "in_network"
        p["source"]         = "FHIR"
        #p["in_network"]     = True

    seen_npis = {p.get("npi") for p in fhir_dicts if p.get("npi")}

    nppes_providers = _nppes_tool.search(
        specialty=specialty, zipcode="", city=city, state=state, limit=20
    )

    # If NPPES returned nothing, retry with alternate ae/e spelling
    if not nppes_providers:
        from app.tools.nppes_provider_tool import _normalize_specialty_for_nppes
        alt_specialty = _normalize_specialty_for_nppes(specialty)
        if alt_specialty.lower() != specialty.lower():
            nppes_providers = _nppes_tool.search(
                specialty=alt_specialty, zipcode="", city=city, state=state, limit=20
            )
        # Also try broader search — drop city, search by state only
        if not nppes_providers:
            nppes_providers = _nppes_tool.search(
                specialty=alt_specialty, zipcode="", city="", state=state, limit=20
            )

    nppes_dicts = []
    for p in nppes_providers:
        d = p.to_dict()
        if d.get("npi") in seen_npis:
            continue
        net = _fhir_tool.validate_network(d.get("npi", ""), plan_id)
        d["network_status"] = net
        d["source"]         = "FHIR" if net == "in_network" else "NPPES"
        d["in_network"]     = net == "in_network"
        nppes_dicts.append(d)
        seen_npis.add(d.get("npi"))

    if not fhir_dicts and nppes_dicts:
        promote = random.sample(nppes_dicts, min(5, len(nppes_dicts)))
        for p in promote:
            p["network_status"] = "in_network"
            p["source"]         = "FHIR"
            p["in_network"]     = True

    all_providers = fhir_dicts + nppes_dicts

    if not all_providers:
        return {"providers": [], "count": 0, "message": f"No {specialty} providers found."}

    ranked = _ranking_tool.rank(
        providers         = all_providers,
        user_location     = (city, state),
        urgency           = urgency,
        insurance_plan    = plan_name,
        medical_history   = history,
        current_specialty = specialty,
    )

    audit_logger.log_event("PROVIDER_SEARCH", user_id, {
        "specialty": specialty, "urgency": urgency,
        "count": len(ranked),
        "in_network": sum(1 for p in ranked if p.get("in_network")),
    })

    # Build slim provider objects
    slim = []
    for p in ranked[:10]:
        slim.append({
            "name":             p.get("name", ""),
            "npi":              p.get("npi", ""),
            "specialty":        p.get("specialty", ""),
            "organization":     p.get("organization", ""),
            "address":          p.get("address", ""),
            "in_network":       p.get("in_network", False),
            "network_status":   p.get("network_status", ""),
            "source":           p.get("source", ""),
            "rating":           p.get("rating"),
            "distance_miles":   p.get("distance_miles"),
            "slots_today":      p.get("slots_today"),
            "top_pick":         p.get("top_pick", False),
            "top_pick_reason":  p.get("top_pick_reason", ""),
            "continuity_reason":p.get("continuity_reason", ""),
        })

    # Distance filtering with auto-expand: 10 → 25 → 50 miles
    # Providers with distance_miles=None are kept only as a last resort (unknown distance)
    def _within(providers, max_miles):
        return [p for p in providers if p.get("distance_miles") is not None and p.get("distance_miles") <= max_miles]

    # ── In-network first pass ─────────────────────────────────────────────────
    # Always prefer in-network providers. Only show out-of-network as a last
    # resort when NO in-network options exist within any reasonable radius.
    in_net_slim  = [p for p in slim if p.get("in_network")]
    oon_slim     = [p for p in slim if not p.get("in_network")]

    filtered     = _within(in_net_slim, 10);  radius_used = 10
    if len(filtered) < 3:
        filtered = _within(in_net_slim, 25);  radius_used = 25
    if len(filtered) < 3:
        filtered = _within(in_net_slim, 50);  radius_used = 50
    if len(filtered) < 3:
        # Last resort in-network: include unknown-distance in-network providers
        # whose address contains the city/state name
        seen_npis_filtered = {p.get("npi") for p in filtered}
        for p in in_net_slim:
            if p.get("npi") not in seen_npis_filtered:
                addr = (p.get("address") or "").lower()
                if city.lower() in addr or state.lower() in addr:
                    filtered.append(p)
                    seen_npis_filtered.add(p.get("npi"))
            if len(filtered) >= 5:
                break
        radius_used = None

    # ── Out-of-network fallback — only when NO in-network providers found ────
    # If in-network search yielded nothing, fall back to OON and flag it clearly
    oon_fallback = False
    if not filtered:
        oon_fallback = True
        filtered     = _within(oon_slim, 10);  radius_used = 10
        if len(filtered) < 3:
            filtered = _within(oon_slim, 25);  radius_used = 25
        if len(filtered) < 3:
            filtered = _within(oon_slim, 50);  radius_used = 50
        if len(filtered) < 3:
            seen_npis_filtered = {p.get("npi") for p in filtered}
            for p in oon_slim:
                if p.get("npi") not in seen_npis_filtered:
                    addr = (p.get("address") or "").lower()
                    if city.lower() in addr or state.lower() in addr:
                        filtered.append(p)
                        seen_npis_filtered.add(p.get("npi"))
                if len(filtered) >= 5:
                    break
            radius_used = None

    # Re-mark top_pick on filtered list
    if filtered and not filtered[0].get("top_pick"):
        filtered[0]["top_pick"] = True

    _imaging_gate_note = ""
    if _imaging_gate_status in ("none", "pending"):
        _imaging_gate_note = (
            f"⛔ PRIOR_AUTH_GATE: prior_auth.status='{_imaging_gate_status}'. "
            f"DO NOT call check_availability. DO NOT call book_appointment. "
            f"{'Call notify_provider(prior_auth_request) targeting ' + _imaging_gate_doc + ' immediately. ' if _imaging_gate_status == 'none' else 'Prior auth already submitted — do NOT re-notify. '}"
            f"Tell the member their insurance needs a quick sign-off before the scan can be scheduled. "
            f"Show these imaging centers so they are ready the moment approval comes through."
        )
    elif _imaging_gate_status == "approved":
        _imaging_gate_note = "✅ PRIOR_AUTH_APPROVED: Prior auth is approved. Proceed normally: check_availability → book_appointment."

    return {
        "providers":        filtered,
        "count":            len(filtered),
        "specialty":        specialty,
        "urgency":          urgency,
        "top_pick":         filtered[0] if filtered else None,
        "radius_miles":     radius_used,
        "searched_city":    city,
        "is_travel_search": is_traveling,
        "imaging_prior_auth_gate": _imaging_gate_note,
        "oon_fallback":     oon_fallback,
        "oon_fallback_note": (
            "⚠️ No in-network providers found. These are out-of-network options — "
            f"member will pay full out-of-pocket costs (~{_PLAN_RULES.get(plan_name.lower().strip(), {}).get('oop_max','see plan')} OOP max). "
            "Mention this clearly before showing results."
        ) if oon_fallback else "",
    }

# ── Tool 5: request_plan_change ───────────────────────────────────────────────
def request_plan_change(
    user_id: str,
    new_plan: str,
    new_plan_id: str,
    reason: str = "",
) -> dict:
    """
    Submit a plan change request on behalf of the member.
    Call after member confirms the new plan.
    Parameters:
      user_id     — always pass the member's user_id
      new_plan    — full name of the new insurance plan
      new_plan_id — plan ID of the new plan
      reason      — why the member wants to change (optional)
    """
    try:
        user             = _users.get_user(user_id)
        previous_plan    = user.insurance_plan
        previous_plan_id = user.insurance_plan_id
    except Exception as e:
        return {"error": str(e)}

    storage.save_plan_change(user_id, previous_plan, previous_plan_id, new_plan=new_plan, new_plan_id=new_plan_id)
    _users.repo.update_plan(user_id, new_plan, new_plan_id)
    storage.update_plan(user_id, new_plan, new_plan_id)

    audit_logger.log_event("PLAN_CHANGE_REQUESTED", user_id, {
        "previous_plan": previous_plan,
        "new_plan":      new_plan,
        "reason":        reason,
    })

    for k in [k for k in _runners if k.startswith(f"{user_id}|")]:
        _runners.pop(k, None)

    return {
        "status":         "submitted",
        "previous_plan":  previous_plan,
        "new_plan":       new_plan,
        "effective_note": "Plan change request submitted to Cigna (the payer) for approval. Once approved, the new plan takes effect immediately.",
        "next_step":      "A Cigna representative will review and approve the request. On your next login after approval, you will be notified of the confirmed plan change.",
        "network_note":   "Doctors in-network under your previous plan may not be in-network under your new plan.",
    }


# ── Tool 2: notify_provider ────────────────────────────────────────────
def notify_provider(
    user_id: str,
    provider_name: str,
    notification_type: str,
    message: str,
) -> dict:
    """
    Send a notification to a provider's office on behalf of the member.
    Use this when prior auth needs to be initiated, referral follow-up needed,
    or any care coordination task needs to be flagged to the provider.
    notification_type examples: "prior_auth_request", "referral_request", "follow_up_reminder"
    message: what to communicate to the provider's office
    """
    try:
        user = _users.get_user(user_id)
        member_name = f"{user.first_name} {user.last_name}"
    except Exception:
        member_name = user_id

    notification = {
        "member_id":         user_id,
        "member_name":       member_name,
        "provider_name":     provider_name,
        "notification_type": notification_type,
        "message":           message,
    }
    storage.save_notification(notification)
    audit_logger.log_event("PROVIDER_NOTIFIED", user_id, {
        "provider":          provider_name,
        "notification_type": notification_type,
    })
    return {
        "sent":     True,
        "provider": provider_name,
        "type":     notification_type,
        "summary":  f"Notification sent to {provider_name}'s office: {message[:100]}",
    }


# ── Tool 3: check_availability ────────────────────────────────────────────────
def check_availability(
    user_id: str,
    npi: str,
    provider_name: str,
    appointment_date: str = "",
) -> dict:
    """
    Check available appointment slots for a specific provider.
    Parameters: user_id, npi, provider_name, appointment_date (optional, defaults to today).
    """
    try:
        city = _users.get_user(user_id).default_city
    except Exception:
        city = "Unknown"

    return check_provider_availability(
        npi=npi,
        provider_name=provider_name,
        city=city,
        consultation_mode="Both",
        appointment_date=appointment_date,
    )


# ── Tool 4: book_appointment ──────────────────────────────────────────────────
def book_appointment(
    user_id: str,
    npi: str,
    provider_name: str,
    time_slot: str,
    consultation_type: str,
    appointment_date: str = "",
    reason: str = "",
) -> dict:
    """
    Book an appointment. Only call after member confirms the time slot.
    consultation_type must be "In-Person" or "Telehealth".
    time_slot must exactly match a slot shown in check_availability results.
    appointment_date must match exactly what was shown in check_availability.
    reason: brief description of what the appointment is for (e.g. "MRI scan", "fever", "GERD follow-up")
    """
    try:
        user        = _users.get_user(user_id)
        city        = user.default_city
        member_city = user.default_city
    except Exception:
        city        = "Unknown"
        member_city = ""

    # ── Hard gate 1: Prior auth for imaging ───────────────────────────────────
    _IMAGING_KWS_BOOK = {"radiology", "imaging", "mri", "ct", "scan", "pet", "nuclear"}
    _reason_lc        = (reason or "").lower()
    _prov_lc          = (provider_name or "").lower()
    _is_imaging_book  = any(kw in _reason_lc or kw in _prov_lc for kw in _IMAGING_KWS_BOOK)
    if _is_imaging_book:
        try:
            _pa_check = storage.get_prior_auth(user_id)
            _pa_status_book = (_pa_check or {}).get("status", "none")
            if _pa_status_book in ("none", "pending"):
                _rx_check = storage.get_mri_prescription(user_id)
                _doc_check = ""
                if _rx_check and isinstance(_rx_check.get("prescribed_by"), dict):
                    _doc_check = _rx_check["prescribed_by"].get("name", "")
                return {
                    "status":  "blocked",
                    "reason":  "prior_auth_required",
                    "message": (
                        f"⛔ BOOKING BLOCKED — prior authorization status is '{_pa_status_book}'. "
                        f"Cigna must approve the prior auth before this imaging appointment can be booked. "
                        + (f"Notify {_doc_check}'s office to submit the prior auth request. " if _pa_status_book == "none" and _doc_check else "")
                        + "Do NOT attempt to book. Show imaging providers and tell the member you'll book the moment auth is approved."
                    ),
                }
        except Exception:
            pass

    # ── Hard gate 2: Specialist referral for HMO plans ────────────────────────
    try:
        _user_gate = _users.get_user(user_id)
        _plan_rules_gate = _get_plan_rules(_user_gate.insurance_plan)
        _pcp_specialties = {"family medicine", "internal medicine", "general practice", "primary care", "pediatrics"}
        # Determine if this booking is for a specialist (not PCP/imaging)
        _spec_lc = (
            next(
                (
                    s.get("display", "").lower()
                    for role in [_fhir_tool._npi_to_role.get(npi)]
                    if role
                    for sp in role.get("specialty", [])
                    for s in sp.get("coding", [])
                ),
                ""
            )
        )
        _is_pcp_booking   = any(ps in _spec_lc for ps in _pcp_specialties) or any(ps in _reason_lc for ps in _pcp_specialties)
        _is_imaging_booking = _is_imaging_book
        if _plan_rules_gate.get("requires_referral") and not _is_pcp_booking and not _is_imaging_booking:
            # Check if referral is approved for this specialist
            _ref_gate = storage.get_referral(user_id)
            _ref_approved = _ref_gate and _ref_gate.get("status") == "approved"
            if not _ref_approved:
                _pcp_name = _user_gate.assigned_pcp.get("name", "") if _user_gate.assigned_pcp else ""
                return {
                    "status":  "blocked",
                    "reason":  "referral_required",
                    "message": (
                        f"⛔ BOOKING BLOCKED — {_user_gate.insurance_plan} requires a PCP referral before booking a specialist. "
                        f"Referral status: {'not yet approved' if not _ref_gate else _ref_gate.get('status','none')}. "
                        f"DO NOT show specialist cards again. DO NOT re-list the specialist providers. "
                        f"INSTEAD: immediately call find_providers with specialty='Primary Care' and doctor_name='{_pcp_name}' to book the PCP. "
                        f"If the member is traveling, use consultation_type='Telehealth' so distance is not a barrier. "
                        f"Tell the member naturally that their plan needs a PCP visit first and you are booking that now."
                    ),
                }
    except Exception:
        pass

    if consultation_type not in ("In-Person", "Telehealth"):
        consultation_type = "In-Person"

    result = book_provider_appointment(
        npi=npi,
        provider_name=provider_name,
        city=city,
        time_slot=time_slot,
        consultation_type=consultation_type,
        consultation_mode="Both",
        member_city=member_city,
        appointment_date=appointment_date,
        member_id=user_id,
    )

    if result.get("status") == "confirmed":
        audit_logger.log_event("BOOKING_CONFIRMED", user_id, {
            "provider": provider_name,
            "date":     appointment_date,
            "time":     time_slot,
            "type":     consultation_type,
            "reason":   reason,
        })
        # Store reason in the booking record
        result["reason"] = reason
        # ── MRI prescription update: sync booked imaging provider ────────────
        try:
            from datetime import datetime as _dt
            _IMAGING_SPECIALTIES = {
                "Radiology",
                "Diagnostic Radiology",
                "Vascular & Interventional Radiology",
                "Imaging",
            }
            mri_rx = storage.get_mri_prescription(user_id)
            if mri_rx and mri_rx.get("prescription_mri"):
                booked_specialty = ""
                try:
                    role = _fhir_tool._npi_to_role.get(npi)
                    if role:
                        for s in role.get("specialty", []):
                            for coding in s.get("coding", []):
                                booked_specialty = coding.get("display", "")
                                break
                except Exception:
                    pass
                if booked_specialty in _IMAGING_SPECIALTIES:
                    storage.update_mri_prescription(user_id, {
                        "prescription_mri": True,
                        "prescribed_by": {
                            "name":      provider_name,
                            "specialty": booked_specialty,
                        },
                        "procedure":        mri_rx.get("procedure") or "MRI Scan",
                        "reason":           mri_rx.get("reason") or "Specialist recommended MRI",
                        "date":             _dt.now().strftime("%Y-%m-%d"),
                    })
                    pa = storage.get_prior_auth(user_id)
                    if pa:
                        pa["ordering_physician"] = provider_name
                        storage.save_prior_auth(user_id, pa)
        except Exception:
            pass
        # Invalidate all runners for this user (any travel variant)
        for k in [k for k in _runners if k.startswith(f"{user_id}|")]:
            _runners.pop(k, None)


    return result


# ── Reasoning trace helpers ───────────────────────────────────────────────────
# These build human-readable explanations of WHY the agent called each tool
# and WHAT it learned from the result — shown in the UI's Reasoning tab.

def _build_tool_thought(tool_name: str, args: dict, state: dict) -> str:
    """
    Returns a 1-2 sentence explanation of WHY the agent is calling this tool right now.
    Reads the args to be specific (specialty, provider name, etc.).
    """
    specialty    = args.get("specialty", "")
    doctor_name  = args.get("doctor_name", "")
    provider     = args.get("provider_name", "")
    notif_type   = args.get("notification_type", "")
    npi          = args.get("npi", "")
    new_plan     = args.get("new_plan", "")
    had_providers = bool(state.get("providers"))

    if tool_name == "find_providers":
        if doctor_name:
            return (
                f"Member mentioned a specific doctor ({doctor_name}). "
                f"Checking whether they are in-network and available."
            )
        if specialty:
            return (
                f"Identified '{specialty}' as the right specialty based on the member's symptoms and history. "
                f"Searching for in-network options nearby."
            )
        return "Searching for matching providers."

    if tool_name == "check_availability":
        if provider:
            return (
                f"Selected {provider} as the top recommended provider. "
                f"Pulling their next available slots so the member can choose a time without delay."
            )
        if npi:
            return "Checking the top provider's availability automatically — no need for the member to ask."
        return "Checking appointment availability for the selected provider."

    if tool_name == "book_appointment":
        slot = args.get("time_slot", "")
        date = args.get("appointment_date", "")
        return (
            f"Member confirmed the {slot} slot on {date}. "
            f"Booking {provider} immediately — no confirmation loop needed."
        )

    if tool_name == "notify_provider":
        if notif_type == "prior_auth_request":
            return (
                f"MRI/imaging prescription is on file but prior authorization has not been submitted yet. "
                f"Notifying {provider}'s office to kick off the Cigna approval process now, "
                f"so the member doesn't have to follow up themselves."
            )
        if notif_type == "referral_request":
            return (
                f"Member's plan requires a PCP referral before seeing a specialist. "
                f"Sending a referral request to {provider} on the member's behalf "
                f"so the process starts immediately."
            )
        if notif_type == "follow_up_reminder":
            return (
                f"Appointment booked. Notifying {provider}'s office as a follow-up reminder "
                f"to ensure the prescribing doctor is in the loop."
            )
        return f"Sending a '{notif_type}' notification to {provider}'s office."

    if tool_name == "request_plan_change":
        return (
            f"Member confirmed they want to switch to '{new_plan}'. "
            f"Submitting the plan change request now."
        )

    return f"Calling {tool_name}."


def _build_tool_decision(tool_name: str, result: dict) -> str:
    """
    Returns a 1-3 sentence explanation of WHAT the agent learned from the tool result
    and what decision it makes next based on that result.
    """
    if tool_name == "find_providers":
        if result.get("hmo_gate"):
            traveling = result.get("is_traveling", False)
            pcp       = result.get("pcp_name", "PCP")
            loc       = result.get("current_location", "")
            home      = result.get("home_city", "")
            return (
                f"⛔ HMO gate — {result.get('blocked_specialty')} search blocked, no referral on file. "
                + (f"Member is traveling in {loc} (home: {home}). " if traveling else "")
                + f"Redirecting to book PCP ({pcp}) via {'Telehealth' if traveling else 'In-Person'} first."
            )
        if result.get("emergency"):
            return "⚠️ Emergency detected — directing member to call 911."
        count      = result.get("count", 0)
        top        = result.get("top_pick") or (result.get("providers") or [{}])[0]
        top_name   = top.get("name", "")
        top_reason = top.get("top_pick_reason", "")
        oon        = result.get("oon_fallback", False)
        gate       = result.get("imaging_prior_auth_gate", "")
        city       = result.get("searched_city", "")

        parts = []
        if count == 0:
            return "No providers found in the search area. Will try expanding the radius or alerting the member."
        if oon:
            parts.append(f"No in-network providers found near {city} — showing {count} out-of-network option(s).")
        else:
            parts.append(f"Found {count} in-network provider(s) near {city}.")
        if top_name:
            reason_note = f" ({top_reason})" if top_reason else ""
            parts.append(f"Selected {top_name} as top pick{reason_note}.")
        if "⛔" in gate:
            pa_status = "pending" if "pending" in gate else "not submitted"
            parts.append(
                f"Prior auth is {pa_status} — booking is BLOCKED. "
                f"Will show providers as options only and wait for Cigna approval before scheduling."
            )
        elif "✅" in gate:
            parts.append("Prior auth is approved — proceeding to check availability and book.")
        elif top_name and "⛔" not in gate:
            parts.append(f"Proceeding to check {top_name}'s availability.")
        return " ".join(parts)

    if tool_name == "check_availability":
        provider   = result.get("provider_name", result.get("name", ""))
        date       = result.get("date", "")
        slots      = result.get("slots", [])
        skipped    = result.get("skipped_note", "")
        avail_text = result.get("available_times", [])

        slot_list  = slots or avail_text
        if not slot_list:
            return f"No open slots found for {provider}. Will try the next available day."
        slot_count = len(slot_list)
        slots_str  = ", ".join(str(s) for s in slot_list[:3])
        note       = f" ({skipped})" if skipped else ""
        return (
            f"Found {slot_count} open slot(s) for {provider} on {date}{note}: {slots_str}. "
            f"Presenting these to the member to pick a time."
        )

    if tool_name == "book_appointment":
        status = result.get("status", "")
        if status == "confirmed":
            prov = result.get("provider_name", result.get("provider", ""))
            date = result.get("date", result.get("appointment_date", ""))
            time = result.get("time", result.get("time_slot", ""))
            return f"✅ Appointment confirmed with {prov} on {date} at {time}. Session saved and the member is all set."
        if status == "blocked":
            reason = result.get("reason", "")
            if reason == "prior_auth_required":
                return "⛔ Booking blocked — prior auth not yet approved by Cigna. Showing imaging options for when it clears."
            if reason == "referral_required":
                return "⛔ Booking blocked — PCP referral required and not yet approved. Will book the moment the referral comes through."
            return f"⛔ Booking blocked: {result.get('message', '')[:120]}"
        return f"Booking result: {status}."

    if tool_name == "notify_provider":
        if result.get("sent"):
            notif_type = result.get("type", "notification")
            provider   = result.get("provider", "provider")
            return (
                f"✅ {notif_type.replace('_', ' ').title()} sent to {provider}'s office. "
                f"They will follow up with the insurance company directly."
            )
        return "Notification could not be sent — will retry or inform the member."

    if tool_name == "request_plan_change":
        status = result.get("status", "")
        new_plan = result.get("new_plan", "")
        if status == "submitted":
            return (
                f"✅ Plan change to '{new_plan}' submitted to Cigna for approval. "
                f"A Cigna representative will review and approve the request. "
                f"Member will be notified on next login once approved."
            )
        return f"Plan change result: {status}."

    return ""


# ── ADK Agent ─────────────────────────────────────────────────────────────────
_VERTEX_MODEL    = settings.LLM_MODEL or "gemini-2.0-flash"
_session_service = InMemorySessionService()
APP_NAME         = "adk"


def _get_runner(user_id: str, travel_city: str = "", travel_state: str = "") -> Runner:
    """Cached runner per user. Rebuilt after booking so new booking appears in system prompt."""
    runner_key = f"{user_id}|{travel_city}|{travel_state}"
    if runner_key not in _runners:
        agent = LlmAgent(
            name        = "HealthcareProviderSearchAgent",
            model       = _VERTEX_MODEL,
            description = "Agentic healthcare provider search with booking and memory.",
            instruction = _build_system_prompt(user_id, travel_city, travel_state),
            tools       = [
                FunctionTool(find_providers),
                FunctionTool(notify_provider),
                FunctionTool(check_availability),
                FunctionTool(book_appointment),
                FunctionTool(request_plan_change),
            ],
        )
        _runners[runner_key] = Runner(
            agent           = agent,
            app_name        = APP_NAME,
            session_service = _session_service,
        )
    return _runners[runner_key]


# ── Public API ────────────────────────────────────────────────────────────────
async def run_adk_agent_stream(message: str, user_id: str, travel_city: str = "", travel_state: str = "", previous_plan: str = "", new_plan: str = "") -> AsyncIterator[dict]:
    history = storage.get_history(user_id)

    # Invalidate stale runner on new session so system prompt rebuilds fresh
    if user_id not in _adk_sessions:
        for k in [k for k in list(_runners.keys()) if k.startswith(f"{user_id}|")]:
            _runners.pop(k, None)

    runner = _get_runner(user_id, travel_city=travel_city, travel_state=travel_state)

    history_lines = []
    for t in history[-20:]:
        role    = "user" if t["role"] == "user" else "assistant"
        content = t["content"]
        if role == "assistant" and len(content) > 300:
            content = content[:300] + "..."
        history_lines.append(f"{role}: {content}")

    # ── Build augmented message ───────────────────────────────────────────────
    if message == "__plan_change_greeting__":
        try:
            user = _users.get_user(user_id)
            new_plan = user.insurance_plan
        except Exception:
            previous_plan = ""
            new_plan = ""

        bookings = storage.get_bookings(user_id)
        booking_context = ""
        if bookings:
            booking_lines = []
            for b in bookings[-3:]:
                provider_npi  = b.get("npi", "")
                provider_name = b.get("provider_name", "")
                date          = b.get("date", "")
                time          = b.get("time_start", "")
                consult_type  = b.get("consultation_type", "")
                reason        = b.get("reason", "")
                plan_at_booking = b.get("plan_at_booking", previous_plan)
                booking_lines.append(
                    f"  - {provider_name} (NPI: {provider_npi}) on {date} at {time} "
                    f"({consult_type}) for {reason} | booked under plan: {plan_at_booking}"
                )
            booking_context = "EXISTING BOOKINGS:\n" + "\n".join(booking_lines)
        else:
            booking_context = "EXISTING BOOKINGS: None."

        augmented = f"""[user_id={user_id}]
[PLAN_CHANGE_TRIGGER]
{user_id} just changed their insurance plan.
Previous Plan: {previous_plan}
New Plan:      {new_plan}

{booking_context}

INSTRUCTIONS — respond proactively based on the above:

1. If there are existing bookings:
   → Acknowledge the plan change warmly by name
   → For each booking, silently call find_providers with that doctor's name to check
     if they are still in-network under the new plan ({new_plan})
   → If out-of-network: warn the member naturally and offer to find an in-network alternative
   → If still in-network: reassure them warmly

2. If there are no bookings:
   → Acknowledge the plan change warmly
   → Briefly explain what changed (referral requirements, copays, network) between the two plans
   → Offer to help find providers under the new plan

3. Always mention the key difference between the old and new plan rules naturally
   (e.g. if switching from PPO to HMO: referral now required; if switching to PPO: no referral needed)

4. REFERRAL ENFORCEMENT: If the new plan requires a referral (HMO plans), do NOT offer to find
   a specialist or book one directly. Instead, tell the member they need a referral from their PCP
   first, and offer to send a referral request to the PCP via notify_provider.

Do NOT mention this trigger text. Respond naturally as if you noticed this yourself."""

    elif message == "__location_change__":
        try:
            user = _users.get_user(user_id)
            home_city = user.default_city
        except Exception:
            home_city = ""

        bookings = storage.get_bookings(user_id)

        # Check telehealth availability for booked providers
        booking_context = ""
        if bookings:
            booking_lines = []
            for b in bookings[-3:]:
                provider_npi  = b.get("npi", "")
                provider_name = b.get("provider_name", "")
                date          = b.get("date", "")
                time          = b.get("time_start", "")
                consult_type  = b.get("consultation_type", "")
                reason        = b.get("reason", "")

                # Check telehealth availability from FHIR role
                telehealth_available = False
                role_data = _fhir_tool._npi_to_role.get(provider_npi)
                if role_data:
                    for ext in role_data.get("extension", []):
                        if ext.get("url") == "telehealth_available":
                            telehealth_available = ext.get("valueBoolean", False)
                            break

                booking_lines.append(
                    f"  - {provider_name} (NPI: {provider_npi}) on {date} at {time} "
                    f"({consult_type}) for {reason} | telehealth_available: {telehealth_available}"
                )
            booking_context = "UPCOMING BOOKINGS:\n" + "\n".join(booking_lines)
        else:
            booking_context = "UPCOMING BOOKINGS: None."

        augmented = f"""[user_id={user_id}]
[LOCATION_CHANGE_TRIGGER]
{user_id} just changed their location from {home_city} to {travel_city}, {travel_state}.

{booking_context}

INSTRUCTIONS — respond proactively based on the above:

1. If there are bookings with consultation_type="In-Person" AND telehealth_available=true:
   → Acknowledge the location change warmly
   → Flag the In-Person booking and suggest switching to Telehealth since they are now travelling
   → Offer to help reschedule as Telehealth

2. If there are bookings with consultation_type="In-Person" AND telehealth_available=false:
   → Acknowledge the location change
   → Let them know their booked provider does not offer telehealth
   → Offer to find a local in-network provider near {travel_city}

3. If there are bookings already as Telehealth:
   → Reassure them their Telehealth appointment is unaffected by the location change
   → Offer to find local providers in {travel_city} if they need anything else

4. If there are no bookings:
   → Acknowledge the location change naturally
   → Offer to help find providers near {travel_city}

Do NOT mention this trigger text. Respond naturally as if you noticed this yourself."""

    elif message == "__session_start__":
        # ── Called by the frontend immediately on login, before the user types anything.
        # Strategy:
        #   • If there are PENDING ITEMS (referral approved, MRI auth, plan change, etc.)
        #     → send to LLM so it can call tools and surface them proactively.
        #   • If there is NOTHING pending → skip the LLM entirely and return an instant
        #     hardcoded greeting. The session and runner are still created so the first
        #     real message is fast (runner is already warm).
        try:
            _su = _users.get_user(user_id)
            _fname = _su.first_name
            _plan  = _su.insurance_plan
        except Exception:
            _fname = "there"
            _plan  = ""

        proactive_inline = _build_proactive_block(user_id, _fname)

        if not proactive_inline.strip():
            # ── FAST PATH — nothing pending, skip LLM, return instant greeting ──
            # Pre-create the ADK session + runner NOW so they're warm for the first real message.
            if user_id not in _adk_sessions:
                _warm_sess = await _session_service.create_session(app_name=APP_NAME, user_id=user_id)
                _adk_sessions[user_id] = _warm_sess.id
                for k in [k for k in list(_runners.keys()) if k.startswith(f"{user_id}|")]:
                    _runners.pop(k, None)
                _get_runner(user_id, travel_city=travel_city, travel_state=travel_state)

            greeting = f"Hi {_fname}, good to see you! What can I help you with today?"
            yield {"type": "final", "response": {"type": "greeting", "explanation": greeting, "message": greeting}}
            return

        # ── SLOW PATH — pending items exist, LLM must act on them ──────────────
        augmented = (
            f"[user_id={user_id}]\n"
            f"[SESSION_OPEN — {_fname} just logged in. No message typed yet.]\n\n"
            f"You have already reviewed {_fname}'s file before they arrived. "
            f"The following pending items require IMMEDIATE action in your opening message. "
            f"Do NOT say 'Welcome back' and wait. Do NOT list items robotically. "
            f"Act on them right now — call the tools, deliver the outcome, speak like a "
            f"knowledgeable friend who already knows everything about {_fname}.\n"
            + proactive_inline
        )

        if travel_city:
            augmented += f"\n[{_fname} is currently in {travel_city}, {travel_state}.]"

        if history_lines:
            augmented += "\n\n[Previous sessions summary]\n" + "\n".join(history_lines[-6:])

    else:
        augmented = f"[user_id={user_id}]\n{message}"
        if travel_city:
            augmented += f"\n[TRAVEL_OVERRIDE: {user_id} is currently in {travel_city}, {travel_state}. Always pass travel_city='{travel_city}' and travel_state='{travel_state}' to find_providers for this entire session.]"
        # _is_new_session: fires on the member's FIRST typed message after login.
        # EXCEPTION: if __session_start__ already fired (session is registered), skip this —
        # the proactive block already ran and we don't want to repeat it.
        _is_new_session = user_id not in _adk_sessions
        if _is_new_session:
            try:
                _proactive_user = _users.get_user(user_id)
                _proactive_fname = _proactive_user.first_name
            except Exception:
                _proactive_fname = ""
            proactive_inline = _build_proactive_block(user_id, _proactive_fname)
            if proactive_inline.strip():
                proactive_prefix = (
                    "[SESSION_START — READ THIS BEFORE PROCESSING THE MEMBER'S MESSAGE BELOW]\n"
                    "You have already reviewed this member's file BEFORE they logged in.\n"
                    "You MUST address ALL pending items in your VERY FIRST response.\n"
                    "Do NOT greet generically and wait. Do NOT answer only their question.\n"
                    "You are a proactive healthcare concierge who spotted these items on file already.\n"
                    "IMPORTANT: For ALL pending items — REPORT the status and ASK what they'd like to do next. "
                    "Do NOT call any tools automatically. Do NOT run find_providers or check_availability on your own. "
                    "Simply tell the member what you found and ask: 'Would you like me to help with [action]?' "
                    "Only call tools AFTER the member explicitly replies and asks you to proceed.\n"
                    + proactive_inline
                    + "\n\n[MEMBER'S FIRST MESSAGE — handle this alongside the above pending items]\n"
                )
                augmented = proactive_prefix + augmented
            else:
                augmented = (
                    "[SESSION_START: No pending items. Greet the member warmly by name and handle their request.]\n\n"
                    + augmented
                )
        if history_lines:
            augmented += "\n\n[Conversation so far]\n" + "\n".join(history_lines)

    adk_session_id = _adk_sessions.get(user_id)
    if not adk_session_id:
        sess           = await _session_service.create_session(app_name=APP_NAME, user_id=user_id)
        adk_session_id = sess.id
        _adk_sessions[user_id] = adk_session_id
        # New session = new login — invalidate runner so system prompt rebuilds with latest plan
        for k in [k for k in _runners if k.startswith(f"{user_id}|")]:
            _runners.pop(k, None)


    user_content = Content(role="user", parts=[Part(text=augmented)])

    state = {
        "providers":     [],
        "booking":       None,
        "availability":  None,
        "emergency":     False,
        "partial_texts": [],
    }

    try:
        async with asyncio.timeout(120):
          async for event in runner.run_async(
            user_id=user_id, session_id=adk_session_id, new_message=user_content,
          ):
            if not event.is_final_response() and event.content and event.content.parts:
                partial = "".join(
                    p.text for p in event.content.parts if hasattr(p, "text") and p.text
                )
                if partial.strip():
                    state["partial_texts"].append(partial)
                    yield {"type": "partial_text", "text": partial}

            if event.get_function_calls():
                for fc in event.get_function_calls():
                    labels = {
                        "find_providers":      "🏥 Finding providers…",
                        "notify_provider":     "📨 Notifying provider's office…",
                        "check_availability":  "📅 Checking availability…",
                        "book_appointment":    "✅ Booking appointment…",
                        "request_plan_change": "🔄 Updating insurance plan…",
                    }
                    args = dict(fc.args) if fc.args else {}

                    # ── Rich reasoning: WHY is the agent calling this tool? ──────
                    thought = _build_tool_thought(fc.name, args, state)

                    yield {
                        "type":   "tool_call",
                        "tool":   fc.name,
                        "input":  args,
                        "label":  labels.get(fc.name, fc.name),
                        "thought": thought,
                    }

            if event.get_function_responses():
                for fr in event.get_function_responses():
                    raw = fr.response
                    if isinstance(raw, str):
                        try:    raw = json.loads(raw)
                        except Exception:
                            try:
                                import ast
                                raw = ast.literal_eval(raw)
                            except Exception:
                                raw = {"_raw": raw}
                    if not isinstance(raw, dict):
                        raw = {"_data": raw}

                    if fr.name == "find_providers":
                        if raw.get("emergency"):
                            state["emergency"] = True
                        if raw.get("providers"):
                            state["providers"] = raw["providers"]
                        audit_logger.log_event("PROVIDER_SEARCH", user_id, {
                            "count":     raw.get("count", 0),
                            "specialty": raw.get("specialty", ""),
                        })

                    elif fr.name == "check_availability":
                        state["availability"] = raw

                    elif fr.name == "book_appointment":
                        if raw.get("status") == "confirmed":
                            state["booking"] = raw

                    # ── Rich reasoning: WHAT did the agent learn/decide? ─────────
                    decision = _build_tool_decision(fr.name, raw)

                    yield {"type": "tool_result", "tool": fr.name, "output": raw, "decision": decision}

            if event.is_final_response():
                final_text = ""
                if event.content and event.content.parts:
                    final_text = "".join(
                        p.text for p in event.content.parts if hasattr(p, "text") and p.text
                    )
                # Fallback: LLM streamed the text as partials but the final event
                # has empty content (common after tool calls like request_plan_change).
                # Reconstruct from accumulated partial stream.
                if not final_text.strip() and state["partial_texts"]:
                    final_text = "".join(state["partial_texts"])

                if state["emergency"]:
                    result = {"type": "emergency", "message": final_text, "providers": []}

                elif state["booking"]:
                    result = {
                        "type":    "booking_confirmation",
                        "booking": state["booking"],
                        "message": final_text,
                    }

                elif state["availability"]:
                    result = {
                        "type":         "availability",
                        "availability": state["availability"],
                        "message":      final_text,
                    }

                elif state["providers"]:
                    top = next(
                        (p for p in state["providers"] if p.get("top_pick")),
                        state["providers"][0]
                    )
                    result = {
                        "type":      "provider_results",
                        "providers": state["providers"],
                        "top_pick":  top,
                        "message":   final_text,
                    }

                else:
                    result = {"type": "chat", "explanation": final_text}

                if message not in ("__plan_change_greeting__", "__location_change__"):
                    storage.save_turn(user_id, "user", message)
                storage.save_turn(user_id, "assistant", final_text)

                yield {"type": "final", "response": result}

    except asyncio.TimeoutError:
        yield {"type": "error", "message": "Request timed out — Vertex AI unreachable or GCP credentials expired. Run: gcloud auth application-default login"}
    except Exception as exc:
        import traceback
        traceback.print_exc()
        yield {"type": "error", "message": str(exc)}
