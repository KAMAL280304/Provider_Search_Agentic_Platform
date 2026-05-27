import json
from typing import Dict, Any
from app.services.llm_service import LLMService
from app.services.nucc_taxonomy_service import NUCCTaxonomyService


class ClinicalReasoningAgent:
    """
    Clinical Reasoning Agent.
    Reasons over the full screened conversation to map symptoms
    to the most precise specialist — using all context gathered
    during the dynamic screening phase.
    """

    def __init__(self):
        self.llm  = LLMService()
        self.nucc = NUCCTaxonomyService()

    def run(self, message: str, user=None, session: dict = None) -> Dict[str, Any]:

        conversation = self._build_conversation(session)

        prompt = f"""You are a senior medical triage physician making a specialist referral decision.

You have conducted a thorough intake screening with the patient. Read the FULL conversation carefully
and use ALL the clinical details gathered to make the most precise routing decision.

Conversation:
{conversation}

Your reasoning must:
- Consider ALL symptoms, duration, severity, triggers, and medical history mentioned
- Distinguish between similar specialties (e.g. Dermatology vs Allergy & Immunology vs Family Medicine)
- Choose the MOST PRECISE specialist — not just the safest generic one
- Explain your reasoning including why you chose this specialty over other possibilities
- Assess urgency based on the complete clinical picture
- If the condition involves a minor injury, burn, cut, sprain, or accident, provide concise first aid steps

Return ONLY valid JSON:
{{
  "primary_specialty": "most precise specialty name",
  "secondary_specialties": ["other relevant specialties if applicable"],
  "urgency": "routine or urgent or emergency",
  "care_type": "telehealth or in_person or either",
  "confidence": 0.0 to 1.0,
  "reasoning": "detailed reasoning — what symptoms led to this decision and why this specialty over others",
  "first_aid": ["step 1", "step 2", "step 3"] or null if not a minor injury/burn/accident
}}

Rules:
- primary_specialty: precise US specialty (e.g. Cardiology, Neurology, Dermatology — NEVER use 'Emergency Medicine'). For emergencies, use the underlying specialty and set urgency to 'emergency'.
- urgency: "emergency" ONLY for life-threatening presentations. "urgent" for same-day needs. "routine" otherwise.
- care_type: decide based on what the condition actually requires clinically:
  "in_person" — anything needing physical exam, lab work, imaging, or hands-on assessment
                 (fever, chest pain, abdominal pain, injuries, joint pain, neurological symptoms)
  "telehealth" — conditions where a visual or verbal consult is sufficient
                 (visible skin conditions where photos suffice, mild cold/cough with no red flags,
                  mental health therapy, medication refills, follow-up consultations)
  "either"     — only when both genuinely work equally well clinically
- confidence: higher when symptoms are specific and clear, lower when ambiguous
- reasoning: must be detailed enough for the agent to explain the decision to the patient in plain language
- first_aid: only for minor injuries/burns/cuts/sprains/accidents — practical immediate steps the patient can take RIGHT NOW before seeing a doctor. null for all other conditions."""

        result = self._safe_default()

        try:
            raw     = self.llm.generate_text(prompt)
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed  = json.loads(cleaned)
            result  = {
                "primary_specialty":     parsed.get("primary_specialty", "Family Medicine"),
                "secondary_specialties": parsed.get("secondary_specialties", []),
                "urgency":               parsed.get("urgency", "routine"),
                "care_type":             parsed.get("care_type", "either"),
                "confidence":            float(parsed.get("confidence", 0.7)),
                "reasoning":             parsed.get("reasoning", ""),
                "first_aid":             parsed.get("first_aid") or [],
            }
        except Exception:
            pass

        result["nucc_codes"] = self.nucc.get_related_codes(result["primary_specialty"])

        if session is not None:
            session["clinical_reasoning"] = result

        return result

    def _build_conversation(self, session: dict) -> str:
        if not session:
            return "(no conversation)"
        lines = []
        for turn in session.get("history", []):
            role    = "Patient"   if turn["role"] == "user"      else "Assistant"
            content = turn["content"]
            # Keep assistant screening questions but trim long provider dumps
            if role == "Assistant" and len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "(no conversation)"

    def _safe_default(self) -> Dict[str, Any]:
        return {
            "primary_specialty":     "Family Medicine",
            "secondary_specialties": [],
            "urgency":               "routine",
            "care_type":             "either",
            "confidence":            0.5,
            "reasoning":             "Defaulted to Family Medicine due to parsing error.",
            "first_aid":             [],
        }
