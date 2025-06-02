"""
Workflow Manager for Legal Discovery Backend.
Handles LangGraph workflow execution, state management, and human feedback integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.orm import Session

# Import LangGraph components
import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from open_deep_research.legal_discovery import legal_graph
from open_deep_research.legal_state import LegalAnalysisState, AnalysisCategory
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

try:
    from .models import AnalysisDB, AnalysisCategory as AnalysisCategoryModel
    from .websocket_manager import WebSocketManager
except ImportError:
    from models import AnalysisDB, AnalysisCategory as AnalysisCategoryModel
    from websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

@dataclass
class WorkflowExecution:
    """Represents an active workflow execution."""
    analysis_id: str
    case_id: str
    task: Optional[asyncio.Task]
    status: str
    config: Dict[str, Any]
    checkpointer: BaseCheckpointSaver
    thread_id: str
    interrupt_event: Optional[asyncio.Event] = None
    feedback_data: Optional[Dict[str, Any]] = None

class WorkflowManager:
    """Manages LangGraph workflow executions and state."""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.websocket_manager: Optional[WebSocketManager] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the workflow manager."""
        try:
            # Import WebSocketManager to avoid circular imports
            try:
                from .websocket_manager import websocket_manager
            except ImportError:
                from websocket_manager import websocket_manager
            self.websocket_manager = websocket_manager
            
            self._initialized = True
            logger.info("Workflow manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize workflow manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup all active workflows."""
        logger.info("Cleaning up active workflows...")
        
        # Stop all active workflows
        for analysis_id in list(self.active_workflows.keys()):
            await self.stop_workflow(analysis_id)
        
        logger.info("Workflow manager cleanup complete")
    
    async def health_check(self) -> bool:
        """Check if workflow manager is healthy."""
        return self._initialized
    
    def get_active_workflow_count(self) -> int:
        """Get the number of active workflows."""
        return len(self.active_workflows)
    
    async def start_workflow(
        self,
        analysis_id: str,
        case_background: str,
        config: Dict[str, Any],
        db_session: Session
    ) -> None:
        """Start a new workflow execution."""
        try:
            # Check if workflow is already running
            if analysis_id in self.active_workflows:
                raise ValueError(f"Workflow {analysis_id} is already running")
            
            # Create checkpointer for state persistence
            checkpointer = MemorySaver()
            
            # Generate thread ID for this workflow execution
            thread_id = f"thread-{analysis_id}"
            
            # Create workflow execution
            execution = WorkflowExecution(
                analysis_id=analysis_id,
                case_id=config.get("case_id"),
                task=None,
                status="starting",
                config=config,
                checkpointer=checkpointer,
                thread_id=thread_id
            )
            
            self.active_workflows[analysis_id] = execution
            
            # Start workflow task
            task = asyncio.create_task(
                self._execute_workflow(
                    analysis_id=analysis_id,
                    case_background=case_background,
                    config=config,
                    checkpointer=checkpointer,
                    thread_id=thread_id,
                    db_session=db_session
                )
            )
            
            execution.task = task
            execution.status = "in_progress"
            
            logger.info(f"Started workflow for analysis {analysis_id}")
            
        except Exception as e:
            # Clean up on failure
            if analysis_id in self.active_workflows:
                del self.active_workflows[analysis_id]
            
            logger.error(f"Failed to start workflow for analysis {analysis_id}: {e}")
            raise
    
    async def _execute_workflow(
        self,
        analysis_id: str,
        case_background: str,
        config: Dict[str, Any],
        checkpointer: BaseCheckpointSaver,
        thread_id: str,
        db_session: Session
    ) -> None:
        """Execute the LangGraph workflow with proper error handling and progress tracking."""
        try:
            execution = self.active_workflows[analysis_id]
            
            # Prepare workflow input
            workflow_input = {
                "background_on_case": case_background
            }
            
            # Compile graph with checkpointer
            compiled_graph = legal_graph.compile(checkpointer=checkpointer)
            
            # Update analysis status
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="in_progress",
                current_step="generate_analysis_plan",
                progress_percentage=10,
                db_session=db_session
            )
            
            # Send initial progress update
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="in_progress",
                current_step="generate_analysis_plan",
                progress_percentage=10,
                message="Starting legal analysis workflow..."
            )
            
            # Execute workflow with interrupt handling
            final_state = None
            async for chunk in compiled_graph.astream(
                workflow_input,
                config={"configurable": config.get("configurable", {}), "thread_id": thread_id}
            ):
                # Handle workflow updates
                await self._handle_workflow_chunk(analysis_id, chunk, db_session)
                
                # Check for interrupts (human feedback requests)
                if chunk.get("__interrupt__"):
                    await self._handle_workflow_interrupt(analysis_id, chunk, db_session)
                    
                    # Wait for feedback
                    execution.interrupt_event = asyncio.Event()
                    await execution.interrupt_event.wait()
                    
                    # Resume with feedback
                    if execution.feedback_data:
                        # Continue workflow with feedback
                        continue
                
                final_state = chunk
            
            # Workflow completed successfully
            await self._complete_workflow(analysis_id, final_state, db_session)
            
        except asyncio.CancelledError:
            logger.info(f"Workflow {analysis_id} was cancelled")
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="stopped",
                db_session=db_session
            )
        except Exception as e:
            logger.error(f"Workflow {analysis_id} failed: {e}")
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="failed",
                current_step="error",
                db_session=db_session
            )
            
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="failed",
                message=f"Workflow failed: {str(e)}"
            )
        finally:
            # Clean up
            if analysis_id in self.active_workflows:
                del self.active_workflows[analysis_id]
    
    async def _handle_workflow_chunk(
        self,
        analysis_id: str,
        chunk: Dict[str, Any],
        db_session: Session
    ) -> None:
        """Handle individual workflow state updates."""
        try:
            # Extract current node and state
            current_node = chunk.get("__metadata__", {}).get("source", "unknown")
            state = chunk
            
            # Calculate progress based on completed steps
            progress_mapping = {
                "generate_analysis_plan": 20,
                "human_feedback": 30,
                "analyze_category_with_documents": 60,
                "gather_completed_categories": 70,
                "analyze_final_categories": 80,
                "generate_deposition_questions": 90,
                "compile_final_analysis": 95
            }
            
            progress = progress_mapping.get(current_node, 0)
            
            # Update categories if available
            categories = state.get("categories", [])
            completed_categories = state.get("completed_categories", [])
            
            if categories:
                await self._update_analysis_categories(
                    analysis_id=analysis_id,
                    categories=categories,
                    completed_categories=completed_categories,
                    db_session=db_session
                )
            
            # Update analysis status
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="in_progress",
                current_step=current_node,
                progress_percentage=progress,
                categories_completed=len(completed_categories),
                total_categories=len(categories),
                db_session=db_session
            )
            
            # Send progress update
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="in_progress",
                current_step=current_node,
                progress_percentage=progress,
                categories_completed=len(completed_categories),
                total_categories=len(categories),
                message=f"Processing step: {current_node.replace('_', ' ').title()}"
            )
            
        except Exception as e:
            logger.error(f"Error handling workflow chunk for {analysis_id}: {e}")
    
    async def _handle_workflow_interrupt(
        self,
        analysis_id: str,
        chunk: Dict[str, Any],
        db_session: Session
    ) -> None:
        """Handle workflow interrupts (human feedback requests)."""
        try:
            # Extract feedback request info
            interrupt_info = chunk.get("__interrupt__", {})
            message = interrupt_info.get("message", "Human feedback required")
            
            # Update analysis to show feedback is requested
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="pending_feedback",
                feedback_requested=True,
                feedback_message=message,
                db_session=db_session
            )
            
            # Send feedback request via WebSocket
            await self._send_feedback_request(
                analysis_id=analysis_id,
                message=message,
                context=chunk
            )
            
        except Exception as e:
            logger.error(f"Error handling workflow interrupt for {analysis_id}: {e}")
    
    async def _complete_workflow(
        self,
        analysis_id: str,
        final_state: Dict[str, Any],
        db_session: Session
    ) -> None:
        """Complete the workflow and update final results."""
        try:
            # Extract final results
            final_analysis = final_state.get("final_analysis", "")
            deposition_questions = final_state.get("deposition_questions")
            completed_categories = final_state.get("completed_categories", [])
            
            # Update analysis with final results
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if analysis_db:
                analysis_db.status = "completed"
                analysis_db.current_step = "completed"
                analysis_db.progress_percentage = 100
                analysis_db.final_analysis = final_analysis
                analysis_db.completed_at = datetime.utcnow()
                
                if deposition_questions:
                    analysis_db.deposition_questions = deposition_questions.dict() if hasattr(deposition_questions, 'dict') else deposition_questions
                
                if completed_categories:
                    analysis_db.completed_categories = [
                        cat.dict() if hasattr(cat, 'dict') else cat
                        for cat in completed_categories
                    ]
                
                db_session.commit()
            
            # Send completion update
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="completed",
                current_step="completed",
                progress_percentage=100,
                message="Legal analysis completed successfully!"
            )
            
            logger.info(f"Workflow {analysis_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing workflow {analysis_id}: {e}")
    
    async def _update_analysis_status(
        self,
        analysis_id: str,
        status: str,
        current_step: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        categories_completed: Optional[int] = None,
        total_categories: Optional[int] = None,
        feedback_requested: Optional[bool] = None,
        feedback_message: Optional[str] = None,
        db_session: Session = None
    ) -> None:
        """Update analysis status in database."""
        try:
            if not db_session:
                return
            
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if not analysis_db:
                return
            
            # Update fields
            analysis_db.status = status
            analysis_db.updated_at = datetime.utcnow()
            
            if current_step is not None:
                analysis_db.current_step = current_step
            
            if progress_percentage is not None:
                analysis_db.progress_percentage = progress_percentage
            
            if categories_completed is not None:
                analysis_db.categories_completed = categories_completed
            
            if total_categories is not None:
                analysis_db.total_categories = total_categories
            
            if feedback_requested is not None:
                analysis_db.feedback_requested = feedback_requested
            
            if feedback_message is not None:
                analysis_db.feedback_message = feedback_message
            
            db_session.commit()
            
        except Exception as e:
            logger.error(f"Error updating analysis status for {analysis_id}: {e}")
    
    async def _update_analysis_categories(
        self,
        analysis_id: str,
        categories: List[Any],
        completed_categories: List[Any],
        db_session: Session
    ) -> None:
        """Update analysis categories in database."""
        try:
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if not analysis_db:
                return
            
            # Convert categories to dict format
            categories_dict = []
            for cat in categories:
                if hasattr(cat, 'dict'):
                    categories_dict.append(cat.dict())
                elif isinstance(cat, dict):
                    categories_dict.append(cat)
                else:
                    # Try to extract fields from object
                    cat_dict = {
                        "name": getattr(cat, 'name', ''),
                        "description": getattr(cat, 'description', ''),
                        "requires_document_search": getattr(cat, 'requires_document_search', False),
                        "content": getattr(cat, 'content', '')
                    }
                    categories_dict.append(cat_dict)
            
            completed_categories_dict = []
            for cat in completed_categories:
                if hasattr(cat, 'dict'):
                    completed_categories_dict.append(cat.dict())
                elif isinstance(cat, dict):
                    completed_categories_dict.append(cat)
                else:
                    # Try to extract fields from object
                    cat_dict = {
                        "name": getattr(cat, 'name', ''),
                        "description": getattr(cat, 'description', ''),
                        "requires_document_search": getattr(cat, 'requires_document_search', False),
                        "content": getattr(cat, 'content', '')
                    }
                    completed_categories_dict.append(cat_dict)
            
            analysis_db.categories = categories_dict
            analysis_db.completed_categories = completed_categories_dict
            db_session.commit()
            
        except Exception as e:
            logger.error(f"Error updating categories for {analysis_id}: {e}")
    
    async def _send_progress_update(
        self,
        analysis_id: str,
        status: str,
        current_step: Optional[str] = None,
        progress_percentage: int = 0,
        categories_completed: int = 0,
        total_categories: int = 0,
        message: Optional[str] = None
    ) -> None:
        """Send progress update via WebSocket."""
        try:
            if not self.websocket_manager:
                return
            
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                return
            
            update_data = {
                "type": "progress_update",
                "analysis_id": analysis_id,
                "status": status,
                "current_step": current_step,
                "progress_percentage": progress_percentage,
                "categories_completed": categories_completed,
                "total_categories": total_categories,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket_manager.broadcast_to_case(
                case_id=execution.case_id,
                message=update_data
            )
            
        except Exception as e:
            logger.error(f"Error sending progress update for {analysis_id}: {e}")
    
    async def _send_feedback_request(
        self,
        analysis_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """Send feedback request via WebSocket."""
        try:
            if not self.websocket_manager:
                return
            
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                return
            
            request_data = {
                "type": "feedback_requested",
                "analysis_id": analysis_id,
                "message": message,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket_manager.broadcast_to_case(
                case_id=execution.case_id,
                message=request_data
            )
            
        except Exception as e:
            logger.error(f"Error sending feedback request for {analysis_id}: {e}")
    
    async def pause_workflow(self, analysis_id: str) -> None:
        """Pause a running workflow."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution or not execution.task:
                raise ValueError(f"No active workflow found for analysis {analysis_id}")
            
            execution.status = "paused"
            # Note: LangGraph workflows pause naturally at interrupt points
            logger.info(f"Paused workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to pause workflow {analysis_id}: {e}")
            raise
    
    async def resume_workflow(self, analysis_id: str) -> None:
        """Resume a paused workflow."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                raise ValueError(f"No workflow found for analysis {analysis_id}")
            
            execution.status = "in_progress"
            
            # If there's an interrupt event, signal it to resume
            if execution.interrupt_event:
                execution.interrupt_event.set()
            
            logger.info(f"Resumed workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to resume workflow {analysis_id}: {e}")
            raise
    
    async def stop_workflow(self, analysis_id: str) -> None:
        """Stop a running workflow."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                logger.warning(f"No workflow found for analysis {analysis_id}")
                return
            
            # Cancel the task
            if execution.task and not execution.task.done():
                execution.task.cancel()
            
            # Signal any waiting interrupt events
            if execution.interrupt_event:
                execution.interrupt_event.set()
            
            # Remove from active workflows
            del self.active_workflows[analysis_id]
            
            logger.info(f"Stopped workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop workflow {analysis_id}: {e}")
            raise
    
    async def provide_feedback(
        self,
        analysis_id: str,
        feedback: str,
        approve: Optional[bool] = None
    ) -> None:
        """Provide human feedback to a workflow waiting for input."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                raise ValueError(f"No active workflow found for analysis {analysis_id}")
            
            # Store feedback data
            execution.feedback_data = {
                "feedback": feedback,
                "approve": approve,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Signal the workflow to resume
            if execution.interrupt_event:
                execution.interrupt_event.set()
            
            logger.info(f"Provided feedback to workflow {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to provide feedback to workflow {analysis_id}: {e}")
            raise
    
    async def stop_case_workflows(self, case_id: str) -> None:
        """Stop all workflows for a specific case."""
        try:
            workflows_to_stop = [
                analysis_id for analysis_id, execution in self.active_workflows.items()
                if execution.case_id == case_id
            ]
            
            for analysis_id in workflows_to_stop:
                await self.stop_workflow(analysis_id)
            
            logger.info(f"Stopped {len(workflows_to_stop)} workflows for case {case_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop workflows for case {case_id}: {e}")
            raise