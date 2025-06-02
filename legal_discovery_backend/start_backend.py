#!/usr/bin/env python3
"""
Startup script for Legal Discovery Backend.
This script handles all the necessary initialization and starts the server.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up basic logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are available."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {missing_packages}")
        logger.error("Please install them using: pip install -r requirements.txt")
        return False
    
    return True

def check_langgraph_availability():
    """Check if LangGraph components are available."""
    try:
        # Add the src directory to Python path
        src_path = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(src_path))
        
        from open_deep_research.legal_discovery import legal_graph
        from open_deep_research.legal_state import LegalAnalysisState
        
        logger.info("✅ LangGraph components found and accessible")
        return True
    except ImportError as e:
        logger.warning(f"⚠️  LangGraph components not fully available: {e}")
        logger.warning("Some analysis features may be limited")
        return False

def setup_environment():
    """Set up environment variables with defaults."""
    env_vars = {
        "DATABASE_URL": "sqlite:///./legal_discovery.db",
        "LOG_LEVEL": "INFO",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "UPLOAD_DIRECTORY": "./uploads",
        "MAX_FILE_SIZE": "52428800",  # 50MB
        "WRITER_PROVIDER": "openai",
        "WRITER_MODEL": "gpt-4",
        "PLANNER_PROVIDER": "anthropic", 
        "PLANNER_MODEL": "claude-3-5-sonnet-latest"
    }
    
    # Set defaults for missing environment variables
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            logger.info(f"Set default environment variable: {key}={default_value}")
    
    # Warn about missing API keys
    api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing_keys = [key for key in api_keys if not os.getenv(key)]
    
    if missing_keys:
        logger.warning(f"⚠️  Missing API keys: {missing_keys}")
        logger.warning("Some AI features will not work without these keys")
        logger.warning("Set them as environment variables or in a .env file")

async def main():
    """Main startup function."""
    print("🚀 Starting Legal Discovery Backend...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed. Please install required packages.")
        sys.exit(1)
    
    # Check LangGraph availability
    langgraph_available = check_langgraph_availability()
    
    # Setup environment
    setup_environment()
    
    # Import and configure the application
    try:
        from main import app
        from config import config
        
        print(f"✅ Application configured successfully")
        print(f"📊 Database: {config.database_url}")
        print(f"📁 Upload directory: {config.upload_directory}")
        
        if langgraph_available:
            print("🧠 LangGraph workflow: Available")
        else:
            print("⚠️  LangGraph workflow: Limited (mock mode)")
        
        print(f"🌐 Server will start on: http://{config.host}:{config.port}")
        print(f"📚 API docs will be at: http://{config.host}:{config.port}/docs")
        print(f"❤️  Health check: http://{config.host}:{config.port}/health")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the server
        import uvicorn
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level=config.log_level.value.lower(),
            reload=config.debug,
            access_log=True
        )
        
    except ImportError as e:
        print(f"❌ Failed to import application: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())