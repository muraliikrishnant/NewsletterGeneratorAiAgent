import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env as early as possible so Settings picks up values at import time
load_dotenv()


def _env_first(*keys: str, default: str | None = None) -> str | None:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            return v
    return default


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

    # Style & voice
    style_name: str = os.getenv("STYLE_NAME", "bartlett_hormozi")
    style_examples_count: int = int(os.getenv("STYLE_EXAMPLES_COUNT", "3"))
    voice_polish: bool = os.getenv("VOICE_POLISH", "true").lower() in {"1", "true", "yes", "on"}
    voice_polish_passes: int = int(os.getenv("VOICE_POLISH_PASSES", "1"))

    # Word limits
    min_words: int = int(os.getenv("MIN_WORDS", "100"))
    max_words: int = int(os.getenv("MAX_WORDS", "5000"))

    # Local image generation (optional)
    image_provider: str = os.getenv("IMAGE_PROVIDER", "tavily")  # 'tavily' or 'auto1111'
    auto1111_url: str = os.getenv("AUTO1111_URL", "http://127.0.0.1:7860")
    image_base_url: str | None = os.getenv("IMAGE_BASE_URL")
    image_storage_dir: str = os.getenv("IMAGE_STORAGE_DIR", "generated_images")
    image_count: int = int(os.getenv("IMAGE_COUNT", "2"))
    image_width: int = int(os.getenv("IMAGE_WIDTH", "768"))
    image_height: int = int(os.getenv("IMAGE_HEIGHT", "512"))
    image_steps: int = int(os.getenv("IMAGE_STEPS", "20"))
    image_cfg_scale: float = float(os.getenv("IMAGE_CFG_SCALE", "7"))
    image_sampler: str = os.getenv("IMAGE_SAMPLER", "Euler")

    # Gemini
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    # Research (Tavily)
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

    # Email
    smtp_host: str = _env_first("SMTP_HOST", "SMTP_SERVER", default="smtp.gmail.com") or "smtp.gmail.com"
    smtp_port: int = int(_env_first("SMTP_PORT", default="587") or "587")
    smtp_username: str | None = _env_first("SMTP_USERNAME")
    smtp_password: str | None = _env_first("SMTP_PASSWORD")
    imap_host: str = _env_first("IMAP_HOST", "IMAP_SERVER", default="imap.gmail.com") or "imap.gmail.com"
    imap_port: int = int(_env_first("IMAP_PORT", default="993") or "993")
    imap_username: str | None = _env_first("IMAP_USERNAME")
    imap_password: str | None = _env_first("IMAP_PASSWORD")

    # App
    from_name: str = os.getenv("FROM_NAME", "TARS Group")
    from_email: str | None = _env_first("FROM_EMAIL", "EMAIL_SENDER")
    default_recipients: List[str] = field(default_factory=_default_recipients)
    poll_interval_seconds: int = int(_env_first("POLL_INTERVAL", "HITL_POLL_INTERVAL", default="30") or "30")
    poll_timeout_minutes: int = int(_env_first("POLL_TIMEOUT", "HITL_TIMEOUT_MINUTES", default="120") or "120")
    max_revisions: int = int(os.getenv("MAX_REVISIONS", "3"))

    # Email sender options (optional)
    email_sender: str = os.getenv("EMAIL_SENDER", "smtp")
    resend_api_key: str | None = os.getenv("RESEND_API_KEY")


settings = Settings()
