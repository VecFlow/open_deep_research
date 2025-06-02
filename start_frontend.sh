#!/bin/bash

echo "🚀 Starting Legal Discovery Frontend"
echo "======================================"

# Navigate to frontend directory
cd "$(dirname "$0")/legal_discovery_frontend"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in frontend directory. Please run this from the root directory."
    exit 1
fi

# Check Node.js version
echo "📋 Checking Node.js version..."
node_version=$(node --version)
echo "Node.js version: $node_version"

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "❌ pnpm not found. Installing..."
    npm install -g pnpm
fi

echo "📦 pnpm version: $(pnpm --version)"

# Clean up any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "next dev" 2>/dev/null || true
sleep 2

# Check for port conflicts
echo "🔍 Checking port availability..."
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 3000 is busy. Will use port 3001"
    PORT=3001
else
    echo "✅ Port 3000 is available"
    PORT=3000
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    pnpm install
fi

# Create environment file
echo "⚙️  Setting up environment..."
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
EOF

# Start the development server
echo "🚀 Starting development server on port $PORT..."
echo "   Access your app at: http://localhost:$PORT"
echo "   Test page at: http://localhost:$PORT/test"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start with explicit host binding
pnpm dev -p $PORT -H 0.0.0.0