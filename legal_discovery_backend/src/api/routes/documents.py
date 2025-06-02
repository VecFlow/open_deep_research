"""
Documents API routes for document search and management.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ...services.document_service import document_service

logger = logging.getLogger(__name__)
router = APIRouter()

class DocumentSearchRequest(BaseModel):
    queries: List[str] = Field(..., min_items=1, max_items=10)
    collection_name: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)
    certainty: float = Field(default=0.7, ge=0.0, le=1.0)

class DocumentSearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int

class DocumentSearchResponse(BaseModel):
    searches: List[DocumentSearchResult]
    formatted_results: str
    total_unique_documents: int

class DocumentDetail(BaseModel):
    id: str
    title: str
    content: str
    source: str
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_request: DocumentSearchRequest
) -> DocumentSearchResponse:
    """Search documents using multiple queries."""
    try:
        # Perform document search
        formatted_results = await document_service.search_documents(
            queries=search_request.queries,
            collection_name=search_request.collection_name,
            limit=search_request.limit,
            certainty=search_request.certainty
        )
        
        # For detailed response, we'd need to modify the service to return structured data
        # For now, return the formatted string
        searches = []
        for query in search_request.queries:
            searches.append(DocumentSearchResult(
                query=query,
                results=[],  # Would be populated with actual search results
                total_found=0
            ))
        
        return DocumentSearchResponse(
            searches=searches,
            formatted_results=formatted_results,
            total_unique_documents=0  # Would be calculated from actual results
        )
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document search failed: {str(e)}"
        )

@router.get("/search")
async def quick_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    certainty: float = Query(default=0.7, ge=0.0, le=1.0),
    collection: Optional[str] = Query(None, description="Collection name")
):
    """Quick single-query document search."""
    try:
        results = await document_service.search_documents(
            queries=[q],
            collection_name=collection,
            limit=limit,
            certainty=certainty
        )
        
        return {
            "query": q,
            "results": results,
            "parameters": {
                "limit": limit,
                "certainty": certainty,
                "collection": collection
            }
        }
        
    except Exception as e:
        logger.error(f"Quick search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    collection: Optional[str] = Query(None, description="Collection name")
) -> DocumentDetail:
    """Get a specific document by ID."""
    try:
        document = await document_service.get_document_by_id(
            document_id=document_id,
            collection_name=collection
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        return DocumentDetail(
            id=document_id,
            title=document.get("title", ""),
            content=document.get("content", ""),
            source=document.get("source", ""),
            metadata=document.get("metadata"),
            relevance_score=document.get("_additional", {}).get("certainty")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )

@router.get("/health/check")
async def check_document_service_health():
    """Check the health of the document service."""
    try:
        health = await document_service.health_check()
        
        if health["status"] == "healthy":
            return health
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health
            )
            
    except Exception as e:
        logger.error(f"Document service health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Document service unavailable: {str(e)}"
        )

@router.post("/collections/test")
async def test_collection_access(
    collection_name: str,
    test_query: str = "test"
):
    """Test access to a specific document collection."""
    try:
        results = await document_service.search_documents(
            queries=[test_query],
            collection_name=collection_name,
            limit=1,
            certainty=0.5
        )
        
        return {
            "collection": collection_name,
            "accessible": True,
            "test_query": test_query,
            "sample_results": results[:200] + "..." if len(results) > 200 else results
        }
        
    except Exception as e:
        logger.error(f"Collection access test failed for {collection_name}: {e}")
        return {
            "collection": collection_name,
            "accessible": False,
            "error": str(e)
        }