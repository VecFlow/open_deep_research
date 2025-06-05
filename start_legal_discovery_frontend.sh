#!/bin/bash

# Navigate to frontend directory
cd "$(dirname "$0")/legal_discovery_frontend"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in frontend directory. Please run this from the root directory."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check Node.js version
echo "📋 Checking Node.js version..."
node_version=$(node --version)
echo "Node.js version: $node_version"

# Install pnpm if not available
if ! command -v pnpm &> /dev/null; then
    echo "📦 Installing pnpm..."
    npm install -g pnpm
fi

# Install dependencies
echo "📦 Installing dependencies with pnpm..."
pnpm install

# Create .env.local file for development
echo "⚙️  Setting up environment..."
cat > .env.local << EOF
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

# Start the development server
echo "🚀 Starting development server..."
echo "   Frontend available at: http://localhost:3000"
echo "   Make sure the backend is running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Next.js development server
pnpm dev 