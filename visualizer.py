#!/usr/bin/env python3
"""
Benchmark Results Visualizer
Creates graphs and charts comparing Legal Discovery System vs GPT-4 results
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any


class BenchmarkVisualizer:
    """Creates visualizations for benchmark results"""
    
    def __init__(self, analysis_file: str = "benchmark_analysis.json",
                 judge_results_file: str = "judge_results.json"):
        self.analysis_file = analysis_file
        self.judge_results_file = judge_results_file
        
        # Set up matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create output directory
        Path("benchmark_charts").mkdir(exist_ok=True)
    
    def load_data(self) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Load analysis and detailed judgment data"""
        with open(self.analysis_file, 'r') as file:
            analysis = json.load(file)
        
        with open(self.judge_results_file, 'r') as file:
            judge_results = json.load(file)
        
        return analysis, judge_results
    
    def create_win_rate_chart(self, analysis: Dict[str, Any]):
        """Create overall win rate pie chart"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Overall win rates
        labels = ['Legal Discovery', 'GPT-4', 'Ties']
        sizes = [
            analysis.get('legal_discovery_wins', 0),
            analysis.get('gpt4_wins', 0),
            analysis.get('ties', 0)
        ]
        colors = ['#2E8B57', '#4169E1', '#FFD700']
        
        # Pie chart
        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                          startangle=90, textprops={'fontsize': 12})
        ax1.set_title('Overall Win Rate Comparison', fontsize=16, fontweight='bold')
        
        # Bar chart
        ax2.bar(labels, sizes, color=colors, alpha=0.8)
        ax2.set_ylabel('Number of Wins', fontsize=12)
        ax2.set_title('Win Counts by System', fontsize=16, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(sizes):
            ax2.text(i, v + 0.1, str(v), ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('benchmark_charts/win_rates.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_score_comparison(self, analysis: Dict[str, Any]):
        """Create score comparison chart"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Average scores
        legal_score = analysis.get('average_legal_score', 0)
        gpt4_score = analysis.get('average_gpt4_score', 0)
        
        systems = ['Legal Discovery', 'GPT-4']
        scores = [legal_score, gpt4_score]
        colors = ['#2E8B57', '#4169E1']
        
        # Bar chart of average scores
        bars = ax1.bar(systems, scores, color=colors, alpha=0.8)
        ax1.set_ylabel('Average Score (out of 100)', fontsize=12)
        ax1.set_title('Average Quality Scores', fontsize=16, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar, score in zip(bars, scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{score:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Score difference
        diff = legal_score - gpt4_score
        ax2.barh(['Score Difference'], [diff], 
                color='green' if diff > 0 else 'red', alpha=0.7)
        ax2.set_xlabel('Score Difference (Legal Discovery - GPT-4)', fontsize=12)
        ax2.set_title('Performance Gap', fontsize=16, fontweight='bold')
        ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax2.grid(axis='x', alpha=0.3)
        
        # Add value label
        ax2.text(diff + (0.5 if diff > 0 else -0.5), 0, f'{diff:+.1f}', 
                ha='left' if diff > 0 else 'right', va='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('benchmark_charts/score_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_category_breakdown(self, analysis: Dict[str, Any]):
        """Create breakdown by question type and complexity"""
        wins_by_category = analysis.get('wins_by_category', {})
        wins_by_complexity = analysis.get('wins_by_complexity', {})
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # By question type
        if wins_by_category:
            categories = list(wins_by_category.keys())
            legal_wins = [wins_by_category[cat].get('legal_discovery', 0) for cat in categories]
            gpt4_wins = [wins_by_category[cat].get('gpt4', 0) for cat in categories]
            ties = [wins_by_category[cat].get('tie', 0) for cat in categories]
            
            x = np.arange(len(categories))
            width = 0.25
            
            ax1.bar(x - width, legal_wins, width, label='Legal Discovery', color='#2E8B57', alpha=0.8)
            ax1.bar(x, gpt4_wins, width, label='GPT-4', color='#4169E1', alpha=0.8)
            ax1.bar(x + width, ties, width, label='Ties', color='#FFD700', alpha=0.8)
            
            ax1.set_xlabel('Question Types', fontsize=12)
            ax1.set_ylabel('Number of Wins', fontsize=12)
            ax1.set_title('Performance by Question Type', fontsize=14, fontweight='bold')
            ax1.set_xticks(x)
            ax1.set_xticklabels([cat.replace('_', ' ').title() for cat in categories], rotation=45, ha='right')
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)
        
        # By complexity
        if wins_by_complexity:
            complexities = list(wins_by_complexity.keys())
            legal_wins_comp = [wins_by_complexity[comp].get('legal_discovery', 0) for comp in complexities]
            gpt4_wins_comp = [wins_by_complexity[comp].get('gpt4', 0) for comp in complexities]
            ties_comp = [wins_by_complexity[comp].get('tie', 0) for comp in complexities]
            
            x_comp = np.arange(len(complexities))
            
            ax2.bar(x_comp - width, legal_wins_comp, width, label='Legal Discovery', color='#2E8B57', alpha=0.8)
            ax2.bar(x_comp, gpt4_wins_comp, width, label='GPT-4', color='#4169E1', alpha=0.8)
            ax2.bar(x_comp + width, ties_comp, width, label='Ties', color='#FFD700', alpha=0.8)
            
            ax2.set_xlabel('Question Complexity', fontsize=12)
            ax2.set_ylabel('Number of Wins', fontsize=12)
            ax2.set_title('Performance by Question Complexity', fontsize=14, fontweight='bold')
            ax2.set_xticks(x_comp)
            ax2.set_xticklabels([comp.title() for comp in complexities])
            ax2.legend()
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('benchmark_charts/category_breakdown.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_detailed_scores_heatmap(self, judge_results: List[Dict[str, Any]]):
        """Create heatmap of detailed criterion scores"""
        successful_results = [r for r in judge_results if r["status"] == "success" and "error" not in r["evaluation"]]
        
        if not successful_results:
            print("No successful results found for heatmap")
            return
        
        # Extract scores by criterion
        criteria = ['comprehensiveness', 'accuracy', 'practical_utility', 'organization_clarity', 'specificity']
        
        legal_scores = []
        gpt4_scores = []
        question_ids = []
        
        for result in successful_results:
            eval_data = result["evaluation"]
            if "response_a_scores" in eval_data and "response_b_scores" in eval_data:
                legal_row = [eval_data["response_a_scores"].get(c, 0) for c in criteria]
                gpt4_row = [eval_data["response_b_scores"].get(c, 0) for c in criteria]
                
                legal_scores.append(legal_row)
                gpt4_scores.append(gpt4_row)
                question_ids.append(result["question_id"])
        
        if legal_scores and gpt4_scores:
            # Create comparison heatmap
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 8))
            
            # Legal Discovery scores
            legal_df = pd.DataFrame(legal_scores, columns=[c.replace('_', ' ').title() for c in criteria], 
                                   index=[f"Q{qid}" for qid in question_ids])
            sns.heatmap(legal_df, annot=True, fmt='.1f', cmap='Greens', ax=ax1, cbar_kws={'label': 'Score'})
            ax1.set_title('Legal Discovery Scores', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Questions', fontsize=12)
            
            # GPT-4 scores
            gpt4_df = pd.DataFrame(gpt4_scores, columns=[c.replace('_', ' ').title() for c in criteria],
                                  index=[f"Q{qid}" for qid in question_ids])
            sns.heatmap(gpt4_df, annot=True, fmt='.1f', cmap='Blues', ax=ax2, cbar_kws={'label': 'Score'})
            ax2.set_title('GPT-4 Scores', fontsize=14, fontweight='bold')
            ax2.set_ylabel('')
            
            # Difference (Legal - GPT4)
            diff_df = legal_df - gpt4_df
            sns.heatmap(diff_df, annot=True, fmt='.1f', cmap='RdBu_r', center=0, ax=ax3, 
                       cbar_kws={'label': 'Score Difference'})
            ax3.set_title('Score Differences\n(Legal Discovery - GPT-4)', fontsize=14, fontweight='bold')
            ax3.set_ylabel('')
            
            plt.tight_layout()
            plt.savefig('benchmark_charts/detailed_scores_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def create_execution_time_comparison(self, judge_results: List[Dict[str, Any]]):
        """Create execution time comparison chart"""
        successful_results = [r for r in judge_results if r["status"] == "success"]
        
        if not successful_results:
            return
        
        legal_times = [r.get("legal_execution_time", 0) for r in successful_results]
        gpt4_times = [r.get("gpt4_execution_time", 0) for r in successful_results]
        question_ids = [r["question_id"] for r in successful_results]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Scatter plot
        ax1.scatter(legal_times, gpt4_times, alpha=0.7, s=60, color='purple')
        
        # Add diagonal line (equal times)
        max_time = max(max(legal_times), max(gpt4_times))
        ax1.plot([0, max_time], [0, max_time], 'r--', alpha=0.5, label='Equal Time')
        
        ax1.set_xlabel('Legal Discovery Execution Time (seconds)', fontsize=12)
        ax1.set_ylabel('GPT-4 Execution Time (seconds)', fontsize=12)
        ax1.set_title('Execution Time Comparison', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(alpha=0.3)
        
        # Box plot
        ax2.boxplot([legal_times, gpt4_times], labels=['Legal Discovery', 'GPT-4'])
        ax2.set_ylabel('Execution Time (seconds)', fontsize=12)
        ax2.set_title('Execution Time Distribution', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('benchmark_charts/execution_times.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_summary_dashboard(self, analysis: Dict[str, Any]):
        """Create a comprehensive summary dashboard"""
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Legal Discovery System vs GPT-4 Benchmark Results', 
                    fontsize=20, fontweight='bold', y=0.95)
        
        # Key metrics text
        ax_text = fig.add_subplot(gs[0, :])
        ax_text.axis('off')
        
        total_questions = analysis.get('total_judgments', 0)
        legal_wins = analysis.get('legal_discovery_wins', 0)
        gpt4_wins = analysis.get('gpt4_wins', 0)
        ties = analysis.get('ties', 0)
        legal_score = analysis.get('average_legal_score', 0)
        gpt4_score = analysis.get('average_gpt4_score', 0)
        
        summary_text = f"""
BENCHMARK SUMMARY
Total Questions Evaluated: {total_questions}
Legal Discovery System: {legal_wins} wins ({legal_wins/total_questions*100:.1f}%) | Avg Score: {legal_score:.1f}/100
GPT-4 Direct: {gpt4_wins} wins ({gpt4_wins/total_questions*100:.1f}%) | Avg Score: {gpt4_score:.1f}/100
Ties: {ties} ({ties/total_questions*100:.1f}%)
        """
        
        ax_text.text(0.5, 0.5, summary_text, ha='center', va='center', fontsize=14,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
        
        # Win rate pie chart
        ax1 = fig.add_subplot(gs[1, 0])
        sizes = [legal_wins, gpt4_wins, ties]
        labels = ['Legal Discovery', 'GPT-4', 'Ties']
        colors = ['#2E8B57', '#4169E1', '#FFD700']
        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Win Distribution', fontweight='bold')
        
        # Score comparison
        ax2 = fig.add_subplot(gs[1, 1])
        systems = ['Legal\nDiscovery', 'GPT-4']
        scores = [legal_score, gpt4_score]
        bars = ax2.bar(systems, scores, color=['#2E8B57', '#4169E1'], alpha=0.8)
        ax2.set_ylabel('Average Score')
        ax2.set_title('Quality Scores', fontweight='bold')
        ax2.set_ylim(0, 100)
        for bar, score in zip(bars, scores):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{score:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Performance by complexity (if available)
        ax3 = fig.add_subplot(gs[1, 2])
        wins_by_complexity = analysis.get('wins_by_complexity', {})
        if wins_by_complexity:
            complexities = list(wins_by_complexity.keys())
            legal_wins_comp = [wins_by_complexity[comp].get('legal_discovery', 0) for comp in complexities]
            gpt4_wins_comp = [wins_by_complexity[comp].get('gpt4', 0) for comp in complexities]
            
            x = np.arange(len(complexities))
            width = 0.35
            ax3.bar(x - width/2, legal_wins_comp, width, label='Legal Discovery', color='#2E8B57', alpha=0.8)
            ax3.bar(x + width/2, gpt4_wins_comp, width, label='GPT-4', color='#4169E1', alpha=0.8)
            ax3.set_xlabel('Complexity')
            ax3.set_ylabel('Wins')
            ax3.set_title('Performance by Complexity', fontweight='bold')
            ax3.set_xticks(x)
            ax3.set_xticklabels([c.title() for c in complexities])
            ax3.legend()
        
        # Timestamp
        ax_footer = fig.add_subplot(gs[2, :])
        ax_footer.axis('off')
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ax_footer.text(0.5, 0.5, f"Generated on: {timestamp}", ha='center', va='center', 
                      fontsize=10, style='italic')
        
        plt.savefig('benchmark_charts/summary_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_all_charts(self):
        """Generate all visualization charts"""
        try:
            analysis, judge_results = self.load_data()
            
            print("Creating benchmark visualizations...")
            
            # Generate individual charts
            self.create_win_rate_chart(analysis)
            print("✓ Win rate chart created")
            
            self.create_score_comparison(analysis)
            print("✓ Score comparison chart created")
            
            self.create_category_breakdown(analysis)
            print("✓ Category breakdown chart created")
            
            self.create_detailed_scores_heatmap(judge_results)
            print("✓ Detailed scores heatmap created")
            
            self.create_execution_time_comparison(judge_results)
            print("✓ Execution time comparison created")
            
            self.create_summary_dashboard(analysis)
            print("✓ Summary dashboard created")
            
            print(f"\nAll charts saved to 'benchmark_charts/' directory")
            
        except FileNotFoundError as e:
            print(f"Error: Could not find required files. Please run the benchmark and judge first. {e}")
        except Exception as e:
            print(f"Error creating visualizations: {e}")


def main():
    """Main execution function"""
    visualizer = BenchmarkVisualizer()
    visualizer.generate_all_charts()


if __name__ == "__main__":
    main() 