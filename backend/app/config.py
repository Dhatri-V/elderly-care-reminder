from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # For MySQL: mysql+pymysql://user:password@host:3306/dbname
    database_url: str = "sqlite:///./elderly_care.db"
    jwt_secret_key: str = "dev-only-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    telegram_bot_token: str = ""  # alerts are skipped when empty
    missed_after_minutes: int = 30
    run_scheduler: bool = True

    # Tried in order.
    llm_models: str = (
        "gemini/gemini-flash-latest,"  # always Google's current Flash model
        "openrouter/qwen/qwen-2.5-72b-instruct,"
        "openrouter/nvidia/llama-3.1-nemotron-70b-instruct"
    )
    ai_timeout_seconds: float = 60
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    chroma_dir: str = "chroma_data"


settings = Settings()
