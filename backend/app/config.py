"""
Application settings, loaded from environment.

All secrets and config live here. Importing `settings` gives you a
typed, validated singleton.
"""
from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Companies House
    companies_house_api_key: str = ""
    companies_house_base_url: str = "https://api.company-information.service.gov.uk"
    companies_house_stream_url: str = "https://stream.companieshouse.gov.uk"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Alert channels
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    resend_api_key: str = ""
    alert_from_email: str = "alerts@dennisandassociates.co.uk"
    alert_to_emails: str = ""

    # Enrichment
    google_places_api_key: str = ""
    hunter_api_key: str = ""
    apollo_api_key: str = ""
    clearbit_api_key: str = ""

    # Intent monitoring
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    serpapi_key: str = ""

    # CRM
    hubspot_api_key: str = ""
    pipedrive_api_token: str = ""
    pipedrive_company_domain: str = ""
    zoho_client_id: str = ""
    zoho_client_secret: str = ""

    # Worker schedule
    companies_house_poll_interval_seconds: int = 900
    compliance_scan_interval_seconds: int = 3600

    @field_validator("alert_to_emails")
    @classmethod
    def _strip_emails(cls, v: str) -> str:
        return ",".join(e.strip() for e in v.split(",") if e.strip())

    @property
    def alert_to_email_list(self) -> List[str]:
        return [e for e in self.alert_to_emails.split(",") if e]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
