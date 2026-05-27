from google import genai
from google.genai import types
from app.config import settings


class LLMService:
    """
    Central LLM abstraction for all agents.
    Uses google-genai SDK with Vertex AI backend (ADC).
    No API key required — relies on GOOGLE_GENAI_USE_VERTEXAI=1 + ADC.
    """

    def __init__(self):
        self._client = genai.Client(
            vertexai=True,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_REGION,
        )
        self._model = settings.LLM_MODEL or "gemini-2.5-flash"

    def generate_text(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
