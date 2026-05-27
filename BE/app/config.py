import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_ENV = os.getenv("APP_ENV", "local")

    # GCP / Vertex AI
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCP_REGION     = os.getenv("GCP_REGION", "us-central1")

    # LLM
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

    # FHIR
    FHIR_MODE     = os.getenv("FHIR_MODE", "memory")
    FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "")

    # Storage backend — "local" or "gcs"
    STORAGE_BACKEND    = os.getenv("STORAGE_BACKEND", "gcs")
    GCS_BUCKET_NAME    = os.getenv("GCS_BUCKET_NAME", "provider_search_applicationstore")

    # Logging
    AUDIT_LOG_SAVE_TO_DB   = os.getenv("AUDIT_LOG_SAVE_TO_DB", "false").lower() == "true"
    AUDIT_LOG_DIR          = os.getenv("AUDIT_LOG_DIR",          "logs/audit")
    CONVERSATION_LOG_DIR   = os.getenv("CONVERSATION_LOG_DIR",   "logs/conversation")
    EXPLAINABILITY_LOG_DIR = os.getenv("EXPLAINABILITY_LOG_DIR", "logs/explainability")


settings = Settings()
