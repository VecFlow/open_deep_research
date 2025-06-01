#!/usr/bin/env python3
"""
LLM Judge for Benchmarking
Compares results from legal discovery system and GPT-4 using an LLM as judge
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
import os
from openai import AsyncOpenAI


class LLMJudge:
    """LLM Judge for comparing legal analysis results"""
    
    def __init__(self, legal_results_file: str = "legal_discovery_results.json", 
                 gpt4_results_file: str = "gpt4_results.json"):
        self.legal_results_file = legal_results_file
        self.gpt4_results_file = gpt4_results_file
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Judging criteria and prompt
        self.judge_prompt = """You are an expert legal analyst tasked with evaluating and comparing two legal analysis responses. 

Evaluate both responses based on these criteria:

**COMPREHENSIVENESS (25 points)**
- Does the response address all relevant legal issues?
- Are important aspects of the legal question covered?
- Is the analysis thorough and complete?

**ACCURACY (25 points)**
- Are the legal principles correctly stated?
- Is the analysis legally sound?
- Are any factual or legal errors present?

**PRACTICAL UTILITY (25 points)**
- Is the advice actionable for a practicing attorney?
- Does it provide clear next steps or strategies?
- Is it useful for litigation planning?

**ORGANIZATION & CLARITY (15 points)**
- Is the response well-structured and easy to follow?
- Are complex concepts explained clearly?
- Is the writing professional and concise?

**SPECIFICITY (10 points)**
- Does the response provide specific guidance rather than generalities?
- Are concrete examples or strategies provided?
- Is the advice tailored to the specific legal scenario?

**EVALUATION INSTRUCTIONS:**
1. Read both responses carefully
2. Score each response on each criterion (0 to maximum points as integers)
3. Provide a brief justification for each score
4. Determine the overall winner
5. Provide a summary explanation of your decision

**RESPONSE FORMAT:**
```json
{
    "response_a_scores": {
        "comprehensiveness": 0,
        "accuracy": 0, 
        "practical_utility": 0,
        "organization_clarity": 0,
        "specificity": 0
    },
    "response_b_scores": {
        "comprehensiveness": 25,
        "accuracy": 25,
        "practical_utility": 25, 
        "organization_clarity": 15,
        "specificity": 10
    },
    "response_a_total": 0,
    "response_b_total": 100,
    "winner": "A",
    "justification": "Brief explanation of scoring decisions for each criterion",
    "summary": "Overall explanation of why the winner was chosen and key differentiators"
}
```

Be objective and fair in your evaluation. Focus on the quality of legal analysis rather than writing style preferences. Use only integer scores without fractions or slashes."""
    
    def load_results(self) -> Tuple[List[Dict], List[Dict]]:
        """Load results from both systems"""
        with open(self.legal_results_file, 'r', encoding='utf-8') as file:
            legal_results = json.load(file)
        
        with open(self.gpt4_results_file, 'r', encoding='utf-8') as file:
            gpt4_results = json.load(file)
        
        return legal_results, gpt4_results
    
    async def judge_comparison(self, question: str, legal_response: str, 
                              gpt4_response: str, question_id: str) -> Dict[str, Any]:
        """Judge a single comparison between legal discovery and GPT-4 responses"""
        print(f"Judging comparison for question {question_id}...")
        
        comparison_prompt = f"""
**LEGAL QUESTION:**
{question}

**RESPONSE A (Legal Discovery System):**
{legal_response}

**RESPONSE B (GPT-4 Direct):**
{gpt4_response}

Please evaluate and compare these two responses according to the criteria provided."""
        
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4 as judge
                messages=[
                    {"role": "system", "content": self.judge_prompt},
                    {"role": "user", "content": comparison_prompt}
                ],
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent judging
                timeout=120
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Try to parse the JSON response
            result_text = response.choices[0].message.content
            
            # Extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
            if json_match:
                try:
                    evaluation = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    evaluation = {"error": "Failed to parse JSON", "raw_response": result_text}
            else:
                evaluation = {"error": "No JSON found in response", "raw_response": result_text}
            
            return {
                "question_id": question_id,
                "question": question,
                "evaluation": evaluation,
                "execution_time": execution_time,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"Error judging question {question_id}: {str(e)}")
            return {
                "question_id": question_id,
                "question": question,
                "evaluation": {"error": str(e)},
                "execution_time": execution_time,
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
    
    async def judge_all_comparisons(self) -> List[Dict[str, Any]]:
        """Judge all comparisons between the two systems"""
        legal_results, gpt4_results = self.load_results()
        
        # Create lookup dictionaries by question_id
        legal_lookup = {r["question_id"]: r for r in legal_results if r["status"] == "success"}
        gpt4_lookup = {r["question_id"]: r for r in gpt4_results if r["status"] == "success"}
        
        # Find common successful questions
        common_questions = set(legal_lookup.keys()) & set(gpt4_lookup.keys())
        print(f"Found {len(common_questions)} questions with successful results from both systems")
        
        judgments = []
        for question_id in sorted(common_questions):
            legal_result = legal_lookup[question_id]
            gpt4_result = gpt4_lookup[question_id]
            
            judgment = await self.judge_comparison(
                legal_result["question"],
                legal_result["result"],
                gpt4_result["result"],
                question_id
            )
            
            # Add metadata
            judgment.update({
                "question_type": legal_result["question_type"],
                "complexity": legal_result["complexity"],
                "expected_focus": legal_result["expected_focus"],
                "legal_execution_time": legal_result["execution_time"],
                "gpt4_execution_time": gpt4_result["execution_time"]
            })
            
            judgments.append(judgment)
            
            # Save intermediate results
            self.save_judgments(judgments, "judge_results_temp.json")
            
            # Small delay between judgments
            await asyncio.sleep(1)
        
        return judgments
    
    def save_judgments(self, judgments: List[Dict[str, Any]], filename: str):
        """Save judgment results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(judgments, file, indent=2, ensure_ascii=False)
        print(f"Judgments saved to {filename}")
    
    def analyze_results(self, judgments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the overall judgment results"""
        successful_judgments = [j for j in judgments if j["status"] == "success" and "error" not in j["evaluation"]]
        
        if not successful_judgments:
            return {"error": "No successful judgments found"}
        
        legal_wins = 0
        gpt4_wins = 0
        ties = 0
        
        legal_scores = []
        gpt4_scores = []
        
        wins_by_category = {}
        wins_by_complexity = {}
        
        for judgment in successful_judgments:
            eval_data = judgment["evaluation"]
            winner = eval_data.get("winner", "").upper()
            
            if winner == "A":  # Legal Discovery System
                legal_wins += 1
                category_winner = "legal_discovery"
            elif winner == "B":  # GPT-4
                gpt4_wins += 1
                category_winner = "gpt4"
            else:
                ties += 1
                category_winner = "tie"
            
            # Track wins by question type and complexity
            question_type = judgment.get("question_type", "unknown")
            complexity = judgment.get("complexity", "unknown")
            
            wins_by_category[question_type] = wins_by_category.get(question_type, {})
            wins_by_category[question_type][category_winner] = wins_by_category[question_type].get(category_winner, 0) + 1
            
            wins_by_complexity[complexity] = wins_by_complexity.get(complexity, {})
            wins_by_complexity[complexity][category_winner] = wins_by_complexity[complexity].get(category_winner, 0) + 1
            
            # Collect scores
            legal_scores.append(eval_data.get("response_a_total", 0))
            gpt4_scores.append(eval_data.get("response_b_total", 0))
        
        total_judgments = len(successful_judgments)
        
        return {
            "total_judgments": total_judgments,
            "legal_discovery_wins": legal_wins,
            "gpt4_wins": gpt4_wins,
            "ties": ties,
            "legal_discovery_win_rate": legal_wins / total_judgments if total_judgments > 0 else 0,
            "gpt4_win_rate": gpt4_wins / total_judgments if total_judgments > 0 else 0,
            "tie_rate": ties / total_judgments if total_judgments > 0 else 0,
            "average_legal_score": sum(legal_scores) / len(legal_scores) if legal_scores else 0,
            "average_gpt4_score": sum(gpt4_scores) / len(gpt4_scores) if gpt4_scores else 0,
            "wins_by_category": wins_by_category,
            "wins_by_complexity": wins_by_complexity
        }


async def main():
    """Main execution function"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found. Please set it in your environment.")
        return
    
    judge = LLMJudge()
    
    try:
        judgments = await judge.judge_all_comparisons()
        
        # Save final results
        judge.save_judgments(judgments, "judge_results.json")
        
        # Analyze results
        analysis = judge.analyze_results(judgments)
        
        # Save analysis
        with open("benchmark_analysis.json", 'w', encoding='utf-8') as file:
            json.dump(analysis, file, indent=2, ensure_ascii=False)
        
        print(f"\nBenchmark Analysis Results:")
        print(f"Total judgments: {analysis.get('total_judgments', 0)}")
        print(f"Legal Discovery wins: {analysis.get('legal_discovery_wins', 0)} ({analysis.get('legal_discovery_win_rate', 0):.1%})")
        print(f"GPT-4 wins: {analysis.get('gpt4_wins', 0)} ({analysis.get('gpt4_win_rate', 0):.1%})")
        print(f"Ties: {analysis.get('ties', 0)} ({analysis.get('tie_rate', 0):.1%})")
        print(f"Average Legal Discovery score: {analysis.get('average_legal_score', 0):.1f}/100")
        print(f"Average GPT-4 score: {analysis.get('average_gpt4_score', 0):.1f}/100")
        
    except FileNotFoundError as e:
        print(f"Error: Could not find results files. Please run the benchmark systems first. {e}")
    except Exception as e:
        print(f"Error running judge: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 