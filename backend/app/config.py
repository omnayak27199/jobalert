from __future__ import annotations

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/jobalert.db"
    fetch_interval_minutes: int = 60
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # JWT auth
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # LLM (OpenAI-compatible API)
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_enabled: bool = True

    # Email alerts (SMTP)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "alerts@indiajob.in"

    # WhatsApp alerts (Twilio)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # Admin upload/fetch (set in production)
    admin_secret: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
