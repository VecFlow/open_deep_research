from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

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

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    background = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=AnalysisStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Configuration
    analysis_structure = Column(Text)
    number_of_queries = Column(Integer, default=3)
    max_search_depth = Column(Integer, default=3)
    
    # LangGraph state management
    langgraph_checkpoint = Column(JSON)
    current_node = Column(String(100))
    
    # Relationships
    analyses = relationship("Analysis", back_populates="case", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="case", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    status = Column(String(20), nullable=False, default=AnalysisStatus.DRAFT)
    
    # Analysis data
    categories = Column(JSON)  # List of analysis categories
    completed_categories = Column(JSON, default=list)
    deposition_questions = Column(JSON)
    final_analysis = Column(Text)
    
    # Workflow state
    current_step = Column(String(100))
    feedback_requested = Column(Boolean, default=False)
    feedback_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    case = relationship("Case", back_populates="analyses")
    category_progress = relationship("CategoryProgress", back_populates="analysis", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="analysis", cascade="all, delete-orphan")

class CategoryProgress(Base):
    __tablename__ = "category_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)
    
    category_name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default=CategoryStatus.PENDING)
    content = Column(Text)
    search_iterations = Column(Integer, default=0)
    
    # Document context
    source_documents = Column(JSON, default=list)
    document_queries = Column(JSON, default=list)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="category_progress")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    
    # Context - what the comment relates to
    context_type = Column(String(50))  # "category", "plan", "general", "deposition"
    context_reference = Column(String(200))  # category name, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="comments")
    analysis = relationship("Analysis", back_populates="comments")

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)
    
    # LangGraph execution details
    thread_id = Column(String(100), nullable=False)
    checkpoint_id = Column(String(100))
    current_state = Column(JSON)
    
    # Execution tracking
    started_at = Column(DateTime, default=datetime.utcnow)
    paused_at = Column(DateTime)
    resumed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    status = Column(String(20), nullable=False, default="running")
    error_message = Column(Text)