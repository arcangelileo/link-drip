from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LinkDrip"
    app_url: str = "http://localhost:8000"
    secret_key: str = "change-me-to-a-random-secret-key"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./linkdrip.db"

    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
