#!/usr/bin/env python3
"""
Simplified Legal Discovery Backend for testing.
This version bypasses complex dependencies while providing full API functionality.
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

# Simple imports without complex dependencies
from config import config
from database import get_db_session, init_database, check_database_health
from models import (
    Case, Analysis, Comment,
    CaseDB, AnalysisDB, CommentDB,
    CaseCreateRequest, CaseUpdateRequest, WorkflowControlRequest, CommentCreateRequest,
    AnalysisCategory
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock workflow manager for testing
class MockWorkflowManager:
    def __init__(self):
        self.active_workflows = {}
    
    async def initialize(self):
        logger.info("Mock workflow manager initialized")
    
    async def cleanup(self):
        logger.info("Mock workflow manager cleaned up")
    
    async def health_check(self):
        return True
    
    def get_active_workflow_count(self):
        return len(self.active_workflows)
    
    async def start_workflow(self, analysis_id: str, case_background: str, config: Dict[str, Any], db_session: Session):
        """Start a mock workflow that simulates analysis progress."""
        logger.info(f"Starting mock workflow for analysis {analysis_id}")
        
        # Update analysis status
        analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if analysis_db:
            analysis_db.status = "in_progress"
            analysis_db.current_step = "generate_analysis_plan"
            analysis_db.progress_percentage = 20
            db_session.commit()
        
        # Store in active workflows
        self.active_workflows[analysis_id] = {
            "status": "in_progress",
            "started_at": datetime.utcnow()
        }
        
        # Simulate workflow progress
        asyncio.create_task(self._simulate_workflow_progress(analysis_id, db_session))
    
    async def _simulate_workflow_progress(self, analysis_id: str, db_session: Session):
        """Simulate workflow progress for demo purposes."""
        try:
            await asyncio.sleep(2)  # Simulate planning
            
            # Update to document analysis
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if analysis_db:
                analysis_db.current_step = "analyze_categories"
                analysis_db.progress_percentage = 60
                
                # Add mock categories
                mock_categories = [
                    {
                        "name": "Contract Analysis",
                        "description": "Review and analysis of contract terms and obligations",
                        "requires_document_search": True,
                        "content": "Preliminary contract analysis shows key obligations and potential breach areas."
                    },
                    {
                        "name": "Damages Assessment",
                        "description": "Evaluation of monetary damages and losses",
                        "requires_document_search": False,
                        "content": "Initial damages assessment indicates potential liability in the range of $100,000-$500,000."
                    }
                ]
                
                analysis_db.categories = mock_categories
                analysis_db.total_categories = len(mock_categories)
                db_session.commit()
            
            await asyncio.sleep(3)  # Simulate category analysis
            
            # Complete workflow
            if analysis_db:
                analysis_db.status = "completed"
                analysis_db.current_step = "completed"
                analysis_db.progress_percentage = 100
                analysis_db.categories_completed = 2
                analysis_db.completed_categories = mock_categories
                analysis_db.final_analysis = "Based on the analysis of contract terms and damages assessment, there are significant liability concerns. Recommend immediate settlement negotiations."
                analysis_db.completed_at = datetime.utcnow()
                
                # Add mock deposition questions
                analysis_db.deposition_questions = {
                    "witness_questions": [
                        {
                            "witness_name": "Contract Signatory",
                            "witness_role": "Primary decision maker for contract execution",
                            "questions": [
                                {
                                    "question": "What was your understanding of the delivery timeline obligations?",
                                    "purpose": "Establish knowledge of contract terms",
                                    "expected_areas": ["Timeline awareness", "Authority level"]
                                }
                            ]
                        }
                    ]
                }
                
                db_session.commit()
            
            # Remove from active workflows
            if analysis_id in self.active_workflows:
                del self.active_workflows[analysis_id]
            
            logger.info(f"Mock workflow completed for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Mock workflow failed for {analysis_id}: {e}")
            
            # Mark as failed
            if analysis_db:
                analysis_db.status = "failed"
                analysis_db.current_step = "error"
                db_session.commit()
            
            if analysis_id in self.active_workflows:
                del self.active_workflows[analysis_id]
    
    async def stop_workflow(self, analysis_id: str):
        if analysis_id in self.active_workflows:
            del self.active_workflows[analysis_id]
            logger.info(f"Stopped workflow {analysis_id}")
    
    async def stop_case_workflows(self, case_id: str):
        logger.info(f"Stopped workflows for case {case_id}")

# Mock WebSocket manager
class MockWebSocketManager:
    def __init__(self):
        self.connections = {}
    
    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    async def disconnect(self, client_id: str):
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        logger.debug(f"Received message from {client_id}: {message}")
    
    async def broadcast_to_case(self, case_id: str, message: Dict[str, Any]):
        logger.debug(f"Broadcasting to case {case_id}: {message}")
    
    async def cleanup(self):
        logger.info("WebSocket manager cleaned up")
    
    def get_connection_count(self):
        return len(self.connections)

# Initialize services
workflow_manager = MockWorkflowManager()
websocket_manager = MockWebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Legal Discovery Backend (Simplified)...")
    
    try:
        init_database()
        await workflow_manager.initialize()
        logger.info("Legal Discovery Backend started successfully")
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
    title="Legal Discovery Backend",
    description="AI-powered legal case analysis system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "legal-discovery-backend-simplified",
        "version": "1.0.0",
        "database": "healthy" if db_healthy else "unhealthy",
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

@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str, db: Session = Depends(get_db)):
    """Start legal analysis workflow for a case."""
    try:
        # Get case
        case_db = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not case_db:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Check if case already has an active analysis
        active_analysis = db.query(AnalysisDB).filter(
            and_(
                AnalysisDB.case_id == case_id,
                AnalysisDB.status.in_(["pending", "in_progress", "paused"])
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
        
        # Start mock workflow
        workflow_config = {"case_id": case_id, "analysis_id": analysis_id}
        await workflow_manager.start_workflow(
            analysis_id=analysis_id,
            case_background=case_db.background,
            config=workflow_config,
            db_session=db
        )
        
        logger.info(f"Started analysis workflow: {analysis_id} for case: {case_id}")
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "Legal analysis workflow started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to start analysis for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start analysis")

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
    """Control workflow execution (pause, resume, stop, provide feedback)."""
    try:
        analysis_db = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if not analysis_db:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        action = control_request.action
        
        if action == "stop":
            await workflow_manager.stop_workflow(analysis_id)
            analysis_db.status = "stopped"
            analysis_db.completed_at = datetime.utcnow()
        else:
            logger.info(f"Mock action '{action}' applied to analysis {analysis_id}")
        
        analysis_db.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "analysis_id": analysis_id,
            "action": action,
            "status": analysis_db.status,
            "message": f"Workflow {action} applied successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to control workflow {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to control workflow")

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
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )