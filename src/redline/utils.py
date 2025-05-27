"""Utility functions for the redline system."""

import warnings
from typing import Any

from src.redline.prompts import reference_doc_summary_template


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


def format_reference_documents_content(state) -> str:
    """Format reference documents with their comments using the standard template.

    Args:
        state: RedlineState containing reference document data

    Returns:
        Formatted string with all reference documents separated by "\n---\n"
    """

    formatted_docs = []
    for i, (ref_id, ref_content, ref_comment) in enumerate(
        zip(
            state["reference_doc_ids"],
            state["reference_documents_content"],
            state["reference_documents_comments"],
        )
    ):
        formatted_docs.append(
            reference_doc_summary_template.format(
                doc_number=i + 1,
                ref_id=ref_id,
                ref_comment=ref_comment,
                ref_content=ref_content,
            )
        )
    return "\n---\n".join(formatted_docs)
