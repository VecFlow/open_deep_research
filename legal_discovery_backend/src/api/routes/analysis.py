"""
Analysis API routes for managing legal analysis workflows.
"""

import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from ...database.models import Case, Analysis
from ...database.connection import get_db_session
from ...schemas.case_schemas import (
    AnalysisCreate, Analysis as AnalysisSchema, 
    WorkflowCommand, WorkflowStatus, AnalysisProgress
)
from ...services.langgraph_service import LangGraphService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_langgraph_service(db: Session = Depends(get_db_session)) -> LangGraphService:
    """Dependency for getting LangGraph service."""
    return LangGraphService(db)

@router.post("/{case_id}/start", response_model=AnalysisSchema, status_code=status.HTTP_201_CREATED)
async def start_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db_session)
) -> AnalysisSchema:
    """Start a new legal analysis for a case."""
    try:
        # Verify case exists
        case = db.query(Case).filter(Case.id == UUID(case_id)).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )
        
        # Create new analysis record
        analysis = Analysis(
            case_id=UUID(case_id),
            status="planning"
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Prepare configuration
        config = {
            "analysis_structure": case.analysis_structure,
            "number_of_queries": case.number_of_queries,
            "max_search_depth": case.max_search_depth,
            "writer_provider": "openai",
            "writer_model": "gpt-4",
            "planner_provider": "anthropic",
            "planner_model": "claude-3-5-sonnet-latest"
        }
        
        # Start workflow execution
        execution = await langgraph_service.start_analysis(
            case_id=case_id,
            analysis_id=str(analysis.id),
            background_on_case=case.background,
            config=config
        )
        
        # Update analysis with execution info
        analysis.current_step = "starting"
        analysis.status = "in_progress"
        db.commit()
        
        logger.info(f"Started analysis {analysis.id} for case {case_id}")
        
        return AnalysisSchema(
            id=str(analysis.id),
            case_id=str(analysis.case_id),
            status=analysis.status,
            current_step=analysis.current_step,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
            category_progress=[]
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case ID format"
        )
    except Exception as e:
        logger.error(f"Failed to start analysis for case {case_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )

@router.get("/{analysis_id}", response_model=AnalysisSchema)
async def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db_session)
) -> AnalysisSchema:
    """Get a specific analysis."""
    try:
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )
        
        return AnalysisSchema(
            id=str(analysis.id),
            case_id=str(analysis.case_id),
            status=analysis.status,
            categories=analysis.categories or [],
            completed_categories=analysis.completed_categories or [],
            deposition_questions=analysis.deposition_questions,
            final_analysis=analysis.final_analysis,
            current_step=analysis.current_step,
            feedback_requested=analysis.feedback_requested,
            feedback_message=analysis.feedback_message,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
            completed_at=analysis.completed_at,
            category_progress=[
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
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis: {str(e)}"
        )

@router.get("/{analysis_id}/stream")
async def stream_analysis_progress(
    analysis_id: str,
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db_session)
):
    """Stream real-time analysis progress updates."""
    try:
        # Verify analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )
        
        # Get thread ID for the workflow
        thread_id = f"case_{analysis.case_id}_{analysis_id}"
        
        async def generate_updates():
            """Generate server-sent events for analysis updates."""
            try:
                async for update in langgraph_service.execute_workflow_step(thread_id):
                    yield f"data: {json.dumps(update)}\n\n"
            except Exception as e:
                logger.error(f"Error in analysis stream: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_updates(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    except Exception as e:
        logger.error(f"Failed to start analysis stream for {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}"
        )

@router.post("/{analysis_id}/control")
async def control_workflow(
    analysis_id: str,
    command: WorkflowCommand,
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db_session)
):
    """Control workflow execution (pause, resume, provide feedback)."""
    try:
        # Verify analysis exists
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )
        
        thread_id = f"case_{analysis.case_id}_{analysis_id}"
        
        if command.action == "pause":
            success = await langgraph_service.pause_workflow(thread_id)
            if success:
                analysis.status = "paused"
                db.commit()
                return {"message": "Workflow paused successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to pause workflow"
                )
        
        elif command.action == "resume":
            success = await langgraph_service.resume_workflow(thread_id)
            if success:
                analysis.status = "in_progress"
                db.commit()
                return {"message": "Workflow resumed successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to resume workflow"
                )
        
        elif command.action == "feedback":
            if not command.feedback and command.approve_plan is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Feedback or approval required for feedback action"
                )
            
            success = await langgraph_service.provide_feedback(
                thread_id=thread_id,
                feedback=command.feedback or "",
                approve=command.approve_plan or False
            )
            
            if success:
                return {"message": "Feedback provided successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to provide feedback"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {command.action}"
            )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    except Exception as e:
        logger.error(f"Failed to control workflow for analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control workflow: {str(e)}"
        )

@router.get("/{analysis_id}/status", response_model=WorkflowStatus)
async def get_workflow_status(
    analysis_id: str,
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
    db: Session = Depends(get_db_session)
) -> WorkflowStatus:
    """Get current workflow status."""
    try:
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )
        
        thread_id = f"case_{analysis.case_id}_{analysis_id}"
        status = langgraph_service.get_workflow_status(thread_id)
        
        if not status:
            # Fallback to database status
            total_categories = len(analysis.categories or [])
            completed_categories = len(analysis.completed_categories or [])
            progress_percentage = (completed_categories / total_categories * 100) if total_categories > 0 else 0
            
            status = WorkflowStatus(
                status=analysis.status,
                current_step=analysis.current_step,
                progress_percentage=progress_percentage,
                feedback_requested=analysis.feedback_requested,
                feedback_message=analysis.feedback_message,
                categories_completed=completed_categories,
                total_categories=total_categories
            )
        
        return status
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    except Exception as e:
        logger.error(f"Failed to get workflow status for analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )

@router.post("/{analysis_id}/export")
async def export_analysis(
    analysis_id: str,
    format: str = "word",
    db: Session = Depends(get_db_session)
):
    """Export completed analysis to specified format."""
    try:
        analysis = db.query(Analysis).filter(Analysis.id == UUID(analysis_id)).first()
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )
        
        if analysis.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analysis must be completed before export"
            )
        
        if not analysis.final_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No final analysis available for export"
            )
        
        if format.lower() == "word":
            # TODO: Implement Word document generation
            # For now, return the text content
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content=analysis.final_analysis,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.txt"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    except Exception as e:
        logger.error(f"Failed to export analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export analysis: {str(e)}"
        )