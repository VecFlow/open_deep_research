"""
Document service for Weaviate integration.
Renamed from Azure for consistency but uses the same underlying Weaviate functionality.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import weaviate
from weaviate.auth import AuthApiKey

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for document search using Weaviate vector database."""
    
    def __init__(self):
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> weaviate.Client:
        """Initialize Weaviate client with authentication."""
        try:
            weaviate_url = os.getenv("WEAVIATE_URL")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
            
            if not weaviate_url:
                raise ValueError("WEAVIATE_URL environment variable is required")
            
            if weaviate_api_key:
                auth_config = AuthApiKey(api_key=weaviate_api_key)
                client = weaviate.Client(
                    url=weaviate_url,
                    auth_client_secret=auth_config
                )
            else:
                client = weaviate.Client(url=weaviate_url)
            
            # Test connection
            if not client.is_ready():
                raise ConnectionError("Weaviate client is not ready")
            
            logger.info("Successfully connected to Weaviate")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise
    
    async def search_documents(
        self, 
        queries: List[str], 
        collection_name: Optional[str] = None,
        limit: int = 10,
        certainty: float = 0.7
    ) -> str:
        """
        Search documents using multiple queries and return formatted results.
        
        Args:
            queries: List of search query strings
            collection_name: Weaviate collection to search (defaults to env var)
            limit: Maximum number of results per query
            certainty: Minimum certainty threshold for results
            
        Returns:
            Formatted string containing search results
        """
        try:
            collection = collection_name or os.getenv("WEAVIATE_COLLECTION_NAME", "Documents")
            all_results = []
            
            for query in queries:
                logger.info(f"Searching for: {query}")
                
                # Perform hybrid search (vector + keyword)
                result = (
                    self.client.query
                    .get(collection, ["title", "content", "source", "metadata"])
                    .with_near_text({"concepts": [query]})
                    .with_limit(limit)
                    .with_additional(["certainty", "distance"])
                    .do()
                )
                
                if "data" in result and "Get" in result["data"]:
                    documents = result["data"]["Get"].get(collection, [])
                    
                    # Filter by certainty threshold
                    filtered_docs = [
                        doc for doc in documents 
                        if doc.get("_additional", {}).get("certainty", 0) >= certainty
                    ]
                    
                    all_results.extend(filtered_docs)
                    logger.info(f"Found {len(filtered_docs)} relevant documents for query: {query}")
            
            # Remove duplicates and format results
            unique_results = self._deduplicate_results(all_results)
            formatted_results = self._format_search_results(unique_results)
            
            logger.info(f"Total unique documents found: {len(unique_results)}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return f"Error searching documents: {str(e)}"
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents based on content similarity."""
        seen_titles = set()
        unique_results = []
        
        for doc in results:
            title = doc.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(doc)
        
        return unique_results
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a readable string."""
        if not results:
            return "No relevant documents found."
        
        formatted_sections = []
        
        for i, doc in enumerate(results, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "")
            source = doc.get("source", "Unknown source")
            certainty = doc.get("_additional", {}).get("certainty", 0)
            
            # Truncate content if too long
            if len(content) > 500:
                content = content[:500] + "..."
            
            section = f"""
Document {i}: {title}
Source: {source}
Relevance: {certainty:.2f}
Content: {content}
---
"""
            formatted_sections.append(section.strip())
        
        return "\n\n".join(formatted_sections)
    
    async def get_document_by_id(self, document_id: str, collection_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by ID."""
        try:
            collection = collection_name or os.getenv("WEAVIATE_COLLECTION_NAME", "Documents")
            
            result = (
                self.client.query
                .get(collection, ["title", "content", "source", "metadata"])
                .with_where({
                    "path": ["id"],
                    "operator": "Equal",
                    "valueString": document_id
                })
                .do()
            )
            
            if "data" in result and "Get" in result["data"]:
                documents = result["data"]["Get"].get(collection, [])
                return documents[0] if documents else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve document {document_id}: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Weaviate connection."""
        try:
            is_ready = self.client.is_ready()
            meta = self.client.get_meta()
            
            return {
                "status": "healthy" if is_ready else "unhealthy",
                "ready": is_ready,
                "version": meta.get("version", "unknown"),
                "modules": meta.get("modules", {})
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global instance
document_service = DocumentService()