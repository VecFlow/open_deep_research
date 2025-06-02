#!/usr/bin/env python3
"""
Debug LangGraph Workflow Execution
Direct test of the LangGraph workflow components
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to Python path
backend_path = Path(__file__).parent
src_path = backend_path.parent / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(backend_path))

# Setup logging to see all details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all LangGraph components can be imported"""
    print("🔍 Testing LangGraph imports...")
    
    try:
        from open_deep_research.legal_discovery import builder
        print("✅ Successfully imported builder from legal_discovery")
        
        from open_deep_research.legal_state import LegalAnalysisState, AnalysisCategory
        print("✅ Successfully imported state classes")
        
        from open_deep_research.configuration import Configuration
        print("✅ Successfully imported Configuration")
        
        from langgraph.checkpoint.memory import MemorySaver
        print("✅ Successfully imported MemorySaver")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        print(f"📋 Traceback:\n{traceback.format_exc()}")
        return False

def test_graph_compilation():
    """Test if the graph can be compiled"""
    print("\n🔧 Testing graph compilation...")
    
    try:
        from open_deep_research.legal_discovery import builder
        from langgraph.checkpoint.memory import MemorySaver
        
        checkpointer = MemorySaver()
        compiled_graph = builder.compile(checkpointer=checkpointer)
        print("✅ Successfully compiled graph with checkpointer")
        
        return compiled_graph
        
    except Exception as e:
        print(f"❌ Graph compilation failed: {e}")
        import traceback
        print(f"📋 Traceback:\n{traceback.format_exc()}")
        return None

def test_workflow_input():
    """Test workflow input preparation"""
    print("\n📝 Testing workflow input preparation...")
    
    try:
        workflow_input = {
            "background_on_case": "This is a test case involving a contract dispute."
        }
        
        workflow_config = {
            "configurable": {
                "writer_provider": "openai",
                "writer_model": "gpt-4o",
                "planner_provider": "openai",
                "planner_model": "gpt-4o",
                "analysis_structure": "liability analysis, damages assessment",
                "number_of_queries": 3,
                "max_search_depth": 2,
            }
        }
        
        print(f"✅ Workflow input: {workflow_input}")
        print(f"✅ Workflow config: {workflow_config}")
        
        return workflow_input, workflow_config
        
    except Exception as e:
        print(f"❌ Input preparation failed: {e}")
        return None, None

async def test_workflow_execution():
    """Test actual workflow execution"""
    print("\n🚀 Testing workflow execution...")
    
    try:
        # Import components
        from open_deep_research.legal_discovery import builder
        from langgraph.checkpoint.memory import MemorySaver
        
        # Prepare components
        checkpointer = MemorySaver()
        compiled_graph = builder.compile(checkpointer=checkpointer)
        
        workflow_input = {
            "background_on_case": "Test contract dispute case for debugging."
        }
        
        workflow_config = {
            "configurable": {
                "thread_id": "debug-thread-123",
                "writer_provider": "openai",
                "writer_model": "gpt-4o",
                "planner_provider": "openai", 
                "planner_model": "gpt-4o",
                "analysis_structure": "liability analysis, damages assessment",
                "number_of_queries": 2,
                "max_search_depth": 1,
            }
        }
        
        print("🎯 Starting workflow stream...")
        
        step_count = 0
        async for chunk in compiled_graph.astream(workflow_input, config=workflow_config):
            step_count += 1
            print(f"📊 Step {step_count}: {list(chunk.keys()) if chunk else 'empty'}")
            
            if step_count > 5:  # Limit to prevent infinite loop
                print("⏹️  Stopping after 5 steps for testing")
                break
        
        print("✅ Workflow execution completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        print(f"📋 Traceback:\n{traceback.format_exc()}")
        return False

def test_environment_variables():
    """Test if environment variables are loaded"""
    print("\n🔑 Testing environment variables...")
    
    env_vars = [
        "OPENAI_API_KEY",
        "PLANNER_PROVIDER", 
        "WRITER_PROVIDER",
        "PLANNER_MODEL",
        "WRITER_MODEL"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Don't print full API keys for security
            if "API_KEY" in var:
                print(f"✅ {var}: {value[:8]}...{value[-4:] if len(value) > 12 else value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")

async def main():
    """Run all debug tests"""
    print("🔧 LangGraph Workflow Debug Tool")
    print("=" * 50)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded environment variables from .env")
    except Exception as e:
        print(f"⚠️  Could not load .env: {e}")
    
    # Run tests
    test_environment_variables()
    
    if not test_imports():
        print("❌ Cannot proceed - import failures")
        return
    
    compiled_graph = test_graph_compilation()
    if not compiled_graph:
        print("❌ Cannot proceed - compilation failures")
        return
    
    workflow_input, workflow_config = test_workflow_input()
    if not workflow_input:
        print("❌ Cannot proceed - input preparation failures")
        return
    
    # Test execution
    success = await test_workflow_execution()
    
    if success:
        print("\n🎉 All tests passed! LangGraph workflow should work.")
    else:
        print("\n💥 Workflow execution failed - see error details above.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())