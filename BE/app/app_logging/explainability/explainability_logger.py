from app.app_logging.audit_logger import audit_logger


class ExplainabilityLogger:
    """
    Logs clinical reasoning decisions — specialty chosen, urgency, confidence, reasoning.
    Delegates to AuditLogger for actual file/DB write.
    """

    def log(
        self,
        user_id:    str,
        session_id: str,
        specialty:  str,
        urgency:    str,
        care_type:  str,
        confidence: float,
        reasoning:  str,
        providers_found: int = 0,
        in_network_count: int = 0,
        first_aid:  list = None,
    ):
        audit_logger.log_clinical_reasoning(
            user_id    = user_id,
            session_id = session_id,
            reasoning  = {
                "specialty":        specialty,
                "urgency":          urgency,
                "care_type":        care_type,
                "confidence":       confidence,
                "reasoning":        reasoning,
                "providers_found":  providers_found,
                "in_network_count": in_network_count,
                "first_aid_given":  bool(first_aid),
            },
        )


explainability_logger = ExplainabilityLogger()
