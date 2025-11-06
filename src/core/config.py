from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # OpenRouter LLM Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Model Configuration
    primary_model: str = "anthropic/claude-3.5-sonnet"
    fallback_model_1: str = "openai/gpt-4o"
    fallback_model_2: str = "meta-llama/llama-3.1-70b-instruct"

    # Langfuse Observability (Optional)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None

    # Memory Backend Configuration
    memory_backend: str = "local"  # Options: local (SQLite), databricks (Delta Lake)
    memory_db_path: str = "data/memory.db"

    # FastAPI Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Streamlit Configuration
    streamlit_port: int = 8501
    api_base_url: str = "http://localhost:8000/api/v1"

    # Agent Temperature Configuration
    taa_temperature: float = 0.3
    paa_temperature: float = 0.1
    ema_temperature: float = 0.2

    # Risk Scoring Thresholds
    high_risk_amount: float = 10000.0
    medium_risk_amount: float = 5000.0
    low_risk_amount: float = 1000.0

    # KPI Settings
    kpi_calculation_frequency: str = "daily"  # Options: daily, hourly, realtime
    kpi_retention_days: int = 90

    # Databricks Configuration (Phase 2)
    databricks_workspace_url: str | None = None
    databricks_token: str | None = None
    databricks_catalog: str = "afga_dev"
    databricks_schema_bronze: str = "bronze"
    databricks_schema_silver: str = "silver"
    databricks_schema_gold: str = "gold"

    # Azure Storage (Phase 2)
    azure_storage_account: str | None = None
    azure_storage_key: str | None = None
    azure_container_raw: str = "raw-transactions"
    azure_container_processed: str = "processed-transactions"

    environment: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def fallback_models(self) -> list[str]:
        """Return list of fallback models."""
        return [self.fallback_model_1, self.fallback_model_2]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

