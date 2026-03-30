from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "NurseLink Auth Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BCRYPT_ROUNDS: int = 12

    ALLOWED_ORIGINS: list[str] = ["*"]

    # Profile microservice
    PROFILE_SERVICE_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str = "02704bbc412e81b76f28c0e14a7a8263db15c43e144b10df9c65e254518c2d1a"

    # ── SMTP (email sending) ───────────────────────────────────────────────
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USER: str          # your Gmail address
    SMTP_PASSWORD: str      # your 16-char Gmail App Password
    SMTP_FROM: str          # e.g. "NurseLink <yourname@gmail.com>"

    # ── OTP settings ──────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    RESET_TOKEN_EXPIRE_MINUTES: int = 15


settings = Settings()