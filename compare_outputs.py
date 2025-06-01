#!/usr/bin/env python3
"""
Compare Outputs Script
Run one question on both systems and display full outputs for comparison
"""

import asyncio
import pandas as pd
from legal_discovery_runner import LegalDiscoveryRunner
from o3_runner import O3Runner


async def compare_outputs():
    """Run both systems and display full outputs for comparison"""
    
    # Load just the first question
    df = pd.read_csv("benchmark_questions.csv")
    first_question = df.iloc[0].to_dict()
    
    print("="*100)
    print("QUESTION BEING ANALYZED:")
    print("="*100)
    print(f"ID: {first_question['question_id']}")
    print(f"Question: {first_question['question']}")
    print(f"Type: {first_question['question_type']}")
    print()
    
    # Run Legal Discovery System
    print("="*100)
    print("LEGAL DISCOVERY SYSTEM OUTPUT:")
    print("="*100)
    
    legal_runner = LegalDiscoveryRunner()
    legal_result = await legal_runner.run_legal_discovery(
        first_question['question'],
        str(first_question['question_id'])
    )
    
    print(f"Execution time: {legal_result['execution_time']:.2f} seconds")
    print(f"Status: {legal_result['status']}")
    print(f"Length: {len(legal_result['result'])} characters")
    print()
    print("FULL LEGAL DISCOVERY OUTPUT:")
    print("-" * 100)
    print(legal_result['result'])
    print("-" * 100)
    print()
    
    # Run O3 System
    print("="*100)
    print("O3 WITH DOCUMENT SEARCH OUTPUT:")
    print("="*100)
    
    o3_runner = O3Runner()
    o3_result = await o3_runner.run_o3_analysis(
        first_question['question'],
        str(first_question['question_id'])
    )
    
    print(f"Execution time: {o3_result['execution_time']:.2f} seconds")
    print(f"Status: {o3_result['status']}")
    print(f"Length: {len(o3_result['result'])} characters")
    print(f"Document context: {o3_result.get('document_context_length', 0)} characters")
    print(f"Search queries: {o3_result.get('search_queries', [])}")
    print()
    print("FULL O3 OUTPUT:")
    print("-" * 100)
    print(o3_result['result'])
    print("-" * 100)
    print()
    
    print("="*100)
    print("COMPARISON SUMMARY:")
    print("="*100)
    print(f"Legal Discovery: {legal_result['execution_time']:.1f}s, {len(legal_result['result'])} chars")
    print(f"O3 with Docs: {o3_result['execution_time']:.1f}s, {len(o3_result['result'])} chars")
    
    return legal_result, o3_result


if __name__ == "__main__":
    asyncio.run(compare_outputs()) 