from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # For MySQL: mysql+pymysql://user:password@host:3306/dbname
    database_url: str = "sqlite:///./elderly_care.db"
    jwt_secret_key: str = "dev-only-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()
