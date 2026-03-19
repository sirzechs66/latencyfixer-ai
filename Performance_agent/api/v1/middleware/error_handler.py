"""
Error Handler Middleware

Global exception handling and logging.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Configure logger
logger = logging.getLogger("latencyfixer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ErrorLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log unhandled exceptions.

    Logs error details for debugging and monitoring.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                f"Unhandled exception: {type(e).__name__} - {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                }
            )
            raise