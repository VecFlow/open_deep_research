"""
Cases API routes for managing legal cases.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database.models import Case, Analysis, Comment
from ...schemas.case_schemas import (
    CaseCreate, CaseUpdate, Case as CaseSchema, 
    CaseWithAnalysis, CommentCreate, Comment as CommentSchema
)
from ...database.connection import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=CaseSchema, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: Session = Depends(get_db_session)
) -> CaseSchema:
    """Create a new legal case."""
    try:
        db_case = Case(
            title=case_data.title,
            background=case_data.background,
            analysis_structure=case_data.analysis_structure,
            number_of_queries=case_data.number_of_queries,
            max_search_depth=case_data.max_search_depth
        )
        
        db.add(db_case)
        db.commit()
        db.refresh(db_case)
        
        logger.info(f"Created case: {db_case.id}")
        return CaseSchema.from_orm(db_case)
        
    except Exception as e:
        logger.error(f"Failed to create case: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case: {str(e)}"
        )

@router.get("/", response_model=List[CaseSchema])
async def list_cases(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db_session)
) -> List[CaseSchema]:
    """List all legal cases with optional filtering."""
    try:
        query = db.query(Case)
        
        if status_filter:
            query = query.filter(Case.status == status_filter)
        
        cases = query.order_by(Case.updated_at.desc()).offset(skip).limit(limit).all()
        
        return [CaseSchema.from_orm(case) for case in cases]
        
    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cases: {str(e)}"
        )

@router.get("/{case_id}", response_model=CaseWithAnalysis)
async def get_case(
    case_id: str,
    db: Session = Depends(get_db_session)
) -> CaseWithAnalysis:
    """Get a specific case with its analyses and comments."""
    try:
        case = db.query(Case).filter(Case.id == UUID(case_id)).first()
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        # Load relationships
        case_dict = {
            "id": str(case.id),
            "title": case.title,
            "background": case.background,
            "status": case.status,
            "analysis_structure": case.analysis_structure,
            "number_of_queries": case.number_of_queries,
            "max_search_depth": case.max_search_depth,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "current_node": case.current_node,
            "analyses": [
                {
                    "id": str(analysis.id),
                    "case_id": str(analysis.case_id),
                    "status": analysis.status,
                    "categories": analysis.categories or [],
                    "completed_categories": analysis.completed_categories or [],
                    "deposition_questions": analysis.deposition_questions,
                    "final_analysis": analysis.final_analysis,
                    "current_step": analysis.current_step,
                    "feedback_requested": analysis.feedback_requested,
                    "feedback_message": analysis.feedback_message,
                    "created_at": analysis.created_at,
                    "updated_at": analysis.updated_at,
                    "completed_at": analysis.completed_at,
                    "category_progress": [
                        {
                            "id": str(cp.id),
                            "analysis_id": str(cp.analysis_id),
                            "category_name": cp.category_name,
                            "status": cp.status,
                            "content": cp.content,
                            "search_iterations": cp.search_iterations,
                            "source_documents": cp.source_documents or [],
                            "document_queries": cp.document_queries or [],
                            "started_at": cp.started_at,
                            "completed_at": cp.completed_at,
                            "updated_at": cp.updated_at
                        }
                        for cp in analysis.category_progress
                    ]
                }
                for analysis in case.analyses
            ],
            "comments": [
                {
                    "id": str(comment.id),
                    "case_id": str(comment.case_id),
                    "analysis_id": str(comment.analysis_id) if comment.analysis_id else None,
                    "content": comment.content,
                    "context_type": comment.context_type,
                    "context_reference": comment.context_reference,
                    "created_at": comment.created_at
                }
                for comment in case.comments
            ]
        }
        
        return CaseWithAnalysis(**case_dict)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get case: {str(e)}"
        )

@router.put("/{case_id}", response_model=CaseSchema)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: Session = Depends(get_db_session)
) -> CaseSchema:
    """Update a legal case."""
    try:
        case = db.query(Case).filter(Case.id == UUID(case_id)).first()
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        # Update fields
        update_data = case_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)
        
        db.commit()
        db.refresh(case)
        
        logger.info(f"Updated case: {case_id}")
        return CaseSchema.from_orm(case)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format"
        )
    except Exception as e:
        logger.error(f"Failed to update case {case_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case: {str(e)}"
        )

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    db: Session = Depends(get_db_session)
):
    """Delete a legal case and all its related data."""
    try:
        case = db.query(Case).filter(Case.id == UUID(case_id)).first()
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        db.delete(case)
        db.commit()
        
        logger.info(f"Deleted case: {case_id}")
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format"
        )
    except Exception as e:
        logger.error(f"Failed to delete case {case_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}"
        )

@router.post("/{case_id}/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
async def add_comment(
    case_id: str,
    comment_data: CommentCreate,
    db: Session = Depends(get_db_session)
) -> CommentSchema:
    """Add a comment to a case."""
    try:
        # Verify case exists
        case = db.query(Case).filter(Case.id == UUID(case_id)).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        # Verify analysis exists if provided
        if comment_data.analysis_id:
            analysis = db.query(Analysis).filter(
                Analysis.id == UUID(comment_data.analysis_id),
                Analysis.case_id == UUID(case_id)
            ).first()
            if not analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Analysis {comment_data.analysis_id} not found for case {case_id}"
                )
        
        db_comment = Comment(
            case_id=UUID(case_id),
            analysis_id=UUID(comment_data.analysis_id) if comment_data.analysis_id else None,
            content=comment_data.content,
            context_type=comment_data.context_type,
            context_reference=comment_data.context_reference
        )
        
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        
        logger.info(f"Added comment to case {case_id}")
        return CommentSchema.from_orm(db_comment)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )
    except Exception as e:
        logger.error(f"Failed to add comment to case {case_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add comment: {str(e)}"
        )