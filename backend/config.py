import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/donation_management"
    )
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "3d9b8a7c6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c"  # fallback default
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "yolov8s.pt")
    YOLO_CONFIDENCE_THRESHOLD: float = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.25"))

    # NGO matching configurations
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    MATCH_MIN_SCORE: float = float(os.getenv("MATCH_MIN_SCORE", "40.0"))
    SEMANTIC_SIMILARITY_THRESHOLD: float = float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.65"))
    MATCH_NOTIFICATION_THRESHOLD: float = float(os.getenv("MATCH_NOTIFICATION_THRESHOLD", "75.0"))
    
    WEIGHT_ITEM_MATCH: float = 0.45
    WEIGHT_QUANTITY_FIT: float = 0.20
    WEIGHT_GEOGRAPHIC: float = 0.20
    WEIGHT_PRIORITY: float = 0.15

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
