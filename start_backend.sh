#!/bin/bash

echo "🔧 Starting Legal Discovery Backend"
echo "==================================="

# Navigate to backend directory
cd "$(dirname "$0")/legal_discovery_backend"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Not in backend directory. Please run this from the root directory."
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1)
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create environment file
echo "⚙️  Setting up environment..."
cat > .env << EOF
# Database (SQLite for development)
DATABASE_URL=sqlite:///./legal_discovery.db

# Weaviate (Optional - for document search)
WEAVIATE_URL=http://localhost:8080
WEAVIATE_COLLECTION_NAME=Documents

# AI Models (Add your API keys)
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here

# Model Configuration
WRITER_PROVIDER=openai
WRITER_MODEL=gpt-4
PLANNER_PROVIDER=anthropic
PLANNER_MODEL=claude-3-5-sonnet-latest
EOF

# Initialize database
echo "🗄️  Initializing database..."
python -c "
from src.database.connection import create_tables
create_tables()
print('✅ Database tables created successfully!')
" 2>/dev/null || echo "⚠️  Database initialization failed (this is OK for first run)"

# Start the server
echo "🚀 Starting backend server..."
echo "   API available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo "   Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start with auto-reload for development
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000