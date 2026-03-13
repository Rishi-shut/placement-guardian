import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CLOUD_PROJECT: str = ""
    PUBSUB_TOPIC: str = "gmail-notifications"
    PUBSUB_SUBSCRIPTION: str = "gmail-webhook"
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALARM_DEEP_LINK_SCHEME: str = "placementguardian"
    BACKEND_URL: str = ""

    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_OAUTH_SCOPE: str = "https://www.googleapis.com/auth/gmail.readonly"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if not settings.BACKEND_URL:
        settings.GOOGLE_REDIRECT_URI = "https://placement-guardian-bot-production.up.railway.app/auth/callback"
    else:
        settings.GOOGLE_REDIRECT_URI = f"{settings.BACKEND_URL}/auth/callback"
    return settings


settings = get_settings()
