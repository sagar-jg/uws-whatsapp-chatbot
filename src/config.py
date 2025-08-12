"""Application Configuration"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str
    PINECONE_DIMENSION: int = 1536
    
    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_WEBHOOK_URL: Optional[str] = None
    
    # HubSpot MCP
    HUBSPOT_API_KEY: str
    HUBSPOT_PORTAL_ID: str
    HUBSPOT_MCP_SERVER_URL: str = "http://localhost:3001"
    
    # Web Search
    SERPER_API_KEY: str
    SEARCH_RESULTS_LIMIT: int = 5
    SEARCH_TIMEOUT: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 3600
    
    # Application
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # Monitoring
    PROMETHEUS_PORT: int = 9090
    METRICS_ENABLED: bool = True
    
    # Conversation Settings
    MAX_CONVERSATION_HISTORY: int = 50
    CONTEXT_WINDOW_SIZE: int = 4000
    MAX_RESPONSE_LENGTH: int = 1000
    
    # Data Freshness
    VECTOR_FRESHNESS_THRESHOLD_DAYS: int = 30
    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_THRESHOLD_SCORE: float = 0.7
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()