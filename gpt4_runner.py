#!/usr/bin/env python3
"""
GPT-4 Runner for Benchmarking
Runs GPT-4 directly on questions from CSV file for comparison with legal discovery system
"""

import asyncio
import csv
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os
from openai import AsyncOpenAI


class GPT4Runner:
    """Runner for GPT-4 benchmark"""
    
    def __init__(self, questions_file: str = "benchmark_questions.csv"):
        self.questions_file = questions_file
        self.results = []
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # System prompt for legal analysis
        self.system_prompt = """You are an expert legal analyst and attorney with extensive experience in litigation, discovery, and legal research. 

Your task is to provide comprehensive legal analysis for the given case scenarios or questions. For each question, provide:

1. **Legal Analysis**: Thorough analysis of the legal issues involved
2. **Key Considerations**: Important factors, precedents, and legal principles
3. **Strategic Approach**: Recommended approach for handling the matter
4. **Discovery Strategy**: If applicable, outline document discovery and witness examination strategies
5. **Potential Challenges**: Identify likely obstacles and opposing arguments
6. **Deposition Questions**: If relevant, suggest key deposition questions for witnesses

Provide practical, actionable advice that would be useful for a practicing attorney. Be specific and cite relevant legal concepts, but you don't need to cite specific cases unless they are landmark decisions that any attorney would know.

Format your response with clear sections and bullet points where appropriate for readability."""
    
    def load_questions(self) -> List[Dict[str, str]]:
        """Load questions from CSV file"""
        questions = []
        with open(self.questions_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                questions.append(row)
        return questions
    
    async def run_gpt4_analysis(self, question: str, question_id: str) -> Dict[str, Any]:
        """Run GPT-4 analysis on a single question"""
        print(f"Running GPT-4 analysis for question {question_id}: {question[:100]}...")
        
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=4000,
                temperature=0.1,  # Low temperature for more consistent legal analysis
                timeout=120
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            result_text = response.choices[0].message.content
            
            return {
                "question_id": question_id,
                "question": question,
                "result": result_text,
                "execution_time": execution_time,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"Error running GPT-4 analysis for question {question_id}: {str(e)}")
            return {
                "question_id": question_id,
                "question": question,
                "result": f"Error: {str(e)}",
                "execution_time": execution_time,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": 0
            }
    
    async def run_all_questions(self) -> List[Dict[str, Any]]:
        """Run GPT-4 analysis on all questions"""
        questions = self.load_questions()
        print(f"Running GPT-4 analysis on {len(questions)} questions...")
        
        results = []
        for question_data in questions:
            result = await self.run_gpt4_analysis(
                question_data["question"], 
                question_data["question_id"]
            )
            result.update({
                "question_type": question_data["question_type"],
                "complexity": question_data["complexity"],
                "expected_focus": question_data["expected_focus"]
            })
            results.append(result)
            
            # Save intermediate results
            self.save_results(results, "gpt4_results_temp.json")
            
            # Small delay between questions to avoid rate limits
            await asyncio.sleep(1)
        
        self.results = results
        return results
    
    def save_results(self, results: List[Dict[str, Any]], filename: str):
        """Save results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
        print(f"Results saved to {filename}")


async def main():
    """Main execution function"""
    # Check if we have the necessary environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set it in your environment.")
        return
    
    runner = GPT4Runner()
    results = await runner.run_all_questions()
    
    # Save final results
    runner.save_results(results, "gpt4_results.json")
    print(f"Completed GPT-4 benchmark with {len(results)} questions")
    
    # Print summary statistics
    successful_runs = [r for r in results if r["status"] == "success"]
    if successful_runs:
        avg_time = sum(r["execution_time"] for r in successful_runs) / len(successful_runs)
        total_tokens = sum(r.get("tokens_used", 0) for r in successful_runs)
        print(f"Average execution time: {avg_time:.2f} seconds")
        print(f"Total tokens used: {total_tokens}")


if __name__ == "__main__":
    asyncio.run(main()) 