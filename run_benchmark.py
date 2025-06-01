#!/usr/bin/env python3
"""
Legal Discovery Benchmark Suite
Main orchestrator for running comprehensive benchmarks comparing Legal Discovery System vs O3 with Document Search
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Import our benchmark modules
from legal_discovery_runner import LegalDiscoveryRunner
from o3_runner import O3Runner
from llm_judge import LLMJudge
from visualizer import BenchmarkVisualizer


class BenchmarkOrchestrator:
    """Main orchestrator for the benchmark suite"""
    
    def __init__(self):
        self.start_time = None
        self.results_summary = {}
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        print("Checking prerequisites...")
        
        # Check for OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY environment variable not set")
            print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
            return False
        print("✓ OpenAI API key found")
        
        # Check for required files
        if not Path("benchmark_questions.csv").exists():
            print("❌ benchmark_questions.csv not found")
            return False
        print("✓ Benchmark questions file found")
        
        # Check for required Python packages
        required_packages = ["matplotlib", "seaborn", "pandas", "numpy", "openai"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing required packages: {', '.join(missing_packages)}")
            print("Please install them using: pip install " + " ".join(missing_packages))
            return False
        print("✓ All required packages found")
        
        return True
    
    async def run_legal_discovery_benchmark(self) -> bool:
        """Run the legal discovery system benchmark"""
        print("\n" + "="*60)
        print("PHASE 1: Running Legal Discovery System Benchmark")
        print("="*60)
        
        try:
            runner = LegalDiscoveryRunner()
            results = await runner.run_all_questions()
            
            success_count = len([r for r in results if r["status"] == "success"])
            total_count = len(results)
            
            print(f"✓ Legal Discovery benchmark completed: {success_count}/{total_count} successful")
            self.results_summary["legal_discovery"] = {
                "total": total_count,
                "successful": success_count,
                "success_rate": success_count / total_count if total_count > 0 else 0
            }
            return True
            
        except Exception as e:
            print(f"❌ Legal Discovery benchmark failed: {e}")
            return False
    
    async def run_o3_benchmark(self) -> bool:
        """Run the O3 with document search benchmark"""
        print("\n" + "="*60)
        print("PHASE 2: Running O3 with Document Search Benchmark")
        print("="*60)
        
        try:
            runner = O3Runner()
            results = await runner.run_all_questions()
            
            success_count = len([r for r in results if r["status"] == "success"])
            total_count = len(results)
            
            print(f"✓ O3 with document search benchmark completed: {success_count}/{total_count} successful")
            self.results_summary["o3"] = {
                "total": total_count,
                "successful": success_count,
                "success_rate": success_count / total_count if total_count > 0 else 0
            }
            return True
            
        except Exception as e:
            print(f"❌ O3 benchmark failed: {e}")
            return False
    
    async def run_llm_judge(self) -> bool:
        """Run the LLM judge comparison"""
        print("\n" + "="*60)
        print("PHASE 3: Running LLM Judge Evaluation")
        print("="*60)
        
        try:
            judge = LLMJudge()
            judgments = await judge.judge_all_comparisons()
            analysis = judge.analyze_results(judgments)
            
            # Save analysis summary
            import json
            with open("benchmark_analysis.json", 'w', encoding='utf-8') as file:
                json.dump(analysis, file, indent=2, ensure_ascii=False)
            
            total_judgments = analysis.get('total_judgments', 0)
            legal_wins = analysis.get('legal_discovery_wins', 0)
            o3_wins = analysis.get('o3_wins', 0)
            
            print(f"✓ LLM Judge completed: {total_judgments} comparisons")
            print(f"  Legal Discovery wins: {legal_wins}")
            print(f"  O3 wins: {o3_wins}")
            print(f"  Ties: {analysis.get('ties', 0)}")
            
            self.results_summary["judge"] = {
                "total_judgments": total_judgments,
                "legal_wins": legal_wins,
                "o3_wins": o3_wins,
                "legal_win_rate": analysis.get('legal_discovery_win_rate', 0),
                "o3_win_rate": analysis.get('o3_win_rate', 0)
            }
            return True
            
        except Exception as e:
            print(f"❌ LLM Judge failed: {e}")
            return False
    
    def create_visualizations(self) -> bool:
        """Create benchmark visualizations"""
        print("\n" + "="*60)
        print("PHASE 4: Creating Visualizations")
        print("="*60)
        
        try:
            visualizer = BenchmarkVisualizer()
            visualizer.generate_all_charts()
            
            print("✓ All visualizations created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Visualization creation failed: {e}")
            return False
    
    def generate_final_report(self):
        """Generate a final benchmark report"""
        print("\n" + "="*60)
        print("GENERATING FINAL REPORT")
        print("="*60)
        
        end_time = datetime.now()
        duration = end_time - self.start_time if self.start_time else "Unknown"
        
        report = f"""
# Legal Discovery System vs O3 with Document Search Benchmark Report

**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration}

## Summary

This benchmark compared the Legal Discovery System against O3 with document search across {self.results_summary.get('legal_discovery', {}).get('total', 0)} Suffolk case legal questions. Both systems had access to the same document database containing 70,000 emails and case materials.

### System Performance

**Legal Discovery System:**
- Questions processed: {self.results_summary.get('legal_discovery', {}).get('successful', 0)}/{self.results_summary.get('legal_discovery', {}).get('total', 0)}
- Success rate: {self.results_summary.get('legal_discovery', {}).get('success_rate', 0):.1%}

**O3 with Document Search:**
- Questions processed: {self.results_summary.get('o3', {}).get('successful', 0)}/{self.results_summary.get('o3', {}).get('total', 0)}
- Success rate: {self.results_summary.get('o3', {}).get('success_rate', 0):.1%}

### Head-to-Head Comparison

**Total Comparisons:** {self.results_summary.get('judge', {}).get('total_judgments', 0)}

**Results:**
- Legal Discovery wins: {self.results_summary.get('judge', {}).get('legal_wins', 0)} ({self.results_summary.get('judge', {}).get('legal_win_rate', 0):.1%})
- O3 wins: {self.results_summary.get('judge', {}).get('o3_wins', 0)} ({self.results_summary.get('judge', {}).get('o3_win_rate', 0):.1%})

### Key Differences

**Legal Discovery System:**
- Multi-step workflow with automated category planning
- Document search integrated into analysis workflow
- Specialized legal analysis prompts and structure
- Deposition question generation

**O3 with Document Search:**
- Direct analysis approach with document context
- Query generation followed by document search
- General legal expertise with case-specific evidence
- More streamlined execution

### Files Generated

- `legal_discovery_results.json` - Raw Legal Discovery system results
- `o3_results.json` - Raw O3 with document search results  
- `judge_results.json` - Detailed LLM judge evaluations
- `benchmark_analysis.json` - Statistical analysis summary
- `benchmark_charts/` - Visualization charts and graphs

### Key Insights

The benchmark provides objective comparison across multiple dimensions:
- **Comprehensiveness**: How thoroughly each system addresses legal issues
- **Accuracy**: Legal correctness and soundness of analysis
- **Practical Utility**: Actionability for practicing attorneys
- **Organization & Clarity**: Structure and readability
- **Specificity**: Concrete guidance vs. generalities

### Case Context

This benchmark used Suffolk case-specific questions covering:
- Fraud in the inducement claims
- Construction contract breaches
- Settlement agreement disputes
- Discovery strategy for complex litigation
- Damages assessment and calculation
- Executive deposition planning

### Next Steps

1. Review detailed results in the generated JSON files
2. Examine visualizations in the `benchmark_charts/` directory
3. Consider expanding the question set for more comprehensive evaluation
4. Analyze performance patterns by question type and complexity

---

This benchmark compares a specialized legal discovery workflow against a state-of-the-art LLM with document access on real-world legal questions from an active construction litigation case.
        """
        
        # Save report
        with open("benchmark_report.md", 'w', encoding='utf-8') as file:
            file.write(report)
        
        print("✓ Final report saved to 'benchmark_report.md'")
        print("\n" + "="*60)
        print("BENCHMARK COMPLETE!")
        print("="*60)
        print(f"Total time: {duration}")
        print("\nGenerated files:")
        print("- benchmark_report.md (final report)")
        print("- benchmark_analysis.json (statistical summary)")
        print("- benchmark_charts/ (visualizations)")
        print("- *.json (raw results)")
    
    async def run_full_benchmark(self, skip_legal: bool = False, skip_o3: bool = False, 
                                skip_judge: bool = False, skip_viz: bool = False):
        """Run the complete benchmark suite"""
        self.start_time = datetime.now()
        
        print("🚀 Starting Legal Discovery System vs O3 Benchmark Suite")
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Phase 1: Legal Discovery System
        if not skip_legal:
            success = await self.run_legal_discovery_benchmark()
            if not success:
                print("❌ Benchmark failed at Legal Discovery phase")
                return False
        else:
            print("⏭️  Skipping Legal Discovery benchmark")
        
        # Phase 2: O3
        if not skip_o3:
            success = await self.run_o3_benchmark()
            if not success:
                print("❌ Benchmark failed at O3 phase")
                return False
        else:
            print("⏭️  Skipping O3 benchmark")
        
        # Phase 3: LLM Judge
        if not skip_judge:
            success = await self.run_llm_judge()
            if not success:
                print("❌ Benchmark failed at LLM Judge phase")
                return False
        else:
            print("⏭️  Skipping LLM Judge phase")
        
        # Phase 4: Visualizations
        if not skip_viz:
            success = self.create_visualizations()
            if not success:
                print("❌ Benchmark failed at Visualization phase")
                return False
        else:
            print("⏭️  Skipping Visualization phase")
        
        # Final Report
        self.generate_final_report()
        return True


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Legal Discovery System vs O3 Benchmark Suite")
    parser.add_argument("--skip-legal", action="store_true", 
                       help="Skip legal discovery system benchmark")
    parser.add_argument("--skip-o3", action="store_true", 
                       help="Skip O3 benchmark")
    parser.add_argument("--skip-judge", action="store_true", 
                       help="Skip LLM judge evaluation")
    parser.add_argument("--skip-viz", action="store_true", 
                       help="Skip visualization generation")
    parser.add_argument("--only-viz", action="store_true", 
                       help="Only generate visualizations (requires existing results)")
    
    args = parser.parse_args()
    
    orchestrator = BenchmarkOrchestrator()
    
    # Check prerequisites unless only generating visualizations
    if not args.only_viz and not orchestrator.check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above and try again.")
        sys.exit(1)
    
    # Special case: only generate visualizations
    if args.only_viz:
        print("🎨 Generating visualizations only...")
        success = orchestrator.create_visualizations()
        if success:
            print("✓ Visualizations generated successfully")
        else:
            print("❌ Failed to generate visualizations")
        return
    
    # Run full benchmark
    success = await orchestrator.run_full_benchmark(
        skip_legal=args.skip_legal,
        skip_o3=args.skip_o3, 
        skip_judge=args.skip_judge,
        skip_viz=args.skip_viz
    )
    
    if success:
        print("\n🎉 Benchmark suite completed successfully!")
    else:
        print("\n💥 Benchmark suite failed. Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 