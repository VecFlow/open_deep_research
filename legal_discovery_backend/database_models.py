from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid
import os
from contextlib import contextmanager

Base = declarative_base()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./legal_discovery.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Get database session context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

class CaseDB(Base):
    """Database model for legal cases."""
    __tablename__ = "cases"
    
    id = Column(String(50), primary_key=True, default=lambda: f"case-{uuid.uuid4().hex[:8]}")
    title = Column(String(200), nullable=False)
    description = Column(Text)
    background = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("AnalysisDB", back_populates="case", cascade="all, delete-orphan")
    conversations = relationship("ConversationDB", back_populates="case", cascade="all, delete-orphan")
    comments = relationship("CommentDB", back_populates="case", cascade="all, delete-orphan")

class AnalysisDB(Base):
    """Database model for legal analysis."""
    __tablename__ = "analyses"
    
    id = Column(String(50), primary_key=True, default=lambda: f"analysis-{uuid.uuid4().hex}")
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    status = Column(String(50), default="draft")
    current_step = Column(String(100))
    progress_percentage = Column(Integer, default=0)
    categories_completed = Column(Integer, default=0)
    total_categories = Column(Integer, default=0)
    categories = Column(JSON)
    completed_categories = Column(JSON)
    final_analysis = Column(Text)
    deposition_questions = Column(JSON)
    feedback_requested = Column(Boolean, default=False)
    feedback_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    case = relationship("CaseDB", back_populates="analyses")

class ConversationDB(Base):
    """Database model for chat conversations."""
    __tablename__ = "conversations"
    
    id = Column(String(50), primary_key=True, default=lambda: f"conv-{uuid.uuid4().hex}")
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    analysis_id = Column(String(50), ForeignKey("analyses.id"), nullable=True)
    title = Column(String(200), default="Legal Analysis Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseDB", back_populates="conversations")
    messages = relationship("MessageDB", back_populates="conversation", cascade="all, delete-orphan")

class MessageDB(Base):
    """Database model for chat messages."""
    __tablename__ = "messages"
    
    id = Column(String(50), primary_key=True, default=lambda: f"msg-{uuid.uuid4().hex}")
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False)
    type = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)  # Store additional data like thinking steps, feedback data, etc.
    thinking_steps = Column(JSON)  # Store O1-style thinking steps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("ConversationDB", back_populates="messages")

class CommentDB(Base):
    """Database model for case comments."""
    __tablename__ = "comments"
    
    id = Column(String(50), primary_key=True, default=lambda: f"comment-{uuid.uuid4().hex}")
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), default="User")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("CaseDB", back_populates="comments") 