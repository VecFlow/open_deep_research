#!/usr/bin/env python3
"""
O3 Runner with Document Search for Benchmarking
Runs O3 with document retrieval on questions from CSV file for comparison with legal discovery system
"""

import asyncio
import csv
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os
from openai import AsyncOpenAI

# Import document search functionality from the legal discovery system
from src.open_deep_research.utils import search_documents_with_azure_ai
from src.open_deep_research.configuration import Configuration


class O3Runner:
    """Runner for O3 with document search benchmark"""
    
    def __init__(self, questions_file: str = "benchmark_questions.csv"):
        self.questions_file = questions_file
        self.results = []
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # System prompt for legal analysis with document context
        self.system_prompt = """You are an expert legal analyst and attorney with extensive experience in litigation, discovery, and legal research. You have access to a comprehensive database of legal documents and correspondence related to the case.

Your task is to provide comprehensive legal analysis for the given case scenarios or questions using both your legal expertise and the provided document context from the case files.

For each question, provide:

1. **Legal Analysis**: Thorough analysis of the legal issues based on the document evidence
2. **Key Findings from Documents**: Important discoveries from the case documents
3. **Strategic Approach**: Recommended approach for handling the matter based on document evidence
4. **Discovery Strategy**: Document discovery and witness examination strategies informed by the case materials
5. **Potential Challenges**: Identify likely obstacles and opposing arguments based on case context
6. **Deposition Questions**: If relevant, suggest key deposition questions for witnesses based on document findings

Base your analysis heavily on the provided document context. Reference specific documents, communications, or evidence found in the search results. Provide practical, actionable advice that would be useful for a practicing attorney working on this specific case.

Format your response with clear sections and bullet points where appropriate for readability."""
    
    def load_questions(self) -> List[Dict[str, str]]:
        """Load questions from CSV file"""
        questions = []
        with open(self.questions_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                questions.append(row)
        return questions
    
    async def generate_search_queries(self, question: str) -> List[str]:
        """Generate document search queries for the legal question"""
        query_prompt = f"""Based on the following legal question, generate 3 specific document search queries that would help find relevant evidence and information:

Question: {question}

Generate queries that would search for:
1. Relevant contracts, agreements, or legal documents
2. Communications between parties
3. Evidence of damages, disputes, or procedural issues

Provide only the search queries, one per line."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 for query generation
                messages=[
                    {"role": "user", "content": query_prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse the queries from the response
            query_text = response.choices[0].message.content.strip()
            queries = [q.strip() for q in query_text.split('\n') if q.strip()]
            
            # Ensure we have exactly 3 queries
            if len(queries) < 3:
                queries.extend([question] * (3 - len(queries)))
            
            return queries[:3]
            
        except Exception as e:
            print(f"Error generating search queries: {e}")
            # Fallback: use the question itself as queries
            return [question, question, question]
    
    async def run_o3_analysis(self, question: str, question_id: str) -> Dict[str, Any]:
        """Run O3 analysis with document search on a single question"""
        print(f"Running O3 with document search for question {question_id}: {question[:100]}...")
        
        start_time = time.time()
        
        try:
            # Step 1: Generate search queries for the question
            search_queries = await self.generate_search_queries(question)
            print(f"Generated search queries: {search_queries}")
            
            # Step 2: Search documents using the same function as legal discovery system
            # Create a minimal configuration object for document search
            configurable = type('Configuration', (), {
                'search_provider': 'azureaisearch',
                'search_api_config': {},
                'max_search_depth': 2,
                'number_of_queries': 3
            })()
            
            # Search documents
            document_context = await search_documents_with_azure_ai(search_queries, configurable)
            print(f"Retrieved {len(document_context)} characters of document context")
            
            # Step 3: Run O3 analysis with document context
            analysis_prompt = f"""Legal Question: {question}

Document Context from Case Files:
{document_context}

Please provide a comprehensive legal analysis based on the question and the document evidence provided."""

            response = await self.client.chat.completions.create(
                model="o3-mini",  # Use O3 model
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=8000,
                temperature=0.1,
                timeout=300  # Longer timeout for O3
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            result_text = response.choices[0].message.content
            
            return {
                "question_id": question_id,
                "question": question,
                "search_queries": search_queries,
                "document_context_length": len(document_context),
                "result": result_text,
                "execution_time": execution_time,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"Error running O3 analysis for question {question_id}: {str(e)}")
            return {
                "question_id": question_id,
                "question": question,
                "search_queries": [],
                "document_context_length": 0,
                "result": f"Error: {str(e)}",
                "execution_time": execution_time,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": 0
            }
    
    async def run_all_questions(self) -> List[Dict[str, Any]]:
        """Run O3 analysis with document search on all questions"""
        questions = self.load_questions()
        print(f"Running O3 with document search on {len(questions)} questions...")
        
        results = []
        for question_data in questions:
            result = await self.run_o3_analysis(
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
            self.save_results(results, "o3_results_temp.json")
            
            # Small delay between questions to avoid rate limits
            await asyncio.sleep(2)
        
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
    
    runner = O3Runner()
    results = await runner.run_all_questions()
    
    # Save final results
    runner.save_results(results, "o3_results.json")
    print(f"Completed O3 with document search benchmark with {len(results)} questions")
    
    # Print summary statistics
    successful_runs = [r for r in results if r["status"] == "success"]
    if successful_runs:
        avg_time = sum(r["execution_time"] for r in successful_runs) / len(successful_runs)
        total_tokens = sum(r.get("tokens_used", 0) for r in successful_runs)
        avg_doc_length = sum(r.get("document_context_length", 0) for r in successful_runs) / len(successful_runs)
        print(f"Average execution time: {avg_time:.2f} seconds")
        print(f"Total tokens used: {total_tokens}")
        print(f"Average document context length: {avg_doc_length:.0f} characters")


if __name__ == "__main__":
    asyncio.run(main()) 