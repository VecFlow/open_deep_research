#!/usr/bin/env python3
"""
Single Question Test
Test one question on both Legal Discovery System and O3 with document search
"""

import asyncio
import pandas as pd
from legal_discovery_runner import LegalDiscoveryRunner
from o3_runner import O3Runner


async def test_single_question():
    """Test the first benchmark question on both systems"""
    
    # Load just the first question
    df = pd.read_csv("benchmark_questions.csv")
    first_question = df.iloc[0].to_dict()
    
    print("=" * 80)
    print("TESTING SINGLE QUESTION")
    print("=" * 80)
    print(f"Question ID: {first_question['question_id']}")
    print(f"Question: {first_question['question']}")
    print(f"Type: {first_question['question_type']}")
    print(f"Complexity: {first_question['complexity']}")
    print()
    
    # Test Legal Discovery System
    print("=" * 80)
    print("TESTING LEGAL DISCOVERY SYSTEM")
    print("=" * 80)
    
    try:
        legal_runner = LegalDiscoveryRunner()
        legal_result = await legal_runner.run_legal_discovery(
            first_question['question'],
            str(first_question['question_id'])
        )
        
        print(f"Status: {legal_result['status']}")
        print(f"Execution time: {legal_result['execution_time']:.2f} seconds")
        print(f"Result length: {len(legal_result['result'])} characters")
        print(f"First 500 chars: {legal_result['result'][:500]}...")
        print("✅ Legal Discovery System test completed successfully")
        
    except Exception as e:
        print(f"❌ Legal Discovery System failed: {e}")
        legal_result = None
    
    print()
    
    # Test O3 with Document Search
    print("=" * 80)
    print("TESTING O3 WITH DOCUMENT SEARCH")
    print("=" * 80)
    
    try:
        o3_runner = O3Runner()
        o3_result = await o3_runner.run_o3_analysis(
            first_question['question'],
            str(first_question['question_id'])
        )
        
        print(f"Status: {o3_result['status']}")
        print(f"Execution time: {o3_result['execution_time']:.2f} seconds")
        print(f"Search queries: {o3_result.get('search_queries', [])}")
        print(f"Document context length: {o3_result.get('document_context_length', 0)} characters")
        print(f"Result length: {len(o3_result['result'])} characters")
        print(f"First 500 chars: {o3_result['result'][:500]}...")
        print("✅ O3 with Document Search test completed successfully")
        
    except Exception as e:
        print(f"❌ O3 with Document Search failed: {e}")
        o3_result = None
    
    print()
    print("=" * 80)
    print("SINGLE QUESTION TEST SUMMARY")
    print("=" * 80)
    
    if legal_result and o3_result:
        print("✅ Both systems completed successfully!")
        print(f"Legal Discovery: {legal_result['execution_time']:.2f}s, {len(legal_result['result'])} chars")
        print(f"O3 with Docs: {o3_result['execution_time']:.2f}s, {len(o3_result['result'])} chars")
        print()
        print("🚀 Ready to run full benchmark suite!")
        return True
    else:
        print("❌ One or both systems failed - check errors above")
        return False


if __name__ == "__main__":
    asyncio.run(test_single_question()) 