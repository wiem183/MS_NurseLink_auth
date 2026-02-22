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

    SECRET_KEY: str                           # openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BCRYPT_ROUNDS: int = 12

    ALLOWED_ORIGINS: list[str] = ["*"]


settings = Settings()
