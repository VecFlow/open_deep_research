#!/bin/bash

# Run the interrupt test script
echo "🧪 Running LangGraph interrupt flow test..."
echo "========================================"

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Set OpenAI API key if not already set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Please set it first:"
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    exit 1
fi

# Run the test
echo "🚀 Starting test..."
python test_interrupt_flow.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 Test completed successfully!"
else
    echo ""
    echo "💥 Test failed with exit code $exit_code"
fi

exit $exit_code 