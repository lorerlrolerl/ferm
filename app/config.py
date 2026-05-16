import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/ferm.db")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    APP_NAME: str = "ferm"


settings = Settings()