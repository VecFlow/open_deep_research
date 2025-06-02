#!/usr/bin/env python3
"""
Simple backend without complex dependencies - for testing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="Legal Discovery Backend - Simple")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    case_background: str
    analysis_type: str = "full"

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "legal-discovery-backend-simple"}

@app.get("/api/v1/cases")
async def list_cases():
    return [
        {
            "id": "case-1", 
            "title": "Contract Dispute - TechCorp vs Smith",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]

@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str, request: AnalysisRequest):
    """Start legal analysis workflow"""
    # Simulate analysis workflow steps
    analysis_steps = [
        {"step": "document_review", "status": "in_progress"},
        {"step": "contract_analysis", "status": "pending"},
        {"step": "damages_assessment", "status": "pending"},
        {"step": "timeline_construction", "status": "pending"},
        {"step": "deposition_questions", "status": "pending"}
    ]
    
    return {
        "analysis_id": f"analysis-{case_id}-001",
        "status": "started",
        "steps": analysis_steps,
        "message": "Legal analysis workflow started"
    }

@app.get("/api/v1/analysis/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    return {
        "id": analysis_id,
        "status": "in_progress",
        "progress": 25.0,
        "current_step": "document_review",
        "steps_completed": 1,
        "total_steps": 5
    }

if __name__ == "__main__":
    print("🚀 Starting Simple Legal Discovery Backend...")
    print("   This version doesn't require LangGraph/Weaviate")
    print("   API at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Use different port to avoid conflict