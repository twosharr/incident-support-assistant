import os
from pathlib import Path

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8")

    @staticmethod
    def _read_env_file(env_path: str | Path) -> dict[str, str]:
        path = Path(env_path)
        if not path.exists():
            return {}

        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = (part.strip() for part in line.split("=", 1))
            if not key:
                continue

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            values[key] = value

        return values

    @field_validator("GEMINI_API_KEY", "GEMINI_MODEL", "GROQ_API_KEY", "GROQ_MODEL", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    # App
    APP_NAME: str = "AI Incident Support Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Bot Framework (required for real Teams integration)
    MICROSOFT_APP_ID: str = ""
    MICROSOFT_APP_PASSWORD: str = ""

    # CORS - allow frontend
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    # Jira Cloud Integration (defaults for private repo team access)
    JIRA_DOMAIN: str = "incidentsupportdemo.atlassian.net"
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = "your_jira_api_token_here"  # Replace with your actual Jira API token
    JIRA_PROJECT_KEY: str = "SCRUM"

    # LLM fallback provider configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # Legacy compatibility only; runtime execution should use Gemini
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Data paths — resolve relative to this file's parent (backend/)
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

    def __init__(self, **values):
        super().__init__(**values)

        env_values = self._read_env_file(ENV_FILE)
        for field_name, field_value in env_values.items():
            if field_name in self.model_fields and not getattr(self, field_name, None):
                setattr(self, field_name, field_value)

        if self.GEMINI_API_KEY:
            self.GEMINI_API_KEY = self.GEMINI_API_KEY.strip()
        if self.GEMINI_MODEL:
            self.GEMINI_MODEL = self.GEMINI_MODEL.strip()

        if self.GROQ_API_KEY:
            self.GROQ_API_KEY = self.GROQ_API_KEY.strip()
        if self.GROQ_MODEL:
            self.GROQ_MODEL = self.GROQ_MODEL.strip()


settings = Settings()
