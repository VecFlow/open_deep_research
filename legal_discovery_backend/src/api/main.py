"""
FastAPI application for Legal Discovery Backend.
Provides REST APIs and WebSocket support for the legal analysis workflow.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from .routes import cases, analysis, documents
from ..database.models import Base
from ..services.document_service import document_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Legal Discovery Backend")
    
    # Test document service connection
    health = await document_service.health_check()
    if health["status"] == "healthy":
        logger.info("Document service connection established")
    else:
        logger.warning(f"Document service connection issues: {health}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Discovery Backend")

# Create FastAPI application
app = FastAPI(
    title="Legal Discovery Backend",
    description="Backend API for Legal Discovery Analysis System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Include routers
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.send_personal_message({"type": "pong"}, client_id)
            elif message_type == "subscribe":
                # Subscribe to specific case/analysis updates
                case_id = data.get("case_id")
                if case_id:
                    logger.info(f"Client {client_id} subscribed to case {case_id}")
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "case_id": case_id
                    }, client_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "legal-discovery-backend"}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including dependencies."""
    doc_health = await document_service.health_check()
    
    return {
        "status": "healthy",
        "service": "legal-discovery-backend",
        "dependencies": {
            "document_service": doc_health
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Legal Discovery Backend API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )