#!/usr/bin/env python3
"""
Complete Legal Discovery Backend with Real LangGraph Integration.
This version uses your actual legal_discovery.py workflow.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Import local modules
try:
    from .config import config, get_workflow_config
    from .database import get_db_session, init_database, check_database_health
    from .models import (
        Case, Analysis, Comment,
        CaseDB, AnalysisDB, CommentDB,
        CaseCreateRequest, CaseUpdateRequest, WorkflowControlRequest, CommentCreateRequest,
        AnalysisCategory
    )
    from .real_workflow_manager import RealWorkflowManager
    from .websocket_manager import WebSocketManager
    from .document_service import DocumentService
    from .export_service import ExportService
except ImportError:
    # Handle relative imports when running directly
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    from config import config, get_workflow_config
    from database import get_db_session, init_database, check_database_health
    from models import (
        Case, Analysis, Comment,
        CaseDB, AnalysisDB, CommentDB,
        CaseCreateRequest, CaseUpdateRequest, WorkflowControlRequest, CommentCreateRequest,
        AnalysisCategory
    )
    from real_workflow_manager import RealWorkflowManager
    from websocket_manager import WebSocketManager
    from document_service import DocumentService
    from export_service import ExportService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services with real LangGraph workflow
workflow_manager = RealWorkflowManager()
websocket_manager = WebSocketManager()
document_service = DocumentService()
export_service = ExportService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Legal Discovery Backend with Real LangGraph...")
    
    try:
        init_database()
        await workflow_manager.initialize(websocket_manager)
        await document_service.initialize()
        logger.info("Legal Discovery Backend with LangGraph started successfully")
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Discovery Backend...")
    await workflow_manager.cleanup()
    await websocket_manager.cleanup()
    logger.info("Legal Discovery Backend shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Legal Discovery Backend - LangGraph",
    description="AI-powered legal case analysis with real LangGraph workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for database session
def get_db() -> Session:
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def case_db_to_pydantic(case_db: CaseDB, include_analyses: bool = True) -> Case:
    """Convert SQLAlchemy Case model to Pydantic model."""
    analyses = []
    if include_analyses:
        for analysis_db in case_db.analyses:
            analyses.append(analysis_db_to_pydantic(analysis_db))
    
    comments = [comment_db_to_pydantic(comment_db) for comment_db in case_db.comments]
    
    return Case(
        id=case_db.id,
        title=case_db.title,
        background=case_db.background,
        status=case_db.status,
        analysis_structure=case_db.analysis_structure,
        number_of_queries=case_db.number_of_queries,
        max_search_depth=case_db.max_search_depth,
        created_at=case_db.created_at,
        updated_at=case_db.updated_at,
        analyses=analyses,
        comments=comments
    )

def analysis_db_to_pydantic(analysis_db: AnalysisDB) -> Analysis:
    """Convert SQLAlchemy Analysis model to Pydantic model."""
    return Analysis(
        id=analysis_db.id,
        case_id=analysis_db.case_id,
        status=analysis_db.status,
        current_step=analysis_db.current_step,
        progress_percentage=analysis_db.progress_percentage,
        categories_completed=analysis_db.categories_completed,
        total_categories=analysis_db.total_categories,
        feedback_requested=analysis_db.feedback_requested,
        feedback_message=analysis_db.feedback_message,
        categories=[AnalysisCategory(**cat) for cat in (analysis_db.categories or [])],
        completed_categories=[AnalysisCategory(**cat) for cat in (analysis_db.completed_categories or [])],
        category_progress=analysis_db.category_progress or [],
        deposition_questions=analysis_db.deposition_questions,
        final_analysis=analysis_db.final_analysis,
        created_at=analysis_db.created_at,
        updated_at=analysis_db.updated_at,
        completed_at=analysis_db.completed_at
    )

def comment_db_to_pydantic(comment_db: CommentDB) -> Comment:
    """Convert SQLAlchemy Comment model to Pydantic model."""
    return Comment(
        id=comment_db.id,
        case_id=comment_db.case_id,
        analysis_id=comment_db.analysis_id,
        content=comment_db.content,
        context_type=comment_db.context_type,
        context_reference=comment_db.context_reference,
        created_at=comment_db.created_at
    )

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = check_database_health()
    workflow_healthy = await workflow_manager.health_check()
    
    return {
        "status": "healthy" if all([db_healthy, workflow_healthy]) else "degraded",
        "service": "legal-discovery-backend-langgraph",
        "version": "1.0.0",
        "database": "healthy" if db_healthy else "unhealthy",
        "langgraph": "healthy" if workflow_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    db_healthy = check_database_health()
    workflow_healthy = await workflow_manager.health_check()
    
    return {
        "status": "healthy" if all([db_healthy, workflow_healthy]) else "degraded",
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "workflow_manager": "healthy" if workflow_healthy else "unhealthy",
            "websocket_manager": "healthy",
            "document_service": "healthy",
            "export_service": "healthy"
        },
        "active_websockets": websocket_manager.get_connection_count(),
        "active_workflows": workflow_manager.get_active_workflow_count(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Case management endpoints
@app.get("/api/v1/cases", response_model=List[Case])
async def list_cases(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all cases with optional filtering and pagination."""
    try:
        query = db.query(CaseDB)
        
        if status_filter:
            query = query.filter(CaseDB.status == status_filter)
        
        cases_db = query.offset(skip).limit(limit).all()
        return [case_db_to_pydantic(case_db, include_analyses=False) for case_db in cases_db]
        
    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cases")

@app.get("/api/v1/cases/{case_id}", response_model=Case)
async def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get a specific case with all related data."""
    try:
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return case_db_to_pydantic(case_db, include_analyses=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve case")

@app.post("/api/v1/cases", response_model=Case)
async def create_case(case_data: CaseCreateRequest, db: Session = Depends(get_db)):
    """Create a new legal case."""
    try:
        case_id = f"case-{str(uuid.uuid4())[:8]}"
        now = datetime.utcnow()
        
        case_db = CaseDB(
            id=case_id,
            title=case_data.case_title,
            background=case_data.case_background,
            status="draft",
            analysis_structure=case_data.analysis_structure,
            number_of_queries=case_data.number_of_queries or 5,
            max_search_depth=case_data.max_search_depth or 3,
            created_at=now,
            updated_at=now
        )
        
        db.add(case_db)
        db.commit()
        db.refresh(case_db)
        
        logger.info(f"Created new case: {case_id}")
        return case_db_to_pydantic(case_db)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create case: {e}")
        raise HTTPException(status_code=500, detail="Failed to create case")

@app.put("/api/v1/cases/{case_id}", response_model=Case)
async def update_case(
    case_id: str, 
    case_update: CaseUpdateRequest, 
    db: Session = Depends(get_db)
):
    """Update an existing case."""
    try:
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Update fields that were provided
        update_data = case_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case_db, field, value)
        
        case_db.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(case_db)
        
        logger.info(f"Updated case: {case_id}")
        return case_db_to_pydantic(case_db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update case")

@app.delete("/api/v1/cases/{case_id}")
async def delete_case(case_id: str, db: Session = Depends(get_db)):
    """Delete a case and all related data."""
    try:
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Stop any running workflows for this case
        await workflow_manager.stop_case_workflows(case_id)
        
        # Delete related documents from filesystem and Weaviate
        for analysis_db in case_db.analyses:
            await document_service.cleanup_analysis_documents(analysis_db.id)
        
        db.delete(case_db)
        db.commit()
        
        logger.info(f"Deleted case: {case_id}")
        return {"message": "Case deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete case")

# Analysis workflow endpoints
@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str, db: Session = Depends(get_db)):
    """Start real LangGraph legal analysis workflow for a case."""
    try:
        # Get case
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Check if case already has an active analysis
        active_analysis = db.query(AnalysisDB).filter(
            and_(
                AnalysisDB.case_id == case_id,
                AnalysisDB.status.in_(["pending", "in_progress", "paused", "pending_feedback"])
            )
        ).first()
        
        if active_analysis:
            raise HTTPException(status_code=400, detail="Case already has an active analysis")
        
        # Create new analysis
        analysis_id = f"analysis-{case_id}-{str(uuid.uuid4())[:8]}"
        now = datetime.utcnow()
        
        analysis_db = AnalysisDB(
            id=analysis_id,
            case_id=case_id,
            status="pending",
            current_step="initializing",
            progress_percentage=0,
            categories_completed=0,
            total_categories=0,
            feedback_requested=False,
            created_at=now,
            updated_at=now
        )
        
        db.add(analysis_db)
        db.commit()
        db.refresh(analysis_db)
        
        # Update case status
        case_db.status = "analyzing"
        db.commit()
        
        # Start real LangGraph workflow
        workflow_config = get_workflow_config(config)
        workflow_config["case_id"] = case_id
        workflow_config["analysis_id"] = analysis_id
        workflow_config["analysis_structure"] = case_db.analysis_structure
        workflow_config["number_of_queries"] = case_db.number_of_queries
        workflow_config["max_search_depth"] = case_db.max_search_depth
        
        await workflow_manager.start_workflow(
            analysis_id=analysis_id,
            case_background=case_db.background,
            config=workflow_config,
            db_session=db
        )
        
        logger.info(f"Started real LangGraph analysis: {analysis_id} for case: {case_id}")
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "Real LangGraph legal analysis workflow started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to start real analysis for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.get("/api/v1/analysis/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Get analysis details and status."""
    try:
        analysis_db = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if not analysis_db:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return analysis_db_to_pydantic(analysis_db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis")

@app.post("/api/v1/analysis/{analysis_id}/control")
async def control_workflow(
    analysis_id: str,
    control_request: WorkflowControlRequest,
    db: Session = Depends(get_db)
):
    """Control real LangGraph workflow execution (pause, resume, stop, provide feedback)."""
    try:
        analysis_db = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if not analysis_db:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        action = control_request.action
        
        if action == "pause":
            await workflow_manager.pause_workflow(analysis_id)
            analysis_db.status = "paused"
            
        elif action == "resume":
            await workflow_manager.resume_workflow(analysis_id)
            analysis_db.status = "in_progress"
            
        elif action == "stop":
            await workflow_manager.stop_workflow(analysis_id)
            analysis_db.status = "stopped"
            analysis_db.completed_at = datetime.utcnow()
            
        elif action == "feedback":
            if not control_request.feedback:
                raise HTTPException(status_code=400, detail="Feedback content is required")
            
            await workflow_manager.provide_feedback(
                analysis_id=analysis_id,
                feedback=control_request.feedback,
                approve=control_request.approve
            )
            
            analysis_db.feedback_requested = False
            analysis_db.feedback_message = None
            analysis_db.status = "in_progress"
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        analysis_db.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Real workflow control action '{action}' applied to analysis {analysis_id}")
        
        return {
            "analysis_id": analysis_id,
            "action": action,
            "status": analysis_db.status,
            "message": f"Real workflow {action} applied successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to control real workflow {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to control workflow")

# Comments endpoints
@app.post("/api/v1/cases/{case_id}/comments", response_model=Comment)
async def add_comment(
    case_id: str,
    comment_request: CommentCreateRequest,
    analysis_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Add a comment to a case or analysis."""
    try:
        # Verify case exists
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Verify analysis exists if provided
        if analysis_id:
            analysis_db = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if not analysis_db:
                raise HTTPException(status_code=404, detail="Analysis not found")
        
        comment_id = f"comment-{str(uuid.uuid4())[:8]}"
        comment_db = CommentDB(
            id=comment_id,
            case_id=case_id,
            analysis_id=analysis_id,
            content=comment_request.content,
            context_type=comment_request.context_type,
            context_reference=comment_request.context_reference,
            created_at=datetime.utcnow()
        )
        
        db.add(comment_db)
        db.commit()
        db.refresh(comment_db)
        
        logger.info(f"Added comment {comment_id} to case {case_id}")
        
        # Notify WebSocket clients
        await websocket_manager.broadcast_to_case(
            case_id=case_id,
            message={
                "type": "comment_added",
                "comment": comment_db_to_pydantic(comment_db).dict()
            }
        )
        
        return comment_db_to_pydantic(comment_db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add comment to case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add comment")

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(client_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await websocket_manager.handle_message(client_id, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}: {data}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await websocket_manager.disconnect(client_id)

if __name__ == "__main__":
    print("🚀 Starting Legal Discovery Backend with Real LangGraph...")
    print("=" * 60)
    print("🧠 LangGraph workflow: REAL (using your legal_discovery.py)")
    print("📊 Database: SQLite with full persistence")
    print("🔄 WebSocket: Real-time updates enabled")
    print("🌐 Server: http://0.0.0.0:8000")
    print("📚 API docs: http://0.0.0.0:8000/docs")
    print("❤️  Health: http://0.0.0.0:8000/health")
    print("=" * 60)
    print("⚠️  Make sure to set your API keys:")
    print("   OPENAI_API_KEY=your_openai_key")
    print("   ANTHROPIC_API_KEY=your_anthropic_key")
    print("=" * 60)
    
    uvicorn.run(
        "langgraph_main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )