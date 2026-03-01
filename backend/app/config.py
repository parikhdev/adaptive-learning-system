# backend/app/config.py

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env is at project root: adaptive-learning-system/.env
# backend/app/config.py → go up THREE levels → project root/.env
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    DB_HOST: str
    DB_PORT: int = 6543
    DB_NAME: str = "postgres"
    DB_USER: str
    DB_PASSWORD: str

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS: int = 512
    GROQ_TEMPERATURE: float = 0.3

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()