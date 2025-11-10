"""
Configuration Management
Loads settings from environment variables using Pydantic
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Legal AI Vault"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str

    # Database
    DATABASE_URL: str

    # Vector Database
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    # vLLM Endpoints
    VLLM_CONTRACT_URL: str
    VLLM_COMPLIANCE_URL: str
    VLLM_ROUTER_URL: str
    EMBEDDING_URL: str

    # File Storage
    DOCUMENT_STORAGE_PATH: str = "/app/documents"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".doc", ".txt"]

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "https://legal-ai.client.internal",
        "http://localhost:3000"
    ]

    # Audit Logging
    AUDIT_LOG_PATH: str = "/app/logs/audit.log"
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years

    # Inference Settings
    DEFAULT_MAX_TOKENS: int = 4096
    DEFAULT_TEMPERATURE: float = 0.3
    INFERENCE_TIMEOUT_SECONDS: int = 120

    # Redis (Optional - for caching)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Dify
    DIFY_API_URL: str = "http://dify-api:5001"
    DIFY_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS if it's a comma-separated string"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS


# Global settings instance
settings = Settings()
