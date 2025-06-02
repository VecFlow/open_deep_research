"""
Minimal FastAPI server for testing the frontend.
This bypasses all the complex LangGraph dependencies for quick testing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import uuid

app = FastAPI(title="Legal Discovery Backend (Minimal)")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data models
class Case(BaseModel):
    id: str
    title: str
    background: str
    status: str = "draft"
    created_at: str
    updated_at: str
    analyses: List = []
    comments: List = []

class CaseCreate(BaseModel):
    title: str
    background: str

# Mock database
mock_cases = [
    Case(
        id="case-001",
        title="Smith vs. TechCorp Contract Dispute",
        background="This litigation involves a breach of contract claim where plaintiff Smith alleges that defendant TechCorp failed to deliver software services according to the agreed timeline and specifications.",
        status="in_progress",
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-16T14:30:00Z",
        analyses=[{
            "id": "analysis-001",
            "status": "in_progress",
            "categories": [
                {"name": "Contract Analysis", "description": "Review contract terms and obligations"},
                {"name": "Damages Assessment", "description": "Calculate monetary damages and losses"},
                {"name": "Timeline Analysis", "description": "Establish chronology of events"}
            ],
            "category_progress": [
                {"category_name": "Contract Analysis", "status": "completed", "content": "Analysis complete"},
                {"category_name": "Damages Assessment", "status": "in_progress", "content": ""},
                {"category_name": "Timeline Analysis", "status": "pending", "content": ""}
            ],
            "current_step": "analyzing_damages",
            "feedback_requested": False
        }],
        comments=[]
    ),
    Case(
        id="case-002", 
        title="Johnson Employment Discrimination Case",
        background="Employment discrimination case involving allegations of wrongful termination and workplace harassment.",
        status="draft",
        created_at="2024-01-10T09:00:00Z",
        updated_at="2024-01-10T09:00:00Z",
        analyses=[],
        comments=[]
    )
]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "legal-discovery-backend-minimal"}

@app.get("/api/v1/cases")
async def list_cases():
    return mock_cases

@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str):
    case = next((c for c in mock_cases if c.id == case_id), None)
    if not case:
        return {"error": "Case not found"}, 404
    return case

@app.post("/api/v1/cases")
async def create_case(case_data: CaseCreate):
    new_case = Case(
        id=f"case-{str(uuid.uuid4())[:8]}",
        title=case_data.title,
        background=case_data.background,
        created_at=datetime.now().isoformat() + "Z",
        updated_at=datetime.now().isoformat() + "Z"
    )
    mock_cases.append(new_case)
    return new_case

@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str):
    return {
        "message": "Analysis started (mock)",
        "case_id": case_id,
        "status": "in_progress"
    }

@app.get("/api/v1/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    return {
        "id": analysis_id,
        "status": "in_progress",
        "progress": 45.0,
        "current_step": "analyzing_contracts"
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(client_id: str):
    # Mock WebSocket - just for testing
    return {"message": "WebSocket endpoint (mock)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)