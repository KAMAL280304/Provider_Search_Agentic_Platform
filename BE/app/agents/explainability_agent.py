from app.services.llm_service import LLMService


class ExplainabilityAgent:
    """
    Generates a warm, human-sounding 2-3 sentence explanation of the provider
    search results. Uses LLM to produce natural dialogue, not template bullets.
    """

    def __init__(self):
        self.llm = LLMService()

    def run(self, context: dict, providers: list = None, fallback: dict = None) -> str:
        specialty = context.get("primary_specialty", "a specialist")
        urgency   = context.get("urgency", "routine")
        care_type = context.get("care_type", "either")
        providers = providers or []

        in_net  = sum(1 for p in providers if p.get("network_status") == "in_network")
        out_net = len(providers) - in_net
        total   = len(providers)

        fallback_strategy = (fallback or {}).get("strategy", "none")

        prompt = f"""You are a warm, empathetic healthcare assistant. Write a 2-3 sentence plain-English
summary of these provider search results to share with the member. Sound like a helpful friend, not a system.

Search context:
- Specialty found: {specialty}
- Urgency: {urgency}
- Care type preference: {care_type}
- Total providers found: {total}
- In-network: {in_net}
- Out-of-network: {out_net}
- Fallback strategy: {fallback_strategy}

Rules:
- Do NOT use bullet points, markdown, or headers
- Do NOT use technical jargon
- If urgency is urgent, gently emphasize they should be seen soon
- If urgency is emergency, this function won't be called — skip
- If in_net > 0, mention that in-network options are available (saves money)
- If fallback_strategy is include_out_of_network, mention costs may be higher
- If fallback_strategy is expand_radius, mention providers are a bit further out
- Keep it to 2-3 sentences max
- End warmly

Write only the summary, nothing else."""

        try:
            return self.llm.generate_text(prompt).strip()
        except Exception:
            # Fallback to simple human sentence
            if in_net > 0:
                return f"I found {total} {specialty} providers for you, with {in_net} in-network options that'll keep your costs down."
            return f"I found {total} {specialty} providers. Some may be out-of-network, so costs could vary — worth checking with your insurer."
