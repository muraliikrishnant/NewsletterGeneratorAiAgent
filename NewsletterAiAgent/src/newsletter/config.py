import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env as early as possible so Settings picks up values at import time
load_dotenv()


def _default_recipients() -> List[str]:
    val = os.getenv("RECIPIENTS", "").strip()
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


@dataclass
class Settings:
    # LLM
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")  # 'ollama' or 'gemini'

    # Gemini
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Research (Tavily)
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

    # Email
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    imap_host: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_port: int = int(os.getenv("IMAP_PORT", "993"))
    imap_username: str | None = os.getenv("IMAP_USERNAME")
    imap_password: str | None = os.getenv("IMAP_PASSWORD")

    # App
    from_name: str = os.getenv("FROM_NAME", "TARS Group")
    from_email: str | None = os.getenv("FROM_EMAIL")
    default_recipients: List[str] = field(default_factory=_default_recipients)
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL", "30"))
    poll_timeout_minutes: int = int(os.getenv("POLL_TIMEOUT", "120"))
    max_revisions: int = int(os.getenv("MAX_REVISIONS", "3"))


settings = Settings()
