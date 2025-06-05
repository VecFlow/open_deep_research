# Legal Discovery Agent - FastAPI + Next.js

AI-powered legal discovery and deposition preparation tool with real-time streaming interface.

## Overview

This system consists of:
- **FastAPI Backend**: Runs the legal discovery agent with real-time SSE streaming
- **Next.js 15 Frontend**: Modern React interface with live progress display
- **LangChain Agent**: Intelligent legal discovery analysis (`legal_discovery_new.py`)

## Architecture

```
┌─────────────────┐    HTTP/SSE    ┌──────────────────┐    Python    ┌─────────────────┐
│   Next.js 15   │ ────────────► │   FastAPI        │ ──────────► │  LangChain      │
│   Frontend      │               │   Backend        │              │  Agent          │
│   (Port 3000)   │               │   (Port 8000)    │              │  (legal_disc... │
└─────────────────┘               └──────────────────┘              └─────────────────┘
```

## Features

- 🚀 **Real-time streaming**: Watch the AI agent work in real-time
- 🧠 **Intelligent analysis**: Advanced legal discovery using LangChain agents
- 💡 **Smart insights**: Real-time display of discoveries, insights, and decisions
- 🎯 **Strategic questions**: Generate targeted deposition questions
- 📊 **Progress tracking**: Visual feedback on agent execution
- 🔄 **Server-Sent Events**: Efficient real-time data streaming

## Quick Start

### Prerequisites

- Python 3.8+ with pip
- Node.js 18+ with pnpm
- Environment variables in `.env` file (API keys for OpenAI, Anthropic, etc.)

### Option 1: Use the startup scripts (Recommended)

1. **Start the Backend**:
   ```bash
   ./start_legal_discovery_backend.sh
   ```

2. **Start the Frontend** (in a new terminal):
   ```bash
   ./start_legal_discovery_frontend.sh
   ```

3. **Open your browser**: http://localhost:3000

### Option 2: Manual setup

#### Backend Setup

```bash
cd legal_discovery_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
cd src && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd legal_discovery_frontend

# Install dependencies
pnpm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
pnpm dev
```

## Usage

1. **Enter Case Background**: Provide details about your legal case, including facts, parties, potential issues, and relevant context.

2. **Start Analysis**: Click "Start Discovery Analysis" to begin the AI agent execution.

3. **Watch Real-time Progress**: The interface will show:
   - 🚀 Agent startup and initialization
   - 🔍 Document searches and evidence gathering
   - 🧠 Insights and analysis
   - 💡 Key discoveries
   - 📊 Research progress updates
   - 🤔 AI decision-making process
   - 🎯 Final strategy compilation

4. **Review Results**: Once complete, you'll see:
   - Strategic deposition questions
   - Confidence metrics
   - Analysis basis
   - Evidence sources used

## API Endpoints

### Backend (Port 8000)

- `GET /health` - Health check
- `POST /api/v1/legal-discovery/stream` - Stream agent execution (SSE)
- `POST /api/v1/legal-discovery/run` - Run agent (non-streaming)
- `GET /docs` - API documentation

### Frontend (Port 3000)

- `/` - Main interface
- Real-time streaming via Server-Sent Events

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **LangChain**: AI agent framework
- **Server-Sent Events**: Real-time streaming
- **Pydantic**: Data validation
- **python-dotenv**: Environment management

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling with CSS variables
- **shadcn/ui**: Component library
- **TanStack Query**: Server state management
- **Zod**: Schema validation
- **Lucide React**: Icons

## Environment Variables

Make sure your `.env` file in the root directory contains:

```env
# AI Model API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Search APIs (choose one or more)
TAVILY_API_KEY=your_tavily_key
EXA_API_KEY=your_exa_key
GOOGLE_API_KEY=your_google_key
GOOGLE_CX=your_google_cx

# Model Configuration
WRITER_PROVIDER=anthropic
WRITER_MODEL=claude-3-5-sonnet-latest
PLANNER_PROVIDER=anthropic
PLANNER_MODEL=claude-3-5-sonnet-latest
```

## Development

### Backend Development

The backend uses FastAPI with hot-reload enabled. Any changes to Python files will automatically restart the server.

Key files:
- `legal_discovery_backend/src/main.py` - FastAPI application
- `legal_discovery_backend/src/stream_agent.py` - SSE streaming logic
- `src/open_deep_research/legal_discovery_new.py` - LangChain agent

### Frontend Development

The frontend uses Next.js with hot-reload. Changes to React components will update immediately.

Key files:
- `legal_discovery_frontend/src/app/page.tsx` - Main page
- `legal_discovery_frontend/src/components/legal-discovery/legal-discovery-interface.tsx` - Main interface
- `legal_discovery_frontend/src/lib/legal-discovery/` - Types and utilities

## Troubleshooting

### Backend Issues

1. **Import errors**: Make sure you're in the activated virtual environment
2. **Module not found**: Check that `src/` is in the Python path
3. **API key errors**: Verify your `.env` file has the required API keys

### Frontend Issues

1. **Dependencies**: Run `pnpm install` to ensure all packages are installed
2. **CORS errors**: Make sure the backend is running on port 8000
3. **SSE connection issues**: Check that both services are running and accessible

### Common Issues

1. **Port conflicts**: Make sure ports 3000 and 8000 are available
2. **Environment variables**: Ensure `.env` file exists in the root directory
3. **Network issues**: Check that localhost connections are allowed

## Production Deployment

For production deployment:

1. **Backend**: Use a production WSGI server like Gunicorn
2. **Frontend**: Build with `pnpm build` and deploy static files
3. **Environment**: Update API URLs and ensure proper CORS configuration
4. **Security**: Use HTTPS and secure API key management

## License

This project is part of the Open Deep Research framework. See the main project license for details. 