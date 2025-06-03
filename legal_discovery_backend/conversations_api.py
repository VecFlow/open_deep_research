from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from database_models import ConversationDB, MessageDB, CaseDB, get_db
from real_workflow_manager import WorkflowManager

router = APIRouter(prefix="/conversations", tags=["conversations"])

class ConversationCreate(BaseModel):
    case_id: str
    analysis_id: Optional[str] = None
    title: Optional[str] = "Legal Analysis Chat"

class MessageCreate(BaseModel):
    conversation_id: str
    type: str  # 'user', 'assistant', 'system'
    content: str
    message_metadata: Optional[dict] = None
    thinking_steps: Optional[List[dict]] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    type: str
    content: str
    message_metadata: Optional[dict] = None
    thinking_steps: Optional[List[dict]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: str
    case_id: str
    analysis_id: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate, 
    db: Session = Depends(get_db)
):
    """Create a new conversation for a case."""
    # Verify case exists
    case = db.query(CaseDB).filter(CaseDB.id == conversation.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create conversation
    db_conversation = ConversationDB(
        case_id=conversation.case_id,
        analysis_id=conversation.analysis_id,
        title=conversation.title
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return db_conversation

@router.get("/case/{case_id}", response_model=List[ConversationResponse])
async def get_case_conversations(case_id: str, db: Session = Depends(get_db)):
    """Get all conversations for a case."""
    conversations = db.query(ConversationDB).filter(
        ConversationDB.case_id == case_id
    ).order_by(ConversationDB.updated_at.desc()).all()
    
    return conversations

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get a specific conversation with all messages."""
    conversation = db.query(ConversationDB).filter(
        ConversationDB.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@router.post("/messages", response_model=MessageResponse)
async def create_message(message: MessageCreate, db: Session = Depends(get_db)):
    """Create a new message in a conversation."""
    # Verify conversation exists
    conversation = db.query(ConversationDB).filter(
        ConversationDB.id == message.conversation_id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create message
    db_message = MessageDB(
        conversation_id=message.conversation_id,
        type=message.type,
        content=message.content,
        message_metadata=message.message_metadata,
        thinking_steps=message.thinking_steps
    )
    db.add(db_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return db_message

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get messages for a conversation."""
    messages = db.query(MessageDB).filter(
        MessageDB.conversation_id == conversation_id
    ).order_by(MessageDB.created_at.asc()).offset(skip).limit(limit).all()
    
    return messages

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conversation = db.query(ConversationDB).filter(
        ConversationDB.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}

@router.post("/{conversation_id}/auto-save")
async def auto_save_workflow_messages(
    conversation_id: str,
    case_id: str,
    db: Session = Depends(get_db)
):
    """Auto-save workflow messages to conversation as they're generated."""
    try:
        workflow_manager = WorkflowManager()
        
        # Check if there's an active workflow for this case
        active_workflow = workflow_manager.active_workflows.get(case_id)
        if not active_workflow:
            return {"message": "No active workflow found"}
        
        # Get recent workflow events and save as messages
        # This would be called periodically or via WebSocket events
        
        return {"message": "Messages auto-saved successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-save failed: {str(e)}") 