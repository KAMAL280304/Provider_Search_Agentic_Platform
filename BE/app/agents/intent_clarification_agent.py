import json
from typing import Dict, Any
from app.services.llm_service import LLMService


class IntentClarificationAgent:

    def __init__(self):
        self.llm = LLMService()

    def run(self, message: str, user=None, session: dict = None) -> Dict[str, Any]:

        if not message or len(message.strip()) < 3:
            return {
                "intent_clear": False,
                "clarification_question": "Could you describe what kind of medical help you are looking for?"
            }

        history          = self._build_history(session)
        medical_history  = (session or {}).get("medical_history", {})
        conditions       = medical_history.get("conditions", [])
        past_appts       = medical_history.get("past_appointments", [])
        medications      = medical_history.get("current_medications", [])

        # Build a compact "what we know about this member" block
        known_block = ""
        if conditions:
            known_block += f"\nMember's known conditions: {', '.join(conditions)}"
        if medications:
            known_block += f"\nCurrent medications: {', '.join(medications)}"
        if past_appts:
            recent = sorted(past_appts, key=lambda x: x.get("date", ""), reverse=True)[:3]
            known_block += "\nRecent doctor visits: " + "; ".join(
                f"{a['doctor_name']} ({a['specialty']}) for {a['reason']}" for a in recent
            )

        prompt = f"""You are a warm, empathetic medical intake assistant. You already know this member's
medical background. Use that knowledge to ask smarter, more personal questions.

WHAT YOU KNOW ABOUT THIS MEMBER:{known_block if known_block else " (new member, no history)"}

SCREENING PHILOSOPHY:
- If the symptom matches or could relate to a known condition, acknowledge it naturally
  Example: "That sounds like it could be related to your migraines — is this similar to what you've had before?"
- Each question must dig deeper into the specific problem described
- Stop asking when you have enough to confidently identify the right specialist
- Maximum 3 questions total across the whole conversation

WHEN TO DECLARE INTENT CLEAR:
1. Primary symptom and location/nature is clear
2. Duration is known
3. At least ONE qualifying detail: severity, triggers, pattern, or connection to known history
4. If the patient has answered 3+ questions already — declare clear regardless

WHEN TO ASK ANOTHER QUESTION:
- Duration is missing
- Symptom could route to very different specialties and one more detail would decide it
- The answer given was vague and added no clinical value

QUESTION RULES:
- Ask only ONE question per turn
- If member has a known condition related to the symptom, reference it in the question
- Never ask about insurance, location, or personal details
- Never repeat information already given
- Sound like a caring friend, not a form

Conversation so far:
{history}
Patient (latest): {message}

First silently count how many screening questions have already been asked and answered.
Then decide: do you have enough, or do you need one more specific question?

Respond ONLY with valid JSON:
{{
  "intent_clear": true or false,
  "clarification_question": "your next warm specific question, or null if intent is clear",
  "screening_summary": "brief summary of what you know (only when intent_clear is true)"
}}"""

        try:
            raw     = self.llm.generate_text(prompt)
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed  = json.loads(cleaned)
            return {
                "intent_clear":           bool(parsed.get("intent_clear", False)),
                "clarification_question": parsed.get("clarification_question"),
                "screening_summary":      parsed.get("screening_summary", ""),
            }
        except Exception:
            return {
                "intent_clear": False,
                "clarification_question": "Could you tell me more — what does it feel like and how long have you had it?",
                "screening_summary": "",
            }

    def _build_history(self, session: dict) -> str:
        if not session:
            return "(no prior conversation)"
        lines = []
        for turn in session.get("history", []):
            role    = "Patient"   if turn["role"] == "user"      else "Assistant"
            content = turn["content"]
            if role == "Assistant" and len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "(no prior conversation)"
