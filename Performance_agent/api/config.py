"""
LatencyFixer AI - API Configuration

Centralized configuration for the FastAPI backend.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class APIConfig:
    """API configuration from environment variables."""

    # Server settings
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", 8000))

    # CORS settings
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    ]

    # Authentication
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    API_KEYS: list[str] = [
        key.strip()
        for key in os.getenv("API_KEYS", "").split(",")
        if key.strip()
    ]

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", 60))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # seconds

    # Caching
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "false").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", 300))  # seconds

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT_JSON: bool = os.getenv("LOG_FORMAT_JSON", "true").lower() == "true"

    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


config = APIConfig()
