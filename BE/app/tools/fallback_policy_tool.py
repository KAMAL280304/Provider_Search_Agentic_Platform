class FallbackPolicyTool:
    """
    Decides fallback strategies based on provider results.
    Chain: out_of_network → telehealth → expand_radius → none
    """

    def evaluate(self, ranked_providers: list, clinical_context: dict) -> dict:
        if not ranked_providers:
            care_type = clinical_context.get("care_type", "either")
            if care_type in ("telehealth", "either"):
                return {"strategy": "prefer_telehealth"}
            return {"strategy": "expand_radius"}

        in_network = [p for p in ranked_providers if p.get("network_status") == "in_network"]

        if not in_network:
            return {"strategy": "include_out_of_network"}

        far_providers = [p for p in ranked_providers if p.get("distance_miles") and p["distance_miles"] > 20]

        if far_providers and len(far_providers) == len(ranked_providers):
            # Only trigger expand_radius if ALL providers are far — not just some
            care_type = clinical_context.get("care_type", "either")
            if care_type in ("telehealth", "either"):
                return {"strategy": "prefer_telehealth"}
            return {"strategy": "expand_radius"}

        return {"strategy": "none"}
