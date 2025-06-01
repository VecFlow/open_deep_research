#!/usr/bin/env python3
"""
Test script for the Legal Discovery Benchmark Suite
Tests the system with a single question to verify everything works
"""

import asyncio
import os
import csv
import json
from datetime import datetime

# Import our benchmark modules
from legal_discovery_runner import LegalDiscoveryRunner
from gpt4_runner import GPT4Runner
from llm_judge import LLMJudge


async def test_single_question():
    """Test the benchmark system with a single question"""
    
    print("🧪 Testing Legal Discovery Benchmark Suite")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found. Please set it and try again.")
        return False
    
    # Create a test question
    test_question = {
        "question_id": "test_1",
        "question": "What are the key elements to establish negligence in a motor vehicle accident case?",
        "question_type": "element_analysis", 
        "complexity": "low",
        "expected_focus": "tort law, negligence, causation"
    }
    
    print(f"Test question: {test_question['question']}")
    print()
    
    try:
        # Test Legal Discovery System
        print("1️⃣  Testing Legal Discovery System...")
        legal_runner = LegalDiscoveryRunner()
        legal_result = await legal_runner.run_legal_discovery(
            test_question["question"], 
            test_question["question_id"]
        )
        
        if legal_result["status"] == "success":
            print("✓ Legal Discovery system test passed")
            print(f"   Execution time: {legal_result['execution_time']:.2f} seconds")
            print(f"   Result length: {len(legal_result['result'])} characters")
        else:
            print(f"❌ Legal Discovery system test failed: {legal_result['result']}")
            return False
        
        print()
        
        # Test GPT-4
        print("2️⃣  Testing GPT-4 System...")
        gpt4_runner = GPT4Runner()
        gpt4_result = await gpt4_runner.run_gpt4_analysis(
            test_question["question"],
            test_question["question_id"] 
        )
        
        if gpt4_result["status"] == "success":
            print("✓ GPT-4 system test passed")
            print(f"   Execution time: {gpt4_result['execution_time']:.2f} seconds")
            print(f"   Result length: {len(gpt4_result['result'])} characters")
            print(f"   Tokens used: {gpt4_result.get('tokens_used', 'N/A')}")
        else:
            print(f"❌ GPT-4 system test failed: {gpt4_result['result']}")
            return False
        
        print()
        
        # Test LLM Judge
        print("3️⃣  Testing LLM Judge...")
        judge = LLMJudge()
        judgment = await judge.judge_comparison(
            test_question["question"],
            legal_result["result"],
            gpt4_result["result"],
            test_question["question_id"]
        )
        
        if judgment["status"] == "success" and "error" not in judgment["evaluation"]:
            print("✓ LLM Judge test passed")
            print(f"   Execution time: {judgment['execution_time']:.2f} seconds")
            
            eval_data = judgment["evaluation"]
            if "winner" in eval_data:
                winner = eval_data["winner"]
                legal_score = eval_data.get("response_a_total", "N/A")
                gpt4_score = eval_data.get("response_b_total", "N/A")
                
                print(f"   Winner: {'Legal Discovery' if winner == 'A' else 'GPT-4' if winner == 'B' else 'Tie'}")
                print(f"   Legal Discovery score: {legal_score}")
                print(f"   GPT-4 score: {gpt4_score}")
            else:
                print("   Judge completed but no winner determined")
        else:
            print(f"❌ LLM Judge test failed: {judgment['evaluation']}")
            return False
        
        print()
        print("🎉 All tests passed! The benchmark system is working correctly.")
        print()
        print("Test Results Summary:")
        print(f"   Legal Discovery: {legal_result['execution_time']:.1f}s")
        print(f"   GPT-4: {gpt4_result['execution_time']:.1f}s")
        print(f"   Judge: {judgment['execution_time']:.1f}s")
        print(f"   Total time: {legal_result['execution_time'] + gpt4_result['execution_time'] + judgment['execution_time']:.1f}s")
        
        # Save test results
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_question": test_question,
            "legal_result": legal_result,
            "gpt4_result": gpt4_result,
            "judgment": judgment
        }
        
        with open("test_results.json", 'w', encoding='utf-8') as file:
            json.dump(test_results, file, indent=2, ensure_ascii=False)
        
        print("\n✓ Test results saved to 'test_results.json'")
        print("\nYou can now run the full benchmark with: python run_benchmark.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def main():
    """Main test function"""
    success = asyncio.run(test_single_question())
    
    if not success:
        print("\n💥 Test failed. Please check the error messages above.")
        exit(1)
    else:
        print("\n🚀 Ready to run full benchmark!")


if __name__ == "__main__":
    main() 