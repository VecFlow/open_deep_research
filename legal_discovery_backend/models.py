"""
Data models for the Legal Discovery Backend.
These models define the database schema and API data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

# SQLAlchemy Models (Database Schema)
Base = declarative_base()

class CaseDB(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    background = Column(Text, nullable=False)
    status = Column(String, default="draft")
    analysis_structure = Column(Text, nullable=True)
    number_of_queries = Column(Integer, default=5)
    max_search_depth = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("AnalysisDB", back_populates="case", cascade="all, delete-orphan")
    comments = relationship("CommentDB", back_populates="case", cascade="all, delete-orphan")

class AnalysisDB(Base):
    __tablename__ = "analyses"
    
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    status = Column(String, default="pending")
    current_step = Column(String, nullable=True)
    progress_percentage = Column(Integer, default=0)
    categories_completed = Column(Integer, default=0)
    total_categories = Column(Integer, default=0)
    feedback_requested = Column(Boolean, default=False)
    feedback_message = Column(Text, nullable=True)
    
    # Analysis data (stored as JSON)
    categories = Column(JSON, default=list)
    completed_categories = Column(JSON, default=list)
    category_progress = Column(JSON, default=list)
    deposition_questions = Column(JSON, nullable=True)
    final_analysis = Column(Text, nullable=True)
    
    # Workflow state management
    workflow_state = Column(JSON, nullable=True)
    checkpoint_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    case = relationship("CaseDB", back_populates="analyses")
    comments = relationship("CommentDB", back_populates="analysis", cascade="all, delete-orphan")

class CommentDB(Base):
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=True)
    content = Column(Text, nullable=False)
    context_type = Column(String, nullable=True)  # "category", "step", "general"
    context_reference = Column(String, nullable=True)  # category name, step name, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseDB", back_populates="comments")
    analysis = relationship("AnalysisDB", back_populates="comments")

class DocumentDB(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)
    weaviate_id = Column(String, nullable=True)  # Reference to Weaviate document
    uploaded_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models (API Data Structures)

class AnalysisCategory(BaseModel):
    name: str
    description: str
    requires_document_search: bool
    content: str = ""

class CategoryProgress(BaseModel):
    id: str
    analysis_id: str
    category_name: str
    status: str  # "pending", "in_progress", "completed", "failed"
    content: Optional[str] = None
    search_iterations: int = 0
    source_documents: List[Dict[str, Any]] = []
    document_queries: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

class Comment(BaseModel):
    id: str
    case_id: str
    analysis_id: Optional[str] = None
    content: str
    context_type: Optional[str] = None
    context_reference: Optional[str] = None
    created_at: datetime

class Analysis(BaseModel):
    id: str
    case_id: str
    status: str
    current_step: Optional[str] = None
    progress_percentage: int = 0
    categories_completed: int = 0
    total_categories: int = 0
    feedback_requested: bool = False
    feedback_message: Optional[str] = None
    
    categories: List[AnalysisCategory] = []
    completed_categories: List[AnalysisCategory] = []
    category_progress: List[CategoryProgress] = []
    deposition_questions: Optional[Dict[str, Any]] = None
    final_analysis: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

class Case(BaseModel):
    id: str
    title: str
    background: str
    status: str
    analysis_structure: Optional[str] = None
    number_of_queries: int = 5
    max_search_depth: int = 3
    created_at: datetime
    updated_at: datetime
    analyses: List[Analysis] = []
    comments: List[Comment] = []

class Document(BaseModel):
    id: str
    case_id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    weaviate_id: Optional[str] = None
    uploaded_at: datetime

# Request/Response Models

class CaseCreateRequest(BaseModel):
    case_title: str = Field(..., min_length=1, max_length=500)
    case_background: str = Field(..., min_length=10)
    analysis_structure: Optional[str] = None
    number_of_queries: Optional[int] = Field(default=5, ge=1, le=20)
    max_search_depth: Optional[int] = Field(default=3, ge=1, le=10)

class CaseUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    background: Optional[str] = Field(None, min_length=10)
    status: Optional[str] = None
    analysis_structure: Optional[str] = None
    number_of_queries: Optional[int] = Field(None, ge=1, le=20)
    max_search_depth: Optional[int] = Field(None, ge=1, le=10)

class WorkflowControlRequest(BaseModel):
    action: str = Field(..., pattern="^(start|pause|resume|stop|feedback)$")
    feedback: Optional[str] = None
    approve: Optional[bool] = None

class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    context_type: Optional[str] = None
    context_reference: Optional[str] = None

class WorkflowStatus(BaseModel):
    status: str
    current_step: Optional[str] = None
    progress_percentage: int = 0
    feedback_requested: bool = False
    feedback_message: Optional[str] = None
    categories_completed: int = 0
    total_categories: int = 0
    error_message: Optional[str] = None

# WebSocket Message Types

class WebSocketMessage(BaseModel):
    type: str
    client_id: str
    data: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProgressUpdate(BaseModel):
    analysis_id: str
    status: str
    current_step: Optional[str] = None
    progress_percentage: int = 0
    categories_completed: int = 0
    total_categories: int = 0
    message: Optional[str] = None

class FeedbackRequest(BaseModel):
    analysis_id: str
    message: str
    context: Dict[str, Any] = {}