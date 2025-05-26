"""Utility functions for the redline system."""

import warnings
from typing import List, Dict, Any, Optional


def suppress_langchain_warnings():
    """Suppress known deprecation warnings from LangChain dependencies."""
    # Suppress Pydantic deprecation warnings from LangChain
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*The `schema` method is deprecated.*",
    )
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")


def get_config_value(value: Any, default: Any = None) -> Any:
    """Get configuration value with fallback to default."""
    return value if value is not None else default


def format_document_content(content: str, max_length: Optional[int] = None) -> str:
    """Format document content for processing.

    Args:
        content: Raw document content
        max_length: Optional maximum length to truncate to

    Returns:
        Formatted content string
    """
    if max_length and len(content) > max_length:
        return content[:max_length] + "..."
    return content


def extract_document_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from document content.

    Args:
        content: Document content

    Returns:
        Dictionary of extracted metadata
    """
    # TODO: Implement metadata extraction
    return {
        "length": len(content),
        "word_count": len(content.split()) if content else 0,
        "has_content": bool(content.strip()),
    }
