import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

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
    JIRA_EMAIL: str = "associatewithtushar@gmail.com"
    JIRA_API_TOKEN: str = "ATATT3xFfGF0swvjER33fUvMi5NbFpXnpah1gt9xopDXDGBiQCNFvA6HVHjShuFbFyMayp2tcM350lRuGiHSopdfZYPXrmVPmMPW5QQ2TmhQ2P-4kCWxfWOPEJeCXMpgz2bqJaJaOZlOU_Nt7jhZ7pvAVQpwHtiAMHhMsEE5mjIEif_oPnTLYgc=DC56CEDC"
    JIRA_PROJECT_KEY: str = "SCRUM"

    # Data paths — resolve relative to this file's parent (backend/)
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


settings = Settings()
