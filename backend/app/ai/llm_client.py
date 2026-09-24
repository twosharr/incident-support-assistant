import logging
import os
from typing import Optional

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)


class LLMFallbackClient:
    """Lightweight Gemini fallback client for general-purpose questions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or "").strip()
        self.model = (model or settings.GEMINI_MODEL or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()
        self.provider = "Gemini"
        self.base_url = "https://generativelanguage.googleapis.com"
        self.timeout = 30.0
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                logger.exception("Gemini SDK configuration failed: %s", exc)
                self.api_key = ""
                self.client = None

    def is_available(self) -> bool:
        return bool(self.api_key) and self.client is not None

    def get_response(self, user_message: str) -> str:
        if not self.is_available():
            logger.warning("Gemini fallback disabled: GEMINI_API_KEY is missing.")
            return "LLM fallback is currently unavailable."

        system_instruction = (
            "You are a concise technical assistant. "
            "Provide accurate answers in 3 to 6 bullets or 1 to 3 short paragraphs. "
            "Keep responses under approximately 150 words unless the user explicitly requests details. "
            "Prefer concise, actionable technical explanations. "
            "Avoid long introductions, excessive background, and unnecessary conclusions."
        )

        def extract_message(response):
            message = "".join(
                part.text
                for candidate in getattr(response, "candidates", []) or []
                for part in getattr(getattr(candidate, "content", None), "parts", []) or []
                if getattr(part, "text", None)
            ).strip()

            if not message and hasattr(response, "text") and response.text:
                message = response.text.strip()
            return message

        try:
            logger.warning(
                "Gemini request details: provider=%s model=%s key_loaded=%s message=%s",
                self.provider,
                self.model,
                bool(self.api_key),
                user_message,
            )
            message = ""

            for prompt in (user_message, f"Answer briefly in 2 short paragraphs or 3 bullets, under 150 words. User question: {user_message}"):
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.2,
                        "max_output_tokens": 220,
                    },
                )
                message = extract_message(response)
                logger.warning("Gemini parsed response: %s", message[:4000] if message else "<empty>")
                if message:
                    words = message.split()
                    if len(words) >= 15:
                        if len(words) > 150:
                            message = " ".join(words[:150]).rstrip(".,;:") + "..."
                        return message

            if message:
                words = message.split()
                if len(words) > 150:
                    message = " ".join(words[:150]).rstrip(".,;:") + "..."
                return message

        except Exception as exc:  # pragma: no cover - defensive runtime guard
            exception_text = str(exc).lower()
            status_code = getattr(exc, "status_code", None)
            if status_code == 429 or "429" in exception_text or "resource_exhausted" in exception_text or "rate limit" in exception_text or "quota" in exception_text or "temporarily unavailable" in exception_text:
                logger.warning(
                    "Gemini fallback rate-limited. provider=%s model=%s key_loaded=%s exception=%s",
                    self.provider,
                    self.model,
                    bool(self.api_key),
                    exc,
                )
                return "Gemini fallback is temporarily unavailable due to API quota limits. Please retry in a few moments."

            logger.exception(
                "Gemini fallback request failed. provider=%s model=%s key_loaded=%s exception=%s",
                self.provider,
                self.model,
                bool(self.api_key),
                exc,
            )

        return "LLM fallback is currently unavailable."
