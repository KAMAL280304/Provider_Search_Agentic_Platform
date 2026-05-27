from app.tools.fallback_policy_tool import FallbackPolicyTool


class CareNavigationAgent:
    """
    Evaluates provider results and decides the appropriate fallback strategy.
    """

    _STRATEGY_MESSAGES = {
        "prefer_telehealth":      "Available providers are far from you. A telehealth visit may be faster and more convenient.",
        "include_out_of_network": "No in-network providers were found for your plan. Showing out-of-network providers — costs may be higher. Contact your insurer to check coverage.",
        "expand_radius":          "No providers were found nearby. Consider expanding your search to a wider area or trying telehealth.",
        "none":                   "In-network providers are available near you.",
    }

    def __init__(self):
        self.policy = FallbackPolicyTool()

    def run(self, providers: list, clinical_context: dict, user=None, session: dict = None) -> dict:
        decision = self.policy.evaluate(providers, clinical_context)
        strategy = decision["strategy"]

        return {
            "fallback": strategy.upper() if strategy != "none" else "NONE",
            "strategy": strategy,
            "message":  self._STRATEGY_MESSAGES.get(strategy, ""),
        }
