import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/ferm.db")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    APP_NAME: str = os.getenv("APP_NAME", "fermlog")

    # Seeding
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@ferm.local")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")


settings = Settings()
