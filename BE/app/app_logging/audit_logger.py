import os
import json
from datetime import datetime
from pathlib import Path
from app.config import settings


class AuditLogger:
    """
    Central audit logger with DB toggle.
    Logs to files when AUDIT_LOG_SAVE_TO_DB=false, DB when true.
    """

    def __init__(self):
        self.save_to_db = settings.AUDIT_LOG_SAVE_TO_DB
        if not self.save_to_db:
            Path(settings.AUDIT_LOG_DIR).mkdir(parents=True, exist_ok=True)
            Path(f"{settings.CONVERSATION_LOG_DIR}/json").mkdir(parents=True, exist_ok=True)
            Path(f"{settings.CONVERSATION_LOG_DIR}/txt").mkdir(parents=True, exist_ok=True)
            Path(settings.EXPLAINABILITY_LOG_DIR).mkdir(parents=True, exist_ok=True)

    def log_event(self, event: str, user_id: str, data: dict = None):
        """Log a system audit event."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event":     event,
            "user_id":   user_id,
            "data":      data or {},
        }
        if self.save_to_db:
            self._save_to_db("audit", entry)
        else:
            self._append_json(f"{settings.AUDIT_LOG_DIR}/audit_{self._today()}.json", entry)

    def log_conversation_turn(self, user_id: str, session_id: str, role: str, message: str):
        """Log a single conversation turn (user or assistant message)."""
        turn = {
            "timestamp":  datetime.utcnow().isoformat(),
            "user_id":    user_id,
            "session_id": session_id,
            "role":       role,
            "message":    message,
        }
        if self.save_to_db:
            self._save_to_db("conversation", turn)
        else:
            json_file = f"{settings.CONVERSATION_LOG_DIR}/json/conv_{user_id}_{self._today()}.json"
            self._append_json(json_file, turn)

            txt_file = f"{settings.CONVERSATION_LOG_DIR}/txt/conv_{user_id}_{self._today()}.txt"
            self._append_txt(txt_file, turn)

    def log_clinical_reasoning(self, user_id: str, session_id: str, reasoning: dict):
        """Log clinical reasoning decision."""
        entry = {
            "timestamp":  datetime.utcnow().isoformat(),
            "user_id":    user_id,
            "session_id": session_id,
            "reasoning":  reasoning,
        }
        if self.save_to_db:
            self._save_to_db("explainability", entry)
        else:
            self._append_json(f"{settings.EXPLAINABILITY_LOG_DIR}/explain_{self._today()}.json", entry)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _today(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _append_json(self, filepath: str, entry: dict):
        """Append JSON entry to file (one line per entry)."""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _append_txt(self, filepath: str, turn: dict):
        """Append human-readable conversation turn to txt file."""
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=== Provider Search Conversation ===\n")
                f.write(f"User ID: {turn['user_id']} | Session: {turn['session_id']}\n")
                f.write("=" * 50 + "\n\n")

        with open(filepath, "a", encoding="utf-8") as f:
            ts   = datetime.fromisoformat(turn["timestamp"]).strftime("%H:%M:%S")
            icon = "👤" if turn["role"] == "user" else "🤖"
            role = "Patient" if turn["role"] == "user" else "Assistant"
            msg  = turn["message"][:500]
            f.write(f"[{ts}] {icon} {role}: {msg}\n")

    def _save_to_db(self, table: str, entry: dict):
        """Future: save to MySQL/PostgreSQL."""
        pass


# Singleton
audit_logger = AuditLogger()
