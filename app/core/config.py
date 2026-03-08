from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./shadowblock.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_MODERATION: str = "content-moderation"
    KAFKA_TOPIC_ANALYTICS: str = "moderation-analytics"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Keys
    OPENAI_API_KEY: str = ""
    PERSPECTIVE_API_KEY: str = ""
    HF_TOKEN: str = ""
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]
    
    # AI Models
    HUGGINGFACE_MODEL_PATH: str = "unitary/toxic-bert"
    WHISPER_MODEL_SIZE: str = "base"
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "uploads"
    
    # Monitoring
    PROMETHEUS_PORT: int = 8001
    
    class Config:
        env_file = ".env"

settings = Settings()

servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(",")
# origins = settings.ALLOWED_ORIGINS.split(",")
