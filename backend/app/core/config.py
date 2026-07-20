import json as _json

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_STR = "http://localhost:3000,http://localhost:5173"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://mami:mami@localhost:5432/mami_db"
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "changeme123"
    # Stored as str so pydantic-settings never tries json.loads() on it.
    # Accepts: comma-separated URLs  OR  a JSON array string like '["url1","url2"]'
    CORS_ORIGINS: str = _DEFAULT_CORS_STR
    RESEND_API_KEY: str = ""                    # Empty = dev fallback (log reset link to console)
    FRONTEND_URL: str = "http://localhost:5173" # Used to construct the reset URL in emails

    @property
    def cors_origins_list(self) -> list[str]:
        v = self.CORS_ORIGINS.strip()
        if not v:
            return _DEFAULT_CORS_STR.split(",")
        if v.startswith("["):
            return _json.loads(v)
        return [x.strip() for x in v.split(",") if x.strip()]


settings = Settings()
