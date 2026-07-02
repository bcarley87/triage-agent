from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://triage:triage@localhost:5432/triage_agent"
    anthropic_api_key: str = ""
    debug: bool = False


settings = Settings()
