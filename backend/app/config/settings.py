"""
Configuration settings for MATRXe platform
"""

import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator, PostgresDsn
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings
    """
    
    # Application
    APP_NAME: str = "MATRXe"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    PORT: int = Field(default=8000, env="PORT")
    
    # Domain
    DOMAIN: str = Field(default="matrxe.com", env="DOMAIN")
    BASE_URL: str = Field(default="https://matrxe.com", env="BASE_URL")
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "https://matrxe.com"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "matrxe.com", "*.matrxe.com"],
        env="ALLOWED_HOSTS"
    )
    
    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://postgres:password@localhost/matrxe",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=40, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    HUGGINGFACE_TOKEN: Optional[str] = Field(default=None, env="HUGGINGFACE_TOKEN")
    GOOGLE_CLOUD_KEY: Optional[str] = Field(default=None, env="GOOGLE_CLOUD_KEY")
    
    # Ollama
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    OLLAMA_DEFAULT_MODEL: str = Field(default="llama3:8b", env="OLLAMA_DEFAULT_MODEL")
    
    # Email
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@matrxe.com", env="EMAIL_FROM")
    
    # File Storage
    UPLOAD_DIR: str = Field(default="/uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 100MB
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "mp3", "wav", "mp4", "webm"],
        env="ALLOWED_EXTENSIONS"
    )
    
    # Billing
    DEFAULT_CURRENCY: str = Field(default="USD", env="DEFAULT_CURRENCY")
    CREDIT_PRICE: float = Field(default=0.01, env="CREDIT_PRICE")  # $0.01 per credit
    TRIAL_CREDITS: int = Field(default=1000, env="TRIAL_CREDITS")
    TRIAL_DAYS: int = Field(default=30, env="TRIAL_DAYS")
    
    # AI Costs (in credits)
    VOICE_MINUTE_COST: int = Field(default=10, env="VOICE_MINUTE_COST")
    CHAT_MESSAGE_COST: int = Field(default=1, env="CHAT_MESSAGE_COST")
    FACE_PROCESSING_COST: int = Field(default=5, env="FACE_PROCESSING_COST")
    
    # Internationalization
    DEFAULT_LANGUAGE: str = Field(default="ar", env="DEFAULT_LANGUAGE")
    SUPPORTED_LANGUAGES: List[str] = Field(
        default=["ar", "en", "fr", "es", "de", "ru", "tr", "ur"],
        env="SUPPORTED_LANGUAGES"
    )
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_DAY: int = Field(default=1000, env="RATE_LIMIT_PER_DAY")
    
    # Timezone
    TIMEZONE: str = Field(default="Asia/Riyadh", env="TIMEZONE")
    
    # Payment (for deferred payments)
    DEFERRED_PAYMENT_GRACE_DAYS: int = Field(default=7, env="DEFERRED_PAYMENT_GRACE_DAYS")
    MIN_DEFERRED_AMOUNT: float = Field(default=10.0, env="MIN_DEFERRED_AMOUNT")
    LATE_FEE_PERCENTAGE: float = Field(default=5.0, env="LATE_FEE_PERCENTAGE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("SUPPORTED_LANGUAGES", pre=True)
    def parse_supported_languages(cls, v):
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",")]
        return v
    
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """
    Get settings instance (singleton pattern)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Export settings
settings = get_settings()