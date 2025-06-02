"""
LangGraph service for managing legal discovery workflows.
Handles workflow execution, checkpointing, and state management.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import json
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableConfig

from ..langgraph.legal_discovery import legal_graph
from ..database.models import WorkflowExecution, Analysis, CategoryProgress
from ..schemas.case_schemas import AnalysisStatus, CategoryStatus, WorkflowCommand, WorkflowStatus
from .document_service import document_service

logger = logging.getLogger(__name__)

class LangGraphService:
    """Service for managing LangGraph workflow executions."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.checkpointer = self._setup_checkpointer()
        self.active_workflows: Dict[str, Any] = {}
    
    def _setup_checkpointer(self):
        """Setup checkpointer for workflow persistence."""
        try:
            # Use PostgresSaver for production persistence
            # Fallback to MemorySaver for development
            return MemorySaver()
        except Exception as e:
            logger.warning(f"Failed to setup PostgresSaver, using MemorySaver: {e}")
            return MemorySaver()
    
    async def start_analysis(
        self, 
        case_id: str, 
        analysis_id: str, 
        background_on_case: str,
        config: Dict[str, Any]
    ) -> WorkflowExecution:
        """Start a new legal analysis workflow."""
        try:
            # Create workflow execution record
            execution = WorkflowExecution(
                case_id=UUID(case_id),
                analysis_id=UUID(analysis_id),
                thread_id=f"case_{case_id}_{analysis_id}",
                status="running"
            )
            
            self.db_session.add(execution)
            self.db_session.commit()
            
            # Prepare workflow input
            workflow_input = {
                "background_on_case": background_on_case
            }
            
            # Create runnable config
            runnable_config = RunnableConfig(
                thread_id=execution.thread_id,
                checkpointer=self.checkpointer,
                configurable=config
            )
            
            # Store workflow reference
            self.active_workflows[execution.thread_id] = {
                "execution": execution,
                "config": runnable_config,
                "input": workflow_input
            }
            
            logger.info(f"Started analysis workflow for case {case_id}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to start analysis: {e}")
            raise
    
    async def execute_workflow_step(self, thread_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute workflow and yield real-time updates."""
        if thread_id not in self.active_workflows:
            raise ValueError(f"No active workflow found for thread {thread_id}")
        
        workflow_data = self.active_workflows[thread_id]
        execution = workflow_data["execution"]
        config = workflow_data["config"]
        workflow_input = workflow_data["input"]
        
        try:
            # Stream workflow execution
            async for chunk in legal_graph.astream(
                workflow_input, 
                config=config,
                stream_mode="updates"
            ):
                # Process each workflow update
                update_data = await self._process_workflow_update(execution, chunk)
                if update_data:
                    yield update_data
                    
        except Exception as e:
            logger.error(f"Workflow execution failed for {thread_id}: {e}")
            await self._handle_workflow_error(execution, str(e))
            yield {"type": "error", "message": str(e)}
    
    async def _process_workflow_update(
        self, 
        execution: WorkflowExecution, 
        chunk: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process individual workflow updates and return formatted data."""
        try:
            node_name = chunk.get("node")
            node_output = chunk.get("output", {})
            
            # Update execution state
            execution.current_state = chunk
            execution.checkpoint_id = str(datetime.utcnow().timestamp())
            self.db_session.commit()
            
            # Handle different node types
            if node_name == "generate_analysis_plan":
                return await self._handle_plan_generation(execution, node_output)
            elif node_name == "human_feedback":
                return await self._handle_feedback_request(execution, node_output)
            elif node_name == "analyze_category_with_documents":
                return await self._handle_category_analysis(execution, node_output)
            elif node_name == "generate_deposition_questions":
                return await self._handle_deposition_generation(execution, node_output)
            elif node_name == "compile_final_analysis":
                return await self._handle_analysis_completion(execution, node_output)
            
            # Default update
            return {
                "type": "node_update",
                "node": node_name,
                "data": node_output,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process workflow update: {e}")
            return None
    
    async def _handle_plan_generation(self, execution: WorkflowExecution, output: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analysis plan generation updates."""
        categories = output.get("categories", [])
        
        # Update analysis record
        analysis = self.db_session.query(Analysis).filter(
            Analysis.id == execution.analysis_id
        ).first()
        
        if analysis:
            analysis.categories = [cat.dict() if hasattr(cat, 'dict') else cat for cat in categories]
            analysis.current_step = "plan_generated"
            self.db_session.commit()
        
        return {
            "type": "plan_generated",
            "categories": categories,
            "total_categories": len(categories),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_feedback_request(self, execution: WorkflowExecution, output: Dict[str, Any]) -> Dict[str, Any]:
        """Handle human feedback requests."""
        analysis = self.db_session.query(Analysis).filter(
            Analysis.id == execution.analysis_id
        ).first()
        
        if analysis:
            analysis.feedback_requested = True
            analysis.feedback_message = output.get("message", "Please review the analysis plan")
            analysis.current_step = "awaiting_feedback"
            self.db_session.commit()
        
        return {
            "type": "feedback_requested",
            "message": output.get("message", "Please review the analysis plan"),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_category_analysis(self, execution: WorkflowExecution, output: Dict[str, Any]) -> Dict[str, Any]:
        """Handle category analysis progress updates."""
        completed_categories = output.get("completed_categories", [])
        
        for category in completed_categories:
            # Update category progress
            progress = self.db_session.query(CategoryProgress).filter(
                CategoryProgress.analysis_id == execution.analysis_id,
                CategoryProgress.category_name == category.get("name")
            ).first()
            
            if not progress:
                progress = CategoryProgress(
                    analysis_id=execution.analysis_id,
                    category_name=category.get("name"),
                    status=CategoryStatus.COMPLETED,
                    content=category.get("content", ""),
                    completed_at=datetime.utcnow()
                )
                self.db_session.add(progress)
            else:
                progress.status = CategoryStatus.COMPLETED
                progress.content = category.get("content", "")
                progress.completed_at = datetime.utcnow()
        
        self.db_session.commit()
        
        return {
            "type": "category_completed",
            "categories": completed_categories,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_deposition_generation(self, execution: WorkflowExecution, output: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deposition questions generation."""
        deposition_questions = output.get("deposition_questions")
        
        analysis = self.db_session.query(Analysis).filter(
            Analysis.id == execution.analysis_id
        ).first()
        
        if analysis and deposition_questions:
            analysis.deposition_questions = deposition_questions.dict() if hasattr(deposition_questions, 'dict') else deposition_questions
            analysis.current_step = "deposition_generated"
            self.db_session.commit()
        
        return {
            "type": "deposition_generated",
            "questions": deposition_questions,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_analysis_completion(self, execution: WorkflowExecution, output: Dict[str, Any]) -> Dict[str, Any]:
        """Handle final analysis completion."""
        final_analysis = output.get("final_analysis")
        
        analysis = self.db_session.query(Analysis).filter(
            Analysis.id == execution.analysis_id
        ).first()
        
        if analysis:
            analysis.final_analysis = final_analysis
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.utcnow()
            analysis.current_step = "completed"
            self.db_session.commit()
        
        # Update execution
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        self.db_session.commit()
        
        return {
            "type": "analysis_completed",
            "final_analysis": final_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_workflow_error(self, execution: WorkflowExecution, error_message: str):
        """Handle workflow execution errors."""
        execution.status = "failed"
        execution.error_message = error_message
        self.db_session.commit()
        
        # Update analysis status
        analysis = self.db_session.query(Analysis).filter(
            Analysis.id == execution.analysis_id
        ).first()
        
        if analysis:
            analysis.status = AnalysisStatus.FAILED
            self.db_session.commit()
    
    async def pause_workflow(self, thread_id: str) -> bool:
        """Pause an active workflow."""
        try:
            if thread_id in self.active_workflows:
                execution = self.active_workflows[thread_id]["execution"]
                execution.status = "paused"
                execution.paused_at = datetime.utcnow()
                self.db_session.commit()
                
                logger.info(f"Paused workflow {thread_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause workflow {thread_id}: {e}")
            return False
    
    async def resume_workflow(self, thread_id: str) -> bool:
        """Resume a paused workflow."""
        try:
            if thread_id in self.active_workflows:
                execution = self.active_workflows[thread_id]["execution"]
                execution.status = "running"
                execution.resumed_at = datetime.utcnow()
                self.db_session.commit()
                
                logger.info(f"Resumed workflow {thread_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume workflow {thread_id}: {e}")
            return False
    
    async def provide_feedback(self, thread_id: str, feedback: str, approve: bool = False) -> bool:
        """Provide human feedback to a waiting workflow."""
        try:
            if thread_id not in self.active_workflows:
                return False
            
            workflow_data = self.active_workflows[thread_id]
            config = workflow_data["config"]
            
            # Send feedback to the workflow
            feedback_input = {"feedback": feedback, "approve": approve}
            
            # Continue workflow execution with feedback
            await legal_graph.ainvoke(feedback_input, config=config)
            
            # Update analysis
            execution = workflow_data["execution"]
            analysis = self.db_session.query(Analysis).filter(
                Analysis.id == execution.analysis_id
            ).first()
            
            if analysis:
                analysis.feedback_requested = False
                analysis.feedback_message = None
                self.db_session.commit()
            
            logger.info(f"Provided feedback to workflow {thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to provide feedback to workflow {thread_id}: {e}")
            return False
    
    def get_workflow_status(self, thread_id: str) -> Optional[WorkflowStatus]:
        """Get the current status of a workflow."""
        try:
            if thread_id not in self.active_workflows:
                return None
            
            execution = self.active_workflows[thread_id]["execution"]
            analysis = self.db_session.query(Analysis).filter(
                Analysis.id == execution.analysis_id
            ).first()
            
            if not analysis:
                return None
            
            # Calculate progress
            total_categories = len(analysis.categories or [])
            completed_categories = len(analysis.completed_categories or [])
            progress_percentage = (completed_categories / total_categories * 100) if total_categories > 0 else 0
            
            return WorkflowStatus(
                status=AnalysisStatus(analysis.status),
                current_step=analysis.current_step,
                progress_percentage=progress_percentage,
                feedback_requested=analysis.feedback_requested,
                feedback_message=analysis.feedback_message,
                categories_completed=completed_categories,
                total_categories=total_categories
            )
            
        except Exception as e:
            logger.error(f"Failed to get workflow status for {thread_id}: {e}")
            return None