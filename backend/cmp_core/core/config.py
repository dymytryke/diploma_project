from typing import Mapping

from dotenv import load_dotenv
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

load_dotenv(override=True)


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # celery
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(None, env="CELERY_RESULT_BACKEND")

    # redis cache
    redis_cache_url: str | None = Field(None, env="REDIS_CACHE_URL")

    # pulumi (optional)
    pulumi_config_passphrase: str | None = Field(None, env="PULUMI_CONFIG_PASSPHRASE")

    # initial admin
    initial_admin_email: str | None = Field(None, env="INITIAL_ADMIN_EMAIL")
    initial_admin_password: str | None = Field(None, env="INITIAL_ADMIN_PASSWORD")

    # Azure credentials for pulumi_azure_native
    azure_client_id: str = Field(..., env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., env="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(..., env="AZURE_TENANT_ID")
    azure_subscription_id: str = Field(..., env="AZURE_SUBSCRIPTION_ID")

    # Grafana
    grafana_base_url: str = Field(..., env="GRAFANA_BASE_URL")
    grafana_org_id: int = Field(1, env="GRAFANA_ORG_ID")
    grafana_dashboard_uids: Mapping[str, str] = Field(..., env="GRAFANA_DASHBOARD_UIDS")
    grafana_kiosk: bool = Field(True, env="GRAFANA_KIOSK")

    # CORS settings
    cors_origins: list[str] | None = Field(
        None, env="CORS_ORIGINS"
    )  # List of allowed origins for CORS

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# single global instance
settings = Settings()
