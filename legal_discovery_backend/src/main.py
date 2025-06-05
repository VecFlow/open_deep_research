import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Add the parent directory to Python path to import the legal discovery module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from open_deep_research.legal_discovery_new import run_intelligent_deposition_agent
from open_deep_research.configuration import Configuration
from stream_agent import stream_agent_execution

# Load environment variables from root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class CaseBackgroundRequest(BaseModel):
    case_background: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("🚀 Legal Discovery Backend Starting...")
    print("   Environment variables loaded from .env")
    print("   Agent ready for legal discovery tasks")
    yield
    print("👋 Legal Discovery Backend Shutting Down...")

app = FastAPI(
    title="Legal Discovery Backend",
    description="Backend API for running legal discovery agents with real-time streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # Added port 3001
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "legal-discovery-backend"}

@app.post("/api/v1/legal-discovery/stream")
async def stream_legal_discovery(request: CaseBackgroundRequest):
    """
    Stream the legal discovery agent execution using Server-Sent Events.
    Real-time capture of agent progress, insights, and decisions.
    """
    try:
        # Create a basic config - the agent will use environment variables
        config = {"configurable": {}}
        
        # Stream the agent execution with real-time output capture
        return StreamingResponse(
            stream_agent_execution(
                case_background=request.case_background,
                agent_function=run_intelligent_deposition_agent,
                config=config
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        print(f"❌ Error starting stream: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start streaming: {str(e)}")

# Alternative non-streaming endpoint for testing
@app.post("/api/v1/legal-discovery/run")
async def run_legal_discovery(request: CaseBackgroundRequest):
    """
    Run the legal discovery agent and return results (non-streaming).
    """
    try:
        config = {"configurable": {}}
        
        result = await run_intelligent_deposition_agent(
            case_background=request.case_background,
            config=config
        )
        
        if result and len(result) > 0:
            return {
                "success": True,
                "data": {
                    "questions": result[0].get('questions', []),
                    "basis": result[0].get('basis', ''),
                    "confidence_level": result[0].get('confidence_level', 0),
                    "evidence_sources": result[0].get('evidence_sources', 0)
                }
            }
        else:
            raise HTTPException(status_code=500, detail="No results generated")
            
    except Exception as e:
        print(f"❌ Error running legal discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 