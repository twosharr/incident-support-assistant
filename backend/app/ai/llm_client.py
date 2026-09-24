import logging
import os
import re
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

    def _trim_to_sentence_boundaries(self, message: str, max_words: int = 180) -> str:
        text = (message or "").strip()
        if not text:
            return text

        if len(text.split()) <= max_words:
            return text

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and any(line.lstrip().startswith(("•", "-", "*")) for line in lines):
            kept_lines = []
            used_words = 0
            for line in lines:
                line_words = line.split()
                if not line_words:
                    continue
                if line.lstrip().startswith(("•", "-", "*")):
                    if used_words + len(line_words) <= max_words:
                        kept_lines.append(line)
                        used_words += len(line_words)
                    else:
                        break
                else:
                    if used_words + len(line_words) <= max_words:
                        kept_lines.append(line)
                        used_words += len(line_words)
                    else:
                        break
            if kept_lines:
                return "\n".join(kept_lines).strip()

        sentences = re.split(r"(?<=[.!?])\s+", text)
        kept_sentences = []
        used_words = 0
        for sentence in sentences:
            sentence_words = sentence.split()
            if not sentence_words:
                continue
            if used_words + len(sentence_words) <= max_words:
                kept_sentences.append(sentence)
                used_words += len(sentence_words)
            else:
                break

        if kept_sentences:
            return " ".join(kept_sentences).strip()

        return " ".join(text.split()[:max_words]).rstrip(".,;:") + "."

    def _normalize_bullets(self, message: str) -> str:
        lines = []
        for line in (message or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("* ") or stripped.startswith("- "):
                lines.append("• " + stripped[2:].lstrip())
            else:
                lines.append(line)
        return "\n".join(lines).strip()

    def _is_complete_response(self, message: str) -> bool:
        text = (message or "").strip()
        if not text or len(text.split()) < 10:
            return False
        if text.endswith("...") or text.endswith("…"):
            return False
        if not re.search(r"[.!?]$", text):
            return False
        return True

    def get_response(self, user_message: str) -> str:
        if not self.is_available():
            logger.warning("Gemini fallback disabled: GEMINI_API_KEY is missing.")
            return "LLM fallback is currently unavailable."

        system_instruction = (
            "You are a concise technical assistant. "
            "Provide complete, accurate answers. "
            "Keep responses approximately 80-150 words. "
            "Prefer 3 to 5 bullet points or 1 to 2 short paragraphs. "
            "Do not write long essays. "
            "Do not leave sentences incomplete."
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

        prompt_variants = [
            (
                f"Answer completely and concisely. Use 1 short intro sentence and 3-5 bullet points. "
                f"Keep the total length around 80-150 words. Each bullet must be a complete sentence. "
                f"Do not leave sentences unfinished. User question: {user_message}"
            ),
            (
                f"Provide a complete, concise answer using exactly 4 bullet points. "
                f"Each bullet must be a complete sentence. Keep it under 120 words total. "
                f"Do not cut off any sentence. User question: {user_message}"
            ),
        ]

        try:
            logger.warning(
                "Gemini request details: provider=%s model=%s key_loaded=%s message=%s",
                self.provider,
                self.model,
                bool(self.api_key),
                user_message,
            )

            for prompt in prompt_variants:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.2,
                        "max_output_tokens": 1024,
                    },
                )
                message = extract_message(response)
                logger.warning("Gemini parsed response: %s", message[:4000] if message else "<empty>")
                if message and self._is_complete_response(message):
                    return self._normalize_bullets(self._trim_to_sentence_boundaries(message))

            if message:
                return self._normalize_bullets(self._trim_to_sentence_boundaries(message))

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
