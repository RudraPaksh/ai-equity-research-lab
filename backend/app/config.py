from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    twelve_data_api_key: str = ""
    fmp_api_key: str = ""
    upstox_access_token: str | None = None
    sec_user_agent: str = "AI-Equity-Lab contact@example.com"
    cors_origins: str = "http://localhost:4200"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
