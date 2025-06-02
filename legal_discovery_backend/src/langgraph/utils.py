"""
Utility functions for the legal discovery workflow.
Adapted to use Weaviate document service instead of Azure.
"""

import os
import logging
from typing import List, Optional, Any, Dict
from ..services.document_service import document_service

logger = logging.getLogger(__name__)

def format_categories(categories):
    """Format completed categories for use as context."""
    formatted = []
    for category in categories:
        formatted.append(f"### {category.name}\n\n{category.content}\n")
    return "\n".join(formatted)

def get_config_value(value):
    """Get configuration value, handling both direct values and environment variables."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        # Environment variable format: ${VAR_NAME}
        env_var = value[2:-1]
        return os.getenv(env_var, value)
    return value

async def search_documents_with_weaviate(
    queries: List[str], 
    configurable: Any,
    limit: int = 10,
    certainty: float = 0.7
) -> str:
    """
    Search documents using Weaviate service.
    Renamed from search_documents_with_azure_ai for consistency.
    
    Args:
        queries: List of search query strings
        configurable: Configuration object with search parameters
        limit: Maximum number of results per query
        certainty: Minimum certainty threshold for results
        
    Returns:
        Formatted string containing search results
    """
    try:
        # Extract configuration values
        collection_name = getattr(configurable, 'collection_name', None)
        search_limit = getattr(configurable, 'search_limit', limit)
        search_certainty = getattr(configurable, 'search_certainty', certainty)
        
        # Use document service to search
        results = await document_service.search_documents(
            queries=queries,
            collection_name=collection_name,
            limit=search_limit,
            certainty=search_certainty
        )
        
        logger.info(f"Document search completed for {len(queries)} queries")
        return results
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return f"Error searching documents: {str(e)}"

async def get_document_context(
    document_ids: List[str],
    collection_name: Optional[str] = None
) -> str:
    """
    Retrieve specific documents by ID for context.
    
    Args:
        document_ids: List of document IDs to retrieve
        collection_name: Optional collection name
        
    Returns:
        Formatted string containing document content
    """
    try:
        documents = []
        for doc_id in document_ids:
            doc = await document_service.get_document_by_id(
                document_id=doc_id,
                collection_name=collection_name
            )
            if doc:
                documents.append(doc)
        
        if not documents:
            return "No documents found for the provided IDs."
        
        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "")
            source = doc.get("source", "Unknown source")
            
            # Truncate content if too long
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            formatted_docs.append(f"""
Document {i}: {title}
Source: {source}
Content: {content}
---
""".strip())
        
        return "\n\n".join(formatted_docs)
        
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        return f"Error retrieving documents: {str(e)}"

def validate_legal_analysis_input(background: str) -> bool:
    """
    Validate legal analysis input for completeness.
    
    Args:
        background: Case background description
        
    Returns:
        True if input is valid, False otherwise
    """
    if not background or len(background.strip()) < 50:
        return False
    
    # Check for key legal elements
    legal_keywords = [
        "case", "claim", "defendant", "plaintiff", "contract", 
        "breach", "damages", "liability", "dispute", "agreement"
    ]
    
    background_lower = background.lower()
    keyword_count = sum(1 for keyword in legal_keywords if keyword in background_lower)
    
    return keyword_count >= 2

def format_deposition_questions(deposition_questions: Any) -> str:
    """
    Format deposition questions for display or export.
    
    Args:
        deposition_questions: DepositionQuestions object
        
    Returns:
        Formatted string of deposition questions
    """
    if not deposition_questions or not hasattr(deposition_questions, 'witness_questions'):
        return "No deposition questions available."
    
    formatted_sections = []
    
    for witness_questions in deposition_questions.witness_questions:
        section = f"## {witness_questions.witness_name}\n\n"
        section += f"**Role/Relevance:** {witness_questions.witness_role}\n\n"
        section += "**Questions:**\n\n"
        
        for i, question in enumerate(witness_questions.questions, 1):
            section += f"{i}. {question.question}\n"
            section += f"   - *Purpose:* {question.purpose}\n"
            if question.expected_areas:
                section += f"   - *Expected areas:* {', '.join(question.expected_areas)}\n"
            section += "\n"
        
        formatted_sections.append(section)
    
    return "\n".join(formatted_sections)

def extract_case_entities(background: str) -> Dict[str, List[str]]:
    """
    Extract key entities from case background for enhanced searching.
    
    Args:
        background: Case background description
        
    Returns:
        Dictionary with entity types and their values
    """
    entities = {
        "parties": [],
        "dates": [],
        "amounts": [],
        "locations": [],
        "contracts": []
    }
    
    # Simple entity extraction (could be enhanced with NLP)
    words = background.split()
    
    # Look for common legal patterns
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # Parties (often preceded by certain words)
        if word_lower in ["plaintiff", "defendant", "petitioner", "respondent"] and i + 1 < len(words):
            entities["parties"].append(words[i + 1])
        
        # Contracts/agreements
        if word_lower in ["contract", "agreement", "lease", "license"] and i + 1 < len(words):
            entities["contracts"].append(f"{word} {words[i + 1]}")
    
    return entities

async def health_check_dependencies() -> Dict[str, Any]:
    """
    Check the health of all dependencies.
    
    Returns:
        Dictionary with health status of each dependency
    """
    health_status = {
        "document_service": await document_service.health_check(),
        "overall_status": "healthy"
    }
    
    # Determine overall status
    if health_status["document_service"]["status"] != "healthy":
        health_status["overall_status"] = "degraded"
    
    return health_status