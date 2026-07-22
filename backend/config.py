from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/donation_management"
    SECRET_KEY: str = "3d9b8a7c6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # YOLO Object Detection
    YOLO_MODEL_NAME: str = "yolo26s.pt"
    YOLO_MODEL_PATH: Optional[str] = None
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25

    # SMTP Email Settings — pydantic reads these directly from .env
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@donateai.org"
    SMTP_USE_TLS: bool = True

    # Frontend URL (used in email links)
    FRONTEND_URL: str = "http://localhost:8080"

    # NGO Matching Configuration
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    MATCH_MIN_SCORE: float = 40.0
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.65
    MATCH_NOTIFICATION_THRESHOLD: float = 75.0
    DONATION_MATCH_WAIT_DAYS: int = 30

    WEIGHT_ITEM_MATCH: float = 0.45
    WEIGHT_QUANTITY_FIT: float = 0.20
    WEIGHT_GEOGRAPHIC: float = 0.20
    WEIGHT_PRIORITY: float = 0.15

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
