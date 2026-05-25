"""Configuration management for HyperFactory API"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Core
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://hyperfactory:password@localhost:5432/hyperfactory"

    # Cache
    redis_url: str = "redis://localhost:6379"

    # Graph Database
    neo4j_url: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # External APIs
    claude_api_key: str = ""
    openai_api_key: str = ""

    # API Configuration
    api_title: str = "HyperFactory API"
    api_version: str = "0.2.0"
    api_prefix: str = "/api"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
