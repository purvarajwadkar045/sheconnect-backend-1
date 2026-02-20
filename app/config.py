from pydantic_settings import BaseSettings, SettingsConfigDict
import os
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    OTP_SECRET_KEY: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str
    MAIL_PORT: int = 587

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()