"""
CORS Middleware Configuration

Configures Cross-Origin Resource Sharing settings.
In production, restrict origins to specific frontend URLs.
"""

from fastapi.middleware.cors import CORSMiddleware
from typing import List


class CORSSettings:
    """CORS configuration settings."""

    # Development: allow all origins
    ALLOW_ORIGINS_DEV = ["*"]

    # Production: specify exact origins
    ALLOW_ORIGINS_PROD = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-production-domain.com",
    ]

    ALLOW_CREDENTIALS = True
    ALLOW_METHODS = ["POST", "GET", "PUT", "DELETE", "OPTIONS"]
    ALLOW_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]

    @classmethod
    def apply_middleware(cls, app, production: bool = False):
        """
        Apply CORS middleware to FastAPI app.

        Args:
            app: FastAPI application instance
            production: If True, use restricted origins
        """
        origins = cls.ALLOW_ORIGINS_PROD if production else cls.ALLOW_ORIGINS_DEV

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=cls.ALLOW_CREDENTIALS,
            allow_methods=cls.ALLOW_METHODS,
            allow_headers=cls.ALLOW_HEADERS,
        )