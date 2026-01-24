import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

load_dotenv()


class Settings(BaseModel):
    # App
    APP_NAME: str = "safeLedger"
    ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Ledger behaviour
    DEFAULT_CURRENCY: str = "NGN"
    MAX_TRANSACTION_AMOUNT: int = 10_000_000
    MIN_TRANSACTION_AMOUNT: float = 0.01

    # SQLAlchemy
    DB_ECHO: bool = False

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Ensure SECRET_KEY is properly set in production."""
        env = os.getenv("ENV", "development")

        if env != "development":
            if not v or v == "dev-only-secret" or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a secure value (min 32 chars) in production"
                )
        return v or "dev-only-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        DATABASE_URL=os.getenv("DATABASE_URL"),
        TEST_DATABASE_URL=os.getenv("TEST_DATABASE_URL"),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-secret"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        ENV=os.getenv("ENV", "development"),
        DB_ECHO=os.getenv("DB_ECHO", "false").lower() == "true",
    )
