#!/usr/bin/env python3
"""
Direct O3 Test
Test just the O3 system to verify API parameters are correct
"""

import asyncio
import pandas as pd
from o3_runner import O3Runner


async def test_o3_direct():
    """Test O3 directly with the first question"""
    
    # Load just the first question
    df = pd.read_csv("benchmark_questions.csv")
    first_question = df.iloc[0].to_dict()
    
    print("=" * 80)
    print("DIRECT O3 TEST")
    print("=" * 80)
    print(f"Question ID: {first_question['question_id']}")
    print(f"Question: {first_question['question']}")
    print()
    
    # Test O3 with Document Search
    print("Testing O3 with document search...")
    
    try:
        o3_runner = O3Runner()
        o3_result = await o3_runner.run_o3_analysis(
            first_question['question'],
            str(first_question['question_id'])
        )
        
        print(f"✅ Status: {o3_result['status']}")
        print(f"✅ Execution time: {o3_result['execution_time']:.2f} seconds")
        print(f"✅ Search queries: {o3_result.get('search_queries', [])}")
        print(f"✅ Document context length: {o3_result.get('document_context_length', 0)} characters")
        print(f"✅ Result length: {len(o3_result['result'])} characters")
        print(f"✅ Tokens used: {o3_result.get('tokens_used', 0)}")
        print()
        print("First 1000 characters of result:")
        print("-" * 80)
        print(o3_result['result'][:1000])
        print("-" * 80)
        
        if o3_result['status'] == 'success':
            print("\n🎉 O3 TEST SUCCESSFUL!")
            return True
        else:
            print(f"\n❌ O3 returned error status: {o3_result['status']}")
            return False
            
    except Exception as e:
        print(f"❌ O3 test failed with exception: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_o3_direct()) 