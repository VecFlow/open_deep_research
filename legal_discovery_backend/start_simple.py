#!/usr/bin/env python3
"""
Simple backend that uses your existing legal_discovery.py directly
"""
import sys
import os
sys.path.append('/Users/thomas/git/vecflow/open_deep_research/src')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your existing legal discovery
from open_deep_research.legal_discovery import LegalResearchWorkflow

app = FastAPI(title="Legal Discovery Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your workflow
workflow = LegalResearchWorkflow()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "legal-discovery-backend"}

@app.get("/api/v1/cases")
async def list_cases():
    return [{"id": "1", "title": "Test Case", "status": "active"}]

@app.post("/api/v1/analysis/{case_id}/start")
async def start_analysis(case_id: str):
    try:
        # Use your actual workflow here
        result = workflow.run({"case_id": case_id})
        return {"status": "started", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Legal Discovery Backend with your existing workflow...")
    uvicorn.run(app, host="0.0.0.0", port=8000)