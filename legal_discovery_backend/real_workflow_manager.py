"""
Real Workflow Manager for Legal Discovery Backend.
Handles actual LangGraph workflow execution with your legal_discovery.py.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_
import traceback
import json

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
from langgraph.types import Command
from database_models import CaseDB, AnalysisDB, ConversationDB, MessageDB, get_db, init_database
from langchain_core.runnables import RunnableConfig
from langgraph.pregel import Pregel
from langgraph.errors import GraphInterrupt

try:
    from .models import AnalysisDB, AnalysisCategory as AnalysisCategoryModel, WebSocketMessage
    from .websocket_manager import WebSocketManager
    from .database import get_db_session
except ImportError:
    from models import AnalysisDB, AnalysisCategory as AnalysisCategoryModel, WebSocketMessage
    from websocket_manager import WebSocketManager
    from database import get_db_session

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
    waiting_for_feedback: bool = False

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
    
    def _get_db_session(self):
        """Get a database session."""
        return get_db_session()
    
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
            workflow_interrupted = False
            
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
                    
                    # Store that we're waiting for feedback
                    execution.interrupt_event = asyncio.Event()
                    execution.waiting_for_feedback = True
                    workflow_interrupted = True
                    logger.info(f"Workflow {analysis_id} paused for human feedback - stopping current stream")
                    
                    # Stop the current stream - we'll resume with a new one when feedback arrives
                    break
                
                final_state = chunk
            
            # Only complete workflow if it wasn't interrupted (i.e., it finished naturally)
            if not workflow_interrupted and final_state:
                logger.info(f"🏁 Workflow {analysis_id} completed naturally - calling completion")
                await self._complete_workflow(analysis_id, final_state, db_session)
            elif workflow_interrupted:
                logger.info(f"🔄 Workflow {analysis_id} interrupted and waiting for feedback - NOT completing")
            else:
                logger.warning(f"⚠️  Workflow {analysis_id} ended without final state or interrupt")
            
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
            # Only clean up if workflow completed or failed, not if waiting for feedback
            execution = self.active_workflows.get(analysis_id)
            if execution and not execution.waiting_for_feedback:
                # Clean up completed or failed workflows
                if analysis_id in self.active_workflows:
                    del self.active_workflows[analysis_id]
                    logger.info(f"🧹 Cleaned up completed/failed workflow {analysis_id}")
            elif execution and execution.waiting_for_feedback:
                logger.info(f"🔄 Keeping workflow {analysis_id} active - waiting for feedback")
    
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
                message=f"{current_node.replace('_', ' ').title()}"
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
            logger.info(f"🏁 Completing workflow {analysis_id}")
            logger.info(f"📊 Final state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}")
            
            # Debug: log the full final state structure
            if isinstance(final_state, dict):
                for key, value in final_state.items():
                    logger.info(f"🔍 Final state[{key}]: {type(value)} - {str(value)[:200]}...")
            
            # Extract final results from workflow state (safely handle non-dict values)
            final_analysis = ""
            deposition_questions = None
            completed_categories = []
            categories = []
            
            if isinstance(final_state, dict):
                # Try to get the final analysis content
                if 'compile_final_analysis' in final_state:
                    final_content = final_state['compile_final_analysis']
                    if isinstance(final_content, dict):
                        final_analysis = final_content.get("final_analysis", "")
                        deposition_questions = final_content.get("deposition_questions")
                        # Try to get categories from final content
                        completed_categories = final_content.get("completed_categories", [])
                        categories = final_content.get("categories", [])
                        
                        # If not found in final content, try to extract from the analysis text
                        if not categories and not completed_categories:
                            # Get from execution context if available
                            execution = self.active_workflows.get(analysis_id)
                            if execution and execution.last_state:
                                if isinstance(execution.last_state, dict):
                                    categories = execution.last_state.get("categories", [])
                                    completed_categories = categories  # Assume all completed since we reached final analysis
                elif 'final_analysis' in final_state:
                    final_analysis = final_state.get("final_analysis", "")
                    deposition_questions = final_state.get("deposition_questions")
                    completed_categories = final_state.get("completed_categories", [])
                    categories = final_state.get("categories", [])
                else:
                    # Try to extract from any available data
                    final_analysis = final_state.get("final_analysis", "")
                    deposition_questions = final_state.get("deposition_questions")
                    completed_categories = final_state.get("completed_categories", [])
                    categories = final_state.get("categories", [])
                
                # If still no categories found, get from execution state (since workflow completed all categories)
                if not completed_categories and not categories:
                    execution = self.active_workflows.get(analysis_id)
                    if execution and execution.last_state:
                        if isinstance(execution.last_state, dict):
                            categories = execution.last_state.get("categories", [])
                            # Since workflow completed successfully, all categories are completed
                            completed_categories = categories
                            logger.info(f"🔄 Retrieved {len(categories)} categories from execution state")
                
                # If we have final analysis but no categories, try to get from database
                if final_analysis and not categories:
                    try:
                        analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
                        if analysis_db and analysis_db.categories:
                            categories = analysis_db.categories
                            # Since we completed successfully, mark all as completed
                            completed_categories = categories
                            logger.info(f"🔄 Retrieved {len(categories)} categories from database")
                    except Exception as e:
                        logger.warning(f"Could not retrieve categories from database: {e}")
            
            logger.info(f"📋 Final analysis length: {len(final_analysis) if final_analysis else 0}")
            logger.info(f"📂 Completed categories: {len(completed_categories)}")
            logger.info(f"📁 Total categories: {len(categories)}")
            
            # Convert categories to serializable format
            completed_categories_dict = []
            for cat in completed_categories:
                if hasattr(cat, 'model_dump'):
                    completed_categories_dict.append(cat.model_dump())
                elif hasattr(cat, 'dict'):
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
            
            categories_dict = []
            for cat in categories:
                if hasattr(cat, 'model_dump'):
                    categories_dict.append(cat.model_dump())
                elif hasattr(cat, 'dict'):
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

            # Update analysis with final results
            analysis_db = db_session.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if analysis_db:
                analysis_db.status = "completed"
                analysis_db.current_step = "completed"
                analysis_db.progress_percentage = 100
                analysis_db.final_analysis = final_analysis
                analysis_db.completed_at = datetime.utcnow()
                analysis_db.categories_completed = len(completed_categories_dict)
                analysis_db.total_categories = len(categories_dict)
                analysis_db.categories = categories_dict
                analysis_db.completed_categories = completed_categories_dict
                
                if deposition_questions:
                    if hasattr(deposition_questions, 'model_dump'):
                        analysis_db.deposition_questions = deposition_questions.model_dump()
                    elif hasattr(deposition_questions, 'dict'):
                        analysis_db.deposition_questions = deposition_questions.dict()
                    else:
                        analysis_db.deposition_questions = deposition_questions
                
                db_session.commit()
                logger.info(f"💾 Updated database with final results for {analysis_id}")
            
            # Send completion update with results
            await self._send_progress_update(
                analysis_id=analysis_id,
                status="completed",
                current_step="completed",
                progress_percentage=100,
                categories_completed=len(completed_categories_dict),
                total_categories=len(categories_dict),
                message="Legal analysis completed successfully!"
            )
            
            # Send detailed completion update with categories
            await self._send_analysis_completion(
                analysis_id=analysis_id,
                final_analysis=final_analysis,
                completed_categories=completed_categories_dict,
                deposition_questions=deposition_questions
            )
            
            logger.info(f"✅ Real LangGraph workflow {analysis_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing real workflow {analysis_id}: {e}")
            import traceback
            logger.error(f"📋 Completion error traceback:\n{traceback.format_exc()}")
    
    async def _send_analysis_completion(
        self, 
        analysis_id: str, 
        final_analysis: str,
        completed_categories: List[Dict[str, Any]],
        deposition_questions: Optional[Any] = None
    ) -> None:
        """Send analysis completion via WebSocket and save to conversation."""
        try:
            completion_data = {
                "type": "analysis_completed",
                "analysis_id": analysis_id,
                "final_analysis": final_analysis,
                "completed_categories": completed_categories,
                "deposition_questions": deposition_questions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get case_id for broadcasting (frontend subscribes to case_id, not analysis_id)
            execution = self.active_workflows.get(analysis_id)
            case_id = execution.case_id if execution else analysis_id
            
            # Send via WebSocket (pass raw data, not WebSocketMessage object)
            await self.websocket_manager.broadcast_to_case(case_id, completion_data)
            
            # Create rich content for assistant message
            categories_count = len(completed_categories)
            content = f"# Legal Analysis Complete\n\n**Categories Analyzed:** {categories_count}\n\n## Analysis Results\n\n{final_analysis}"
            
            if deposition_questions:
                if isinstance(deposition_questions, str):
                    content += f"\n\n## Deposition Questions\n\n{deposition_questions}"
                else:
                    content += f"\n\n## Deposition Questions\n\n```json\n{json.dumps(deposition_questions, indent=2)}\n```"
            
            # Save to conversation as assistant message
            await self._save_assistant_message(analysis_id, content, metadata=completion_data)
            
        except Exception as e:
            logger.error(f"Failed to send analysis completion: {e}")
    
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
        """Send progress update via WebSocket and save to conversation."""
        try:
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
            
            # Get case_id for broadcasting (frontend subscribes to case_id, not analysis_id)
            execution = self.active_workflows.get(analysis_id)
            case_id = execution.case_id if execution else analysis_id
            
            # Send via WebSocket (pass raw data, not WebSocketMessage object)
            await self.websocket_manager.broadcast_to_case(case_id, update_data)
            
            # Save to conversation if message exists
            if message:
                await self._save_system_message(analysis_id, message, update_data)
            
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")

    async def _save_system_message(self, analysis_id: str, content: str, metadata: Dict[str, Any] = None):
        """Save a system message to the conversation."""
        try:
            # Get database session
            with get_db() as db:
                # Get or create conversation for this analysis
                conversation = await self._get_or_create_conversation(db, analysis_id)
                
                # Create system message
                message = MessageDB(
                    conversation_id=conversation.id,
                    type="system",
                    content=content,
                    message_metadata=metadata,
                    created_at=datetime.utcnow()
                )
                
                db.add(message)
                
                # Update conversation timestamp
                conversation.updated_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save system message: {e}")

    async def _save_assistant_message(self, analysis_id: str, content: str, thinking_steps: List[Dict] = None, metadata: Dict[str, Any] = None):
        """Save an assistant message with optional thinking steps."""
        try:
            # Get database session
            with get_db() as db:
                # Get or create conversation for this analysis
                conversation = await self._get_or_create_conversation(db, analysis_id)
                
                # Create assistant message
                message = MessageDB(
                    conversation_id=conversation.id,
                    type="assistant",
                    content=content,
                    message_metadata=metadata,
                    thinking_steps=thinking_steps,
                    created_at=datetime.utcnow()
                )
                
                db.add(message)
                
                # Update conversation timestamp
                conversation.updated_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")

    async def _get_or_create_conversation(self, db: Session, analysis_id: str) -> ConversationDB:
        """Get existing conversation or create new one for analysis."""
        try:
            # Get analysis to find case_id
            analysis = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
            if not analysis:
                raise ValueError(f"Analysis {analysis_id} not found")
            
            # Look for existing conversation
            conversation = db.query(ConversationDB).filter(
                and_(
                    ConversationDB.case_id == analysis.case_id,
                    ConversationDB.analysis_id == analysis_id
                )
            ).first()
            
            if not conversation:
                # Create new conversation
                conversation = ConversationDB(
                    case_id=analysis.case_id,
                    analysis_id=analysis_id,
                    title=f"Legal Analysis - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get/create conversation: {e}")
            raise
    
    async def _send_feedback_request(
        self, 
        analysis_id: str, 
        message: str, 
        categories: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Send feedback request via WebSocket and save to conversation."""
        try:
            feedback_data = {
                "type": "feedback_requested",
                "analysis_id": analysis_id,
                "message": message,
                "categories": categories or [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get case_id for broadcasting (frontend subscribes to case_id, not analysis_id)
            execution = self.active_workflows.get(analysis_id)
            case_id = execution.case_id if execution else analysis_id
            
            logger.info(f"🔔 Sending feedback request for analysis {analysis_id} to case {case_id}")
            logger.info(f"📱 Feedback data: {feedback_data}")
            
            # Send via WebSocket (pass raw data, not WebSocketMessage object)
            connection_count = await self.websocket_manager.broadcast_to_case(case_id, feedback_data)
            
            logger.info(f"✅ Feedback request sent to {connection_count} WebSocket clients for case {case_id}")
            
            # Save to conversation
            await self._save_system_message(analysis_id, message, feedback_data)
            
        except Exception as e:
            logger.error(f"Failed to send feedback request: {e}")
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
            
            if not execution.waiting_for_feedback:
                raise ValueError(f"Workflow {analysis_id} is not waiting for feedback")
            
            logger.info(f"📝 Providing feedback to workflow {analysis_id}: feedback='{feedback}', approve={approve}")
            
            # Use database context manager for proper session handling
            try:
                from .database import get_db
            except ImportError:
                from database import get_db
            
            with get_db() as db_session:
                # Prepare the feedback value for LangGraph
                if approve:
                    feedback_value = True  # Boolean True for approval
                else:
                    feedback_value = feedback  # String for modification
                    
                logger.info(f"🎯 Resuming workflow with feedback_value: {feedback_value} (type: {type(feedback_value)})")
                
                # Resume the workflow using the correct LangGraph pattern
                compiled_graph = builder.compile(checkpointer=execution.checkpointer)
                
                # Start a new stream with Command(resume=feedback_value) to continue the workflow
                final_resume_state = None
                resume_step_count = 0
                resumed_workflow_completed = False
                
                async for chunk in compiled_graph.astream(
                    Command(resume=feedback_value),
                    config={
                        **execution.config,
                        "configurable": {
                            **execution.config["configurable"],
                            "thread_id": execution.thread_id
                        }
                    }
                ):
                    resume_step_count += 1
                    logger.info(f"📊 LangGraph Resume Step {resume_step_count}: {list(chunk.keys()) if isinstance(chunk, dict) else chunk}")
                    if chunk:
                        logger.info(f"🔍 Resume chunk content: {chunk}")
                    
                    # Handle the resumed workflow updates
                    await self._handle_workflow_chunk(analysis_id, chunk, db_session)
                    
                    # Check for another interrupt (shouldn't happen for approval)
                    if isinstance(chunk, dict) and "__interrupt__" in chunk:
                        logger.warning(f"⚠️  Unexpected interrupt in resumed workflow for {analysis_id}")
                        # Could handle nested interrupts here if needed
                    
                    final_resume_state = chunk
                
                # Workflow completed after resume
                if final_resume_state:
                    logger.info(f"🏁 Resumed workflow {analysis_id} completed - calling completion")
                    await self._complete_workflow(analysis_id, final_resume_state, db_session)
                    resumed_workflow_completed = True
                    
                    # Remove from active workflows since it's completed
                    if analysis_id in self.active_workflows:
                        del self.active_workflows[analysis_id]
                
                # Clear the feedback waiting state
                execution.waiting_for_feedback = False
                execution.feedback_data = None
                
                if resumed_workflow_completed:
                    logger.info(f"✅ Successfully completed workflow {analysis_id} after feedback")
                else:
                    logger.warning(f"⚠️  Workflow {analysis_id} resumed but didn't complete properly")
            
        except Exception as e:
            logger.error(f"Failed to provide feedback to real workflow {analysis_id}: {e}")
            import traceback
            logger.error(f"📋 Feedback error traceback:\n{traceback.format_exc()}")
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