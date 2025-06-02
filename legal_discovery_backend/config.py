"""
Configuration and environment validation for the Legal Discovery Backend.
"""

import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EnvironmentConfig(BaseModel):
    """Environment configuration with validation."""
    
    # Database
    database_url: str = Field(default="sqlite:///./legal_discovery.db")
    
    # API Keys (Optional - will warn if missing)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    voyageai_api_key: Optional[str] = None
    
    # Azure AI Search (Optional - for document search)
    azure_search_endpoint: Optional[str] = None
    azure_search_key: Optional[str] = None
    azure_search_index: Optional[str] = None
    
    # Weaviate (Optional - for vector search)
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    weaviate_collection_name: Optional[str] = None
    
    # Model Configuration
    writer_provider: str = Field(default="openai")
    writer_model: str = Field(default="gpt-4")
    planner_provider: str = Field(default="anthropic")
    planner_model: str = Field(default="claude-3-5-sonnet-latest")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    debug: bool = Field(default=False)
    
    # CORS Configuration
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:3001"])
    
    # File Upload Configuration
    max_file_size: int = Field(default=50 * 1024 * 1024)  # 50MB
    upload_directory: str = Field(default="./uploads")
    allowed_file_types: list[str] = Field(default=[".pdf", ".docx", ".txt", ".md"])

def load_environment_config() -> EnvironmentConfig:
    """Load configuration from environment variables."""
    config_dict = {}
    
    # Map environment variables to config fields
    env_mapping = {
        "DATABASE_URL": "database_url",
        "OPENAI_API_KEY": "openai_api_key",
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "VOYAGEAI_API_KEY": "voyageai_api_key",
        "AZURE_SEARCH_ENDPOINT": "azure_search_endpoint",
        "AZURE_SEARCH_KEY": "azure_search_key",
        "AZURE_SEARCH_INDEX": "azure_search_index",
        "WEAVIATE_URL": "weaviate_url",
        "WEAVIATE_API_KEY": "weaviate_api_key",
        "WEAVIATE_COLLECTION_NAME": "weaviate_collection_name",
        "WRITER_PROVIDER": "writer_provider",
        "WRITER_MODEL": "writer_model",
        "PLANNER_PROVIDER": "planner_provider",
        "PLANNER_MODEL": "planner_model",
        "HOST": "host",
        "PORT": "port",
        "LOG_LEVEL": "log_level",
        "DEBUG": "debug",
        "MAX_FILE_SIZE": "max_file_size",
        "UPLOAD_DIRECTORY": "upload_directory",
    }
    
    # Load values from environment
    for env_var, config_key in env_mapping.items():
        value = os.getenv(env_var)
        if value is not None:
            # Handle type conversion
            if config_key == "port" or config_key == "max_file_size":
                try:
                    value = int(value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {env_var}: {value}")
                    continue
            elif config_key == "debug":
                value = value.lower() in ("true", "1", "yes", "on")
            elif config_key == "cors_origins":
                value = value.split(",")
            elif config_key == "allowed_file_types":
                value = value.split(",")
            
            config_dict[config_key] = value
    
    return EnvironmentConfig(**config_dict)

def validate_required_dependencies(config: EnvironmentConfig) -> Dict[str, str]:
    """
    Validate that required dependencies are available.
    Returns dict of missing/invalid configurations.
    """
    issues = {}
    
    # Check API keys for AI models
    if not config.openai_api_key and config.writer_provider == "openai":
        issues["openai_api_key"] = "OpenAI API key required when using OpenAI as writer provider"
    
    if not config.anthropic_api_key and config.planner_provider == "anthropic":
        issues["anthropic_api_key"] = "Anthropic API key required when using Anthropic as planner provider"
    
    # Check document search dependencies
    if config.azure_search_endpoint and not config.azure_search_key:
        issues["azure_search_key"] = "Azure Search key required when endpoint is configured"
    
    if config.weaviate_url and not config.weaviate_collection_name:
        issues["weaviate_collection_name"] = "Weaviate collection name required when URL is configured"
    
    # Check upload directory
    if config.upload_directory and not os.path.exists(config.upload_directory):
        try:
            os.makedirs(config.upload_directory, exist_ok=True)
            logger.info(f"Created upload directory: {config.upload_directory}")
        except Exception as e:
            issues["upload_directory"] = f"Cannot create upload directory: {e}"
    
    return issues

def setup_logging(config: EnvironmentConfig) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.value),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("legal_discovery.log")
        ]
    )
    
    # Set specific logger levels
    if not config.debug:
        # Reduce noise from external libraries
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

def get_workflow_config(config: EnvironmentConfig) -> Dict[str, Any]:
    """Get configuration for LangGraph workflow."""
    return {
        "configurable": {
            "writer_provider": config.writer_provider,
            "writer_model": config.writer_model,
            "planner_provider": config.planner_provider,
            "planner_model": config.planner_model,
            "azure_search_endpoint": config.azure_search_endpoint,
            "azure_search_key": config.azure_search_key,
            "azure_search_index": config.azure_search_index,
            "weaviate_url": config.weaviate_url,
            "weaviate_api_key": config.weaviate_api_key,
            "weaviate_collection_name": config.weaviate_collection_name,
            "number_of_queries": 5,
            "max_search_depth": 3,
        }
    }

# Global configuration instance
config = load_environment_config()
setup_logging(config)

# Validate configuration and log issues
config_issues = validate_required_dependencies(config)
if config_issues:
    logger.warning("Configuration issues detected:")
    for key, issue in config_issues.items():
        logger.warning(f"  {key}: {issue}")
    logger.warning("Some features may not work properly. Please check your environment variables.")
else:
    logger.info("Configuration validation passed")