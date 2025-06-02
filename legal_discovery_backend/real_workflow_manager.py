"""
Real Workflow Manager for Legal Discovery Backend.
Handles actual LangGraph workflow execution with your legal_discovery.py.
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

from open_deep_research.legal_discovery import builder
from open_deep_research.legal_state import LegalAnalysisState, AnalysisCategory
from open_deep_research.configuration import Configuration
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
    last_state: Optional[Dict[str, Any]] = None

class RealWorkflowManager:
    """Manages actual LangGraph workflow executions."""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.websocket_manager: Optional[WebSocketManager] = None
        self._initialized = False
    
    async def initialize(self, websocket_manager=None):
        """Initialize the workflow manager."""
        try:
            # Use provided websocket_manager or try to import it
            if websocket_manager:
                self.websocket_manager = websocket_manager
            else:
                # Import WebSocketManager to avoid circular imports
                try:
                    from .websocket_manager import websocket_manager
                except ImportError:
                    from websocket_manager import websocket_manager
                self.websocket_manager = websocket_manager
            
            self._initialized = True
            logger.info("Real workflow manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize real workflow manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup all active workflows."""
        logger.info("Cleaning up active workflows...")
        
        # Stop all active workflows
        for analysis_id in list(self.active_workflows.keys()):
            await self.stop_workflow(analysis_id)
        
        logger.info("Real workflow manager cleanup complete")
    
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
        """Start a new LangGraph workflow execution."""
        try:
            logger.info(f"🔥 REAL LANGGRAPH WORKFLOW START REQUEST for analysis {analysis_id}")
            logger.info(f"📋 Case background: {case_background}")
            logger.info(f"🛠️  Config: {config}")
            
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
                self._execute_langgraph_workflow(
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
            
            logger.info(f"Started real LangGraph workflow for analysis {analysis_id}")
            
        except Exception as e:
            # Clean up on failure
            if analysis_id in self.active_workflows:
                del self.active_workflows[analysis_id]
            
            logger.error(f"❌ Failed to start real workflow for analysis {analysis_id}: {e}")
            logger.error(f"🔍 Startup error type: {type(e).__name__}")
            logger.error(f"📍 Startup error details: {str(e)}")
            import traceback
            logger.error(f"📋 Startup error traceback:\n{traceback.format_exc()}")
            raise
    
    async def _execute_langgraph_workflow(
        self,
        analysis_id: str,
        case_background: str,
        config: Dict[str, Any],
        checkpointer: BaseCheckpointSaver,
        thread_id: str,
        db_session: Session
    ) -> None:
        """Execute the actual LangGraph legal discovery workflow."""
        try:
            execution = self.active_workflows[analysis_id]
            
            # Prepare workflow input (matching your legal_discovery.py expected input format)
            workflow_input = {
                "background_on_case": case_background
            }
            
            # Create configuration for the workflow
            workflow_config = {
                "configurable": {
                    # Required thread_id for checkpointer
                    "thread_id": thread_id,
                    
                    # Model configuration
                    "writer_provider": config.get("writer_provider", "openai"),
                    "writer_model": config.get("writer_model", "gpt-4o"),
                    "planner_provider": config.get("planner_provider", "openai"),
                    "planner_model": config.get("planner_model", "gpt-4o"),
                    
                    # Analysis configuration
                    "analysis_structure": config.get("analysis_structure", 
                        "liability analysis, damages assessment, key witnesses, timeline of events, document evidence, deposition strategy"),
                    "number_of_queries": config.get("number_of_queries", 5),
                    "max_search_depth": config.get("max_search_depth", 3),
                    
                    # Document search configuration (get from configurable section)
                    "azure_search_endpoint": config.get("configurable", {}).get("azure_search_endpoint"),
                    "azure_search_key": config.get("configurable", {}).get("azure_search_key"),
                    "azure_search_index": config.get("configurable", {}).get("azure_search_index"),
                    "weaviate_url": config.get("configurable", {}).get("weaviate_url"),
                    "weaviate_api_key": config.get("configurable", {}).get("weaviate_api_key"),
                    "weaviate_collection_name": config.get("configurable", {}).get("weaviate_collection_name"),
                }
            }
            
            # Compile graph with our checkpointer for state persistence
            compiled_graph = builder.compile(checkpointer=checkpointer)
            
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
            step_count = 0
            
            logger.info(f"🚀 Starting LangGraph workflow execution for analysis {analysis_id}")
            logger.info(f"📝 Workflow input: {workflow_input}")
            logger.info(f"⚙️  Workflow config: {workflow_config}")
            
            async for chunk in compiled_graph.astream(
                workflow_input,
                config=workflow_config
            ):
                step_count += 1
                logger.info(f"📊 LangGraph Step {step_count} for {analysis_id}: {list(chunk.keys()) if chunk else 'empty'}")
                if chunk:
                    logger.info(f"🔍 Chunk content: {chunk}")
                
                # Handle workflow updates
                await self._handle_workflow_chunk(analysis_id, chunk, db_session)
                
                # Check for interrupts (human feedback requests)
                if "__interrupt__" in chunk:
                    await self._handle_workflow_interrupt(analysis_id, chunk, db_session)
                    
                    # Wait for feedback
                    execution.interrupt_event = asyncio.Event()
                    logger.info(f"Workflow {analysis_id} paused for human feedback")
                    await execution.interrupt_event.wait()
                    logger.info(f"Workflow {analysis_id} resuming with feedback")
                    
                    # Resume with feedback
                    if execution.feedback_data:
                        # Add feedback to workflow state
                        feedback_input = {
                            **workflow_input,
                            "feedback_on_analysis_plan": [execution.feedback_data.get("feedback", "")]
                        }
                        workflow_input = feedback_input
                        execution.feedback_data = None
                
                final_state = chunk
            
            # Workflow completed successfully
            await self._complete_workflow(analysis_id, final_state, db_session)
            
        except asyncio.CancelledError:
            logger.info(f"Real workflow {analysis_id} was cancelled")
            await self._update_analysis_status(
                analysis_id=analysis_id,
                status="stopped",
                db_session=db_session
            )
        except Exception as e:
            logger.error(f"❌ Real workflow {analysis_id} failed with error: {e}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            logger.error(f"📍 Error details: {str(e)}")
            import traceback
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
            
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
            # Extract current node from chunk metadata
            current_node = None
            if "__metadata__" in chunk and "langgraph_node" in chunk["__metadata__"]:
                current_node = chunk["__metadata__"]["langgraph_node"]
            elif len(chunk) == 1:
                # If only one key, it's likely the current node
                current_node = list(chunk.keys())[0]
            
            if not current_node:
                return
            
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
            
            # Extract state from chunk (safely handle non-dict values)
            if isinstance(chunk, dict):
                state = chunk.get(current_node, chunk)
            else:
                state = chunk
            
            # Update categories if available (safely handle non-dict state)
            categories = []
            completed_categories = []
            if isinstance(state, dict):
                categories = state.get("categories", [])
                completed_categories = state.get("completed_categories", [])
            
            if categories:
                await self._update_analysis_categories(
                    analysis_id=analysis_id,
                    categories=categories,
                    completed_categories=completed_categories,
                    db_session=db_session
                )
                
                # Store the state for later use in interrupts
                execution = self.active_workflows.get(analysis_id)
                if execution:
                    execution.last_state = state
            
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
            # Extract feedback request info (handle dict vs other types)
            if isinstance(chunk, dict):
                interrupt_data = chunk.get("__interrupt__", ())
            else:
                interrupt_data = ()
            
            # Handle the tuple structure: (Interrupt(value="...", resumable=True, ns=[...]),)
            message = "Human feedback required for analysis plan"
            if interrupt_data and len(interrupt_data) > 0:
                interrupt_obj = interrupt_data[0]
                if hasattr(interrupt_obj, 'value'):
                    message = interrupt_obj.value
                elif hasattr(interrupt_obj, 'message'):
                    message = interrupt_obj.message
            
            # Extract categories from chunk for frontend display
            categories = []
            if isinstance(chunk, dict):
                # Try to get categories from different possible locations in the chunk
                for key, value in chunk.items():
                    if isinstance(value, dict) and 'categories' in value:
                        raw_categories = value['categories']
                        # Convert AnalysisCategory objects to dictionaries
                        if raw_categories:
                            for cat in raw_categories:
                                if hasattr(cat, 'model_dump'):
                                    categories.append(cat.model_dump())
                                elif hasattr(cat, 'dict'):
                                    categories.append(cat.dict())
                                elif hasattr(cat, 'name') and hasattr(cat, 'description'):
                                    categories.append({
                                        'name': cat.name,
                                        'description': cat.description,
                                        'requires_document_search': getattr(cat, 'requires_document_search', False)
                                    })
                                elif isinstance(cat, dict):
                                    categories.append(cat)
                        break
                    elif key == 'generate_analysis_plan' and isinstance(value, dict) and 'categories' in value:
                        raw_categories = value['categories']
                        # Convert AnalysisCategory objects to dictionaries
                        if raw_categories:
                            for cat in raw_categories:
                                if hasattr(cat, 'model_dump'):
                                    categories.append(cat.model_dump())
                                elif hasattr(cat, 'dict'):
                                    categories.append(cat.dict())
                                elif hasattr(cat, 'name') and hasattr(cat, 'description'):
                                    categories.append({
                                        'name': cat.name,
                                        'description': cat.description,
                                        'requires_document_search': getattr(cat, 'requires_document_search', False)
                                    })
                                elif isinstance(cat, dict):
                                    categories.append(cat)
                        break
                        
                # If not found in direct values, check the previous step context
                if not categories:
                    # Try to get from the analysis state in the execution context
                    execution = self.active_workflows.get(analysis_id)
                    if execution and hasattr(execution, 'last_state') and execution.last_state:
                        if isinstance(execution.last_state, dict) and 'categories' in execution.last_state:
                            raw_categories = execution.last_state['categories']
                            if raw_categories:
                                for cat in raw_categories:
                                    if hasattr(cat, 'model_dump'):
                                        categories.append(cat.model_dump())
                                    elif hasattr(cat, 'dict'):
                                        categories.append(cat.dict())
                                    elif hasattr(cat, 'name') and hasattr(cat, 'description'):
                                        categories.append({
                                            'name': cat.name,
                                            'description': cat.description,
                                            'requires_document_search': getattr(cat, 'requires_document_search', False)
                                        })
                                    elif isinstance(cat, dict):
                                        categories.append(cat)
            
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
                categories=categories
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
            # Extract final results from workflow state (safely handle non-dict values)
            final_analysis = ""
            deposition_questions = None
            completed_categories = []
            categories = []
            
            if isinstance(final_state, dict):
                final_analysis = final_state.get("final_analysis", "")
                deposition_questions = final_state.get("deposition_questions")
                completed_categories = final_state.get("completed_categories", [])
                categories = final_state.get("categories", [])
            
            # Update analysis with final results
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if analysis_db:
                analysis_db.status = "completed"
                analysis_db.current_step = "completed"
                analysis_db.progress_percentage = 100
                analysis_db.final_analysis = final_analysis
                analysis_db.completed_at = datetime.utcnow()
                analysis_db.categories_completed = len(completed_categories)
                analysis_db.total_categories = len(categories)
                
                if deposition_questions:
                    if hasattr(deposition_questions, 'model_dump'):
                        analysis_db.deposition_questions = deposition_questions.model_dump()
                    elif hasattr(deposition_questions, 'dict'):
                        analysis_db.deposition_questions = deposition_questions.dict()
                    else:
                        analysis_db.deposition_questions = deposition_questions
                
                if completed_categories:
                    analysis_db.completed_categories = [
                        cat.model_dump() if hasattr(cat, 'model_dump') 
                        else cat.dict() if hasattr(cat, 'dict') 
                        else cat
                        for cat in completed_categories
                    ]
                
                db_session.commit()
            
            # Send completion update
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="completed",
                current_step="completed",
                progress_percentage=100,
                categories_completed=len(completed_categories),
                total_categories=len(categories),
                message="Legal analysis completed successfully!"
            )
            
            logger.info(f"Real LangGraph workflow {analysis_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing real workflow {analysis_id}: {e}")
    
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
            
            # Convert categories to dict format (using model_dump instead of deprecated dict())
            categories_dict = []
            for cat in categories:
                if hasattr(cat, 'model_dump'):
                    categories_dict.append(cat.model_dump())
                elif hasattr(cat, 'dict'):  # Fallback for older Pydantic versions
                    categories_dict.append(cat.dict())
                elif isinstance(cat, dict):
                    categories_dict.append(cat)
                else:
                    # Try to extract fields from AnalysisCategory object
                    cat_dict = {
                        "name": getattr(cat, 'name', ''),
                        "description": getattr(cat, 'description', ''),
                        "requires_document_search": getattr(cat, 'requires_document_search', False),
                        "content": getattr(cat, 'content', '')
                    }
                    categories_dict.append(cat_dict)
            
            completed_categories_dict = []
            for cat in completed_categories:
                if hasattr(cat, 'model_dump'):
                    completed_categories_dict.append(cat.model_dump())
                elif hasattr(cat, 'dict'):  # Fallback for older Pydantic versions
                    completed_categories_dict.append(cat.dict())
                elif isinstance(cat, dict):
                    completed_categories_dict.append(cat)
                else:
                    # Try to extract fields from AnalysisCategory object
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
        categories: List[Any] = None
    ) -> None:
        """Send feedback request via WebSocket."""
        try:
            logger.info(f"🔔 Sending feedback request for analysis {analysis_id}")
            logger.info(f"📱 WebSocket manager available: {self.websocket_manager is not None}")
            
            if not self.websocket_manager:
                logger.error(f"❌ No websocket_manager available for analysis {analysis_id}")
                return
            
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                logger.error(f"❌ No active workflow found for analysis {analysis_id}")
                return
            
            logger.info(f"📋 Case ID for broadcast: {execution.case_id}")
            logger.info(f"📦 Categories found: {len(categories) if categories else 0}")
            if categories:
                for i, cat in enumerate(categories):
                    if hasattr(cat, 'name'):
                        logger.info(f"  {i+1}. {cat.name}")
                    else:
                        logger.info(f"  {i+1}. {cat}")
            
            request_data = {
                "type": "feedback_requested",
                "analysis_id": analysis_id,
                "message": message,
                "categories": categories,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📤 Broadcasting feedback request: {request_data}")
            
            connection_count = await self.websocket_manager.broadcast_to_case(
                case_id=execution.case_id,
                message=request_data
            )
            
            logger.info(f"✅ Feedback request sent to {connection_count} WebSocket clients")
            
        except Exception as e:
            logger.error(f"Error sending feedback request for {analysis_id}: {e}")
            import traceback
            logger.error(f"📋 Feedback request error traceback:\n{traceback.format_exc()}")
    
    async def pause_workflow(self, analysis_id: str) -> None:
        """Pause a running workflow."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution or not execution.task:
                raise ValueError(f"No active workflow found for analysis {analysis_id}")
            
            execution.status = "paused"
            logger.info(f"Paused real workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to pause real workflow {analysis_id}: {e}")
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
            
            logger.info(f"Resumed real workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to resume real workflow {analysis_id}: {e}")
            raise
    
    async def stop_workflow(self, analysis_id: str) -> None:
        """Stop a running workflow."""
        try:
            execution = self.active_workflows.get(analysis_id)
            if not execution:
                logger.warning(f"No real workflow found for analysis {analysis_id}")
                return
            
            # Cancel the task
            if execution.task and not execution.task.done():
                execution.task.cancel()
            
            # Signal any waiting interrupt events
            if execution.interrupt_event:
                execution.interrupt_event.set()
            
            # Remove from active workflows
            del self.active_workflows[analysis_id]
            
            logger.info(f"Stopped real workflow for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop real workflow {analysis_id}: {e}")
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
            
            logger.info(f"Provided feedback to real workflow {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to provide feedback to real workflow {analysis_id}: {e}")
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
            
            logger.info(f"Stopped {len(workflows_to_stop)} real workflows for case {case_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop real workflows for case {case_id}: {e}")
            raise