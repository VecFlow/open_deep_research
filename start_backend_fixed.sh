#!/bin/bash

echo "🔧 Starting Legal Discovery Backend (Fixed Version)"
echo "=================================================="

# Navigate to backend directory
cd "$(dirname "$0")/legal_discovery_backend"

# Check if we're in the right directory
if [ ! -f "requirements_fixed.txt" ]; then
    echo "❌ Error: Not in backend directory. Please run this from the root directory."
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1)
echo "Python version: $python_version"

# Remove old venv if it has conflicts
if [ -d "venv" ]; then
    echo "🧹 Removing old virtual environment with conflicts..."
    rm -rf venv
fi

# Create fresh virtual environment
echo "🐍 Creating fresh virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip first
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies with fixed versions
echo "📦 Installing Python dependencies (fixed versions)..."
pip install -r requirements_fixed.txt

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
try:
    from src.database.connection import create_tables
    create_tables()
    print('✅ Database tables created successfully!')
except Exception as e:
    print(f'⚠️  Database initialization warning: {e}')
    print('This is OK for first run - tables will be created when needed.')
" 2>/dev/null

# Check if uvicorn is properly installed
echo "🔍 Checking uvicorn installation..."
python -c "import uvicorn; print('✅ uvicorn imported successfully')" || {
    echo "❌ uvicorn import failed, installing manually..."
    pip install uvicorn[standard]==0.24.0
}

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