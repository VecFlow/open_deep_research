#!/usr/bin/env python3
"""
Backend that uses your existing LangGraph legal_discovery workflow
"""
import sys
import os
import asyncio
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

app = FastAPI(title="Legal Discovery Backend - LangGraph")

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
    case_title: str = "Legal Case Analysis"

class Case(BaseModel):
    id: str
    title: str
    background: str
    status: str
    created_at: str
    updated_at: str
    analyses: list = []
    comments: list = []

# Store for cases and analyses
cases_db: Dict[str, Case] = {}
analyses_db: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "legal-discovery-backend-langgraph"}

@app.get("/api/v1/cases")
async def list_cases():
    return list(cases_db.values())

@app.post("/api/v1/cases")
async def create_case(case_data: AnalysisRequest):
    import uuid
    from datetime import datetime
    
    case_id = f"case-{str(uuid.uuid4())[:8]}"
    now = datetime.now().isoformat()
    case = Case(
        id=case_id,
        title=case_data.case_title,
        background=case_data.case_background,
        status="draft",
        created_at=now,
        updated_at=now
    )
    cases_db[case_id] = case
    return case

@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str):
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail="Case not found")
    return cases_db[case_id]

@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str):
    """Start the actual LangGraph legal analysis workflow"""
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail="Case not found")
    
    try:
        # Import your LangGraph workflow
        from open_deep_research.legal_discovery import LegalResearchWorkflow
        from open_deep_research.legal_state import LegalAnalysisInput
        
        # Get case data
        case = cases_db[case_id]
        
        # Create analysis input
        analysis_input = LegalAnalysisInput(
            case_background=case.background,
            case_title=case.title
        )
        
        # Initialize workflow
        workflow = LegalResearchWorkflow()
        
        # Start the analysis (this will run the LangGraph workflow)
        analysis_id = f"analysis-{case_id}-001"
        
        # Store analysis state
        analyses_db[analysis_id] = {
            "id": analysis_id,
            "case_id": case_id,
            "status": "starting",
            "input": analysis_input.dict(),
            "progress": 0.0,
            "current_step": "initializing",
            "workflow": workflow
        }
        
        # Update case status
        cases_db[case_id].status = "analyzing"
        
        # Start workflow in background
        asyncio.create_task(run_workflow_async(analysis_id, workflow, analysis_input))
        
        return {
            "analysis_id": analysis_id,
            "status": "started",
            "message": "LangGraph legal analysis workflow started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

async def run_workflow_async(analysis_id: str, workflow, analysis_input):
    """Run the LangGraph workflow asynchronously"""
    try:
        analyses_db[analysis_id]["status"] = "running"
        analyses_db[analysis_id]["current_step"] = "generate_analysis_plan"
        
        # Run the actual workflow
        result = await workflow.ainvoke(analysis_input.dict())
        
        # Update analysis with results
        analyses_db[analysis_id]["status"] = "completed"
        analyses_db[analysis_id]["result"] = result
        analyses_db[analysis_id]["progress"] = 100.0
        analyses_db[analysis_id]["current_step"] = "completed"
        
    except Exception as e:
        analyses_db[analysis_id]["status"] = "error"
        analyses_db[analysis_id]["error"] = str(e)
        print(f"Workflow error: {e}")

@app.get("/api/v1/analysis/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    if analysis_id not in analyses_db:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analyses_db[analysis_id].copy()
    # Remove the workflow object from the response
    analysis.pop("workflow", None)
    return analysis

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            # Send periodic updates
            await websocket.send_json({
                "type": "status_update",
                "client_id": client_id,
                "message": "Connected to LangGraph backend"
            })
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
    except Exception as e:
        print(f"WebSocket error for {client_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting LangGraph Legal Discovery Backend...")
    print("   Connected to your legal_discovery.py workflow")
    print("   API at: http://localhost:8000")
    print("   Make sure to set your API keys in environment variables")
    uvicorn.run(app, host="0.0.0.0", port=8000)