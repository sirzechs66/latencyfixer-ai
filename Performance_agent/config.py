"""
Configuration module for LatencyFixer AI.

Handles environment variables and application settings.
Supports loading from .env files using python-dotenv.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


# =============================================================================
# ENV FILE LOADING
# =============================================================================

def load_env(env_path: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, searches for .env in current
                  directory and parent directories.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        # Search for .env in current and parent directories
        load_dotenv()
        load_dotenv(".env")


# =============================================================================
# CONFIGURATION CLASS
# =============================================================================

class Config:
    """Application configuration."""

    # Default paths
    DEFAULT_BASE_PATH = Path.cwd()
    DEFAULT_OUTPUT_DIR = Path("./output")
    DEFAULT_REPORT_NAME = "report.json"

    # Scoring weights (can be overridden via env vars)
    SCORING_WEIGHTS = {
        "latency_gain": float(os.environ.get("WEIGHT_LATENCY_GAIN", 0.35)),
        "accuracy": float(os.environ.get("WEIGHT_ACCURACY", 0.25)),
        "stability": float(os.environ.get("WEIGHT_STABILITY", 0.15)),
        "clarity": float(os.environ.get("WEIGHT_CLARITY", 0.15)),
        "context_efficiency": float(os.environ.get("WEIGHT_CONTEXT_EFFICIENCY", 0.10)),
    }

    # Dependency graph limits
    MAX_DEPENDENCY_DEPTH = int(os.environ.get("MAX_DEPENDENCY_DEPTH", 2))
    MAX_CONTEXT_TOKENS = int(os.environ.get("MAX_CONTEXT_TOKENS", 50000))

    # Bottleneck severity thresholds (ms)
    SEVERITY_THRESHOLDS = {
        "critical": int(os.environ.get("THRESHOLD_CRITICAL", 500)),
        "high": int(os.environ.get("THRESHOLD_HIGH", 200)),
        "medium": int(os.environ.get("THRESHOLD_MEDIUM", 50)),
        "low": int(os.environ.get("THRESHOLD_LOW", 10)),
    }

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # AWS Bedrock credentials
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_BEDROCK_MODEL: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    LLM_PROVIDER: str = "anthropic"  # "anthropic" or "aws"

    # Flags
    DEBUG: bool = False
    VERBOSE: bool = False
    DEFAULT_OUTPUT_DIR_PATH: str = "./output"

    # API Version (from .env)
    API_VERSION: str = os.environ.get("API_VERSION", "v1")

    def __init__(self, env_path: Optional[str] = None):
        """
        Load configuration from environment and .env file.

        Args:
            env_path: Optional path to .env file
        """
        # Load .env file
        load_env(env_path)

        # Load API keys
        self.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

        # Load AWS Bedrock credentials
        self.AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.AWS_BEDROCK_MODEL = os.environ.get("AWS_BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

        # Load flags
        self.DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
        self.VERBOSE = os.environ.get("VERBOSE", "false").lower() == "true"

        # Load paths
        self.DEFAULT_OUTPUT_DIR_PATH = os.environ.get("DEFAULT_OUTPUT_DIR", "./output")

    @classmethod
    def get_instance(cls, env_path: Optional[str] = None) -> "Config":
        """Get singleton config instance."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls(env_path)
        return cls._instance

    def reload(self, env_path: Optional[str] = None) -> None:
        """Reload configuration from .env file."""
        load_env(env_path)
        self.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        self.AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.AWS_BEDROCK_MODEL = os.environ.get("AWS_BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")
        self.DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
        self.VERBOSE = os.environ.get("VERBOSE", "false").lower() == "true"
        self.DEFAULT_OUTPUT_DIR_PATH = os.environ.get("DEFAULT_OUTPUT_DIR", "./output")

    def get_api_key(self, provider: str = "anthropic") -> Optional[str]:
        """Get API key for specified provider."""
        if provider == "anthropic":
            return self.ANTHROPIC_API_KEY
        elif provider == "openai":
            return self.OPENAI_API_KEY
        elif provider == "aws":
            return None  # AWS uses credentials, not API key
        return None

    def is_bedrock_configured(self) -> bool:
        """Check if AWS Bedrock credentials are configured."""
        return bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY)

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.DEBUG

    def is_verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self.VERBOSE

    def get_output_dir(self) -> Path:
        """Get output directory, creating if needed."""
        output_dir = Path(self.DEFAULT_OUTPUT_DIR_PATH)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def get_base_path(self) -> Path:
        """Get base path for code search."""
        return Path(os.environ.get("BASE_PATH", Path.cwd()))

    def get_bedrock_model(self) -> str:
        """Get configured Bedrock model ID."""
        return self.AWS_BEDROCK_MODEL

    def get_bedrock_region(self) -> str:
        """Get configured AWS region."""
        return self.AWS_DEFAULT_REGION

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "anthropic_api_key": self.ANTHROPIC_API_KEY is not None,
            "openai_api_key": self.OPENAI_API_KEY is not None,
            "bedrock_configured": self.is_bedrock_configured(),
            "bedrock_region": self.AWS_DEFAULT_REGION,
            "bedrock_model": self.AWS_BEDROCK_MODEL,
            "llm_provider": self.LLM_PROVIDER,
            "debug": self.DEBUG,
            "verbose": self.VERBOSE,
            "base_path": str(self.get_base_path()),
            "output_dir": str(self.get_output_dir()),
            "scoring_weights": self.SCORING_WEIGHTS,
            "max_dependency_depth": self.MAX_DEPENDENCY_DEPTH,
            "max_context_tokens": self.MAX_CONTEXT_TOKENS,
            "severity_thresholds": self.SEVERITY_THRESHOLDS,
            "api_version": self.API_VERSION,
        }


# =============================================================================
# GLOBAL CONFIG INSTANCE
# =============================================================================

# Auto-load .env on import
load_env()

# Global config instance
config = Config.get_instance()
