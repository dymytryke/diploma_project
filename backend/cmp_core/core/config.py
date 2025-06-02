from typing import Mapping  # Ensure Mapping is imported

from pydantic import ConfigDict, Field  # Ensure Field is imported from pydantic
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    secret_key: str = Field(..., validation_alias="SECRET_KEY")
    algorithm: str = "HS256"  # No env var, uses default
    access_token_expire_minutes: int = Field(
        30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # celery
    celery_broker_url: str = Field(..., validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(
        None, validation_alias="CELERY_RESULT_BACKEND"
    )

    # redis cache
    redis_cache_url: str | None = Field(None, validation_alias="REDIS_CACHE_URL")

    # pulumi (optional)
    pulumi_config_passphrase: str | None = Field(
        None, validation_alias="PULUMI_CONFIG_PASSPHRASE"
    )

    # initial admin
    initial_admin_email: str | None = Field(
        None, validation_alias="INITIAL_ADMIN_EMAIL"
    )
    initial_admin_password: str | None = Field(
        None, validation_alias="INITIAL_ADMIN_PASSWORD"
    )

    # Azure credentials for pulumi_azure_native
    azure_client_id: str = Field(..., validation_alias="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., validation_alias="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(..., validation_alias="AZURE_TENANT_ID")
    azure_subscription_id: str = Field(..., validation_alias="AZURE_SUBSCRIPTION_ID")

    # Grafana
    grafana_base_url: str = Field(..., validation_alias="GRAFANA_BASE_URL")
    grafana_org_id: int = Field(1, validation_alias="GRAFANA_ORG_ID")
    grafana_dashboard_uids: Mapping[str, str] = Field(
        ..., validation_alias="GRAFANA_DASHBOARD_UIDS"
    )
    grafana_kiosk: bool = Field(True, validation_alias="GRAFANA_KIOSK")

    # CORS settings
    cors_origins: list[str] | None = Field(None, validation_alias="CORS_ORIGINS")

    model_config = ConfigDict(
        # env_file=".env", # Keep this commented out
        env_file_encoding="utf-8",
        extra="ignore",
        # It might be beneficial to explicitly tell Pydantic to populate by field name
        # as a fallback if aliases are used, though it should do this by default.
        # populate_by_name=True # For Pydantic v2, this is the default behavior.
    )


# single global instance
settings = Settings()
