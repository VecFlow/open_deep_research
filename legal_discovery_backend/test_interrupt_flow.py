#!/usr/bin/env python3
"""
Test script to debug LangGraph interrupt handling flow.
This script simulates the workflow execution without the full backend.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from open_deep_research.legal_discovery import builder
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

async def test_interrupt_workflow():
    """Test the interrupt workflow flow."""
    print("🧪 Testing LangGraph interrupt workflow...")
    
    # Create checkpointer
    checkpointer = MemorySaver()
    
    # Compile graph
    compiled_graph = builder.compile(checkpointer=checkpointer)
    
    # Configuration
    thread_id = "test-thread-123"
    workflow_config = {
        "configurable": {
            "thread_id": thread_id,
            "writer_provider": "openai",
            "writer_model": "gpt-4o",
            "planner_provider": "openai", 
            "planner_model": "gpt-4o",
            "analysis_structure": "liability analysis, damages assessment, key witnesses",
            "number_of_queries": 2,
            "max_search_depth": 1,
            # Add mock Weaviate configuration
            "weaviate_url": "https://mock-weaviate.example.com",
            "weaviate_api_key": "mock-api-key", 
            "weaviate_collection_name": "Test_collection",
            # Set Azure to None to use Weaviate
            "azure_search_endpoint": None,
            "azure_search_key": None,
            "azure_search_index": None,
        }
    }
    
    # Input
    workflow_input = {
        "background_on_case": "Test case about contract dispute"
    }
    
    print(f"📋 Starting workflow with input: {workflow_input}")
    print(f"⚙️  Configuration: {workflow_config}")
    
    # Phase 1: Run until interrupt
    print("\n🚀 Phase 1: Running until interrupt...")
    interrupt_hit = False
    final_state = None
    step_count = 0
    
    try:
        async for chunk in compiled_graph.astream(
            workflow_input,
            config=workflow_config
        ):
            step_count += 1
            print(f"📊 Step {step_count}: {list(chunk.keys()) if isinstance(chunk, dict) else chunk}")
            
            if isinstance(chunk, dict):
                print(f"🔍 Chunk content keys: {list(chunk.keys())}")
                
                # Check for interrupt
                if "__interrupt__" in chunk:
                    print("🛑 INTERRUPT DETECTED!")
                    interrupt_data = chunk.get("__interrupt__", ())
                    if interrupt_data and len(interrupt_data) > 0:
                        interrupt_obj = interrupt_data[0]
                        print(f"📝 Interrupt message: {getattr(interrupt_obj, 'value', 'No message')}")
                    
                    interrupt_hit = True
                    final_state = chunk
                    print("🔄 Breaking from stream to wait for feedback...")
                    break
            
            final_state = chunk
        
        print(f"\n📊 Stream ended. Interrupt hit: {interrupt_hit}")
        print(f"📊 Final state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}")
        
        if not interrupt_hit:
            print("❌ Expected interrupt but didn't get one!")
            return False
        
        # Phase 2: Provide feedback and resume
        print("\n🚀 Phase 2: Providing feedback and resuming...")
        
        # Simulate approval
        feedback_value = True  # Boolean True for approval
        print(f"📝 Providing feedback: {feedback_value} (type: {type(feedback_value)})")
        
        # Resume with new stream
        resume_step_count = 0
        async for resume_chunk in compiled_graph.astream(
            Command(resume=feedback_value),
            config=workflow_config
        ):
            resume_step_count += 1
            print(f"📊 Resume Step {resume_step_count}: {list(resume_chunk.keys()) if isinstance(resume_chunk, dict) else resume_chunk}")
            
            if isinstance(resume_chunk, dict):
                print(f"🔍 Resume chunk content keys: {list(resume_chunk.keys())}")
                
                # Check if we hit another interrupt
                if "__interrupt__" in resume_chunk:
                    print("🛑 Another interrupt detected - this shouldn't happen for approval!")
                    return False
            
            final_state = resume_chunk
        
        print(f"\n✅ Workflow completed successfully!")
        print(f"📊 Final resume state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'Not a dict'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during workflow: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Main test function."""
    print("🔬 Starting LangGraph interrupt flow test...\n")
    
    success = await test_interrupt_workflow()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
    
    return success

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 