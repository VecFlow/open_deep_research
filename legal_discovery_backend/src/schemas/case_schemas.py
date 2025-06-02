from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class AnalysisStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class CategoryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Base schemas
class CaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    background: str = Field(..., min_length=10)
    analysis_structure: Optional[str] = None
    number_of_queries: int = Field(default=3, ge=1, le=10)
    max_search_depth: int = Field(default=3, ge=1, le=5)

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    background: Optional[str] = Field(None, min_length=10)
    analysis_structure: Optional[str] = None
    number_of_queries: Optional[int] = Field(None, ge=1, le=10)
    max_search_depth: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[AnalysisStatus] = None

class Case(CaseBase):
    id: str
    status: AnalysisStatus
    created_at: datetime
    updated_at: datetime
    current_node: Optional[str] = None
    
    class Config:
        from_attributes = True

# Analysis schemas
class AnalysisCategory(BaseModel):
    name: str
    description: str
    requires_document_search: bool
    content: str = ""

class CategoryProgressBase(BaseModel):
    category_name: str
    status: CategoryStatus
    content: Optional[str] = None
    search_iterations: int = 0

class CategoryProgress(CategoryProgressBase):
    id: str
    analysis_id: str
    source_documents: List[Dict[str, Any]] = []
    document_queries: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AnalysisBase(BaseModel):
    status: AnalysisStatus = AnalysisStatus.DRAFT

class AnalysisCreate(AnalysisBase):
    case_id: str

class Analysis(AnalysisBase):
    id: str
    case_id: str
    categories: Optional[List[AnalysisCategory]] = []
    completed_categories: List[AnalysisCategory] = []
    deposition_questions: Optional[Dict[str, Any]] = None
    final_analysis: Optional[str] = None
    current_step: Optional[str] = None
    feedback_requested: bool = False
    feedback_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    category_progress: List[CategoryProgress] = []
    
    class Config:
        from_attributes = True

# Comment schemas
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)
    context_type: Optional[str] = None
    context_reference: Optional[str] = None

class CommentCreate(CommentBase):
    case_id: str
    analysis_id: Optional[str] = None

class Comment(CommentBase):
    id: str
    case_id: str
    analysis_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Workflow control schemas
class WorkflowCommand(BaseModel):
    action: str  # "start", "pause", "resume", "stop"
    feedback: Optional[str] = None
    approve_plan: Optional[bool] = None

class WorkflowStatus(BaseModel):
    status: AnalysisStatus
    current_step: Optional[str] = None
    progress_percentage: float = 0.0
    feedback_requested: bool = False
    feedback_message: Optional[str] = None
    categories_completed: int = 0
    total_categories: int = 0

# Response schemas
class CaseWithAnalysis(Case):
    analyses: List[Analysis] = []
    comments: List[Comment] = []

class AnalysisProgress(BaseModel):
    analysis: Analysis
    workflow_status: WorkflowStatus
    real_time_updates: bool = True