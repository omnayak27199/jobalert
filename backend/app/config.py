from __future__ import annotations

import json
from typing import List, Optional, Union

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(origin).strip() for origin in value if str(origin).strip()]
    if isinstance(value, str):
        raw = value.strip().strip("'").strip('"')
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                inner = raw.strip("[]")
                parsed = [
                    origin.strip().strip("'").strip('"')
                    for origin in inner.split(",")
                    if origin.strip()
                ]
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return []


def _sanitize_env_typos() -> None:
    """Map common .env typos before Settings loads."""
    import os

    if os.environ.get("UBLIC_SITE_URL") and not os.environ.get("PUBLIC_SITE_URL"):
        os.environ["PUBLIC_SITE_URL"] = os.environ["UBLIC_SITE_URL"]
    os.environ.pop("UBLIC_SITE_URL", None)


def _env_file_for_settings() -> str | None:
    """In Docker, vars come from compose — skip baked or mounted .env file reads."""
    import os

    if os.path.exists("/.dockerenv"):
        return None
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_for_settings(),
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/jobalert.db"
    fetch_interval_minutes: int = 60
    public_site_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("PUBLIC_SITE_URL", "UBLIC_SITE_URL", "public_site_url"),
    )
    # Union prevents pydantic-settings from JSON-parsing env before our validator runs.
    cors_origins: Union[str, List[str]] = [
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
    smtp_from: str = "alerts@indiagovjob.online"

    # WhatsApp alerts (Twilio)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # Admin upload/fetch (set in production)
    admin_secret: Optional[str] = None
    # Comma-separated emails that receive admin panel access (login + JWT)
    admin_emails: Union[str, List[str]] = []

    # Skip the heavy scrape on container boot (scheduled fetch still runs).
    skip_initial_fetch: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        return _parse_cors_origins(value)

    @field_validator("admin_emails", mode="before")
    @classmethod
    def parse_admin_emails(cls, value: object) -> List[str]:
        parsed = _parse_cors_origins(value)
        return [email.lower() for email in parsed]

    @property
    def admin_email_set(self) -> set[str]:
        return {email.lower() for email in self.admin_emails}

    @model_validator(mode="after")
    def append_public_site_to_cors(self) -> "Settings":
        origins = _parse_cors_origins(self.cors_origins)
        site = self.public_site_url.rstrip("/")
        if site and site not in origins:
            origins.append(site)
        if site.startswith("https://") and not site.startswith("https://www."):
            www = site.replace("https://", "https://www.", 1)
            if www not in origins:
                origins.append(www)
        self.cors_origins = origins
        return self

    @property
    def site_base_url(self) -> str:
        return self.public_site_url.rstrip("/")


_sanitize_env_typos()
settings = Settings()
