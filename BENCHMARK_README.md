# Legal Discovery System Benchmark Suite

A comprehensive benchmark system to compare the Legal Discovery System against GPT-4 direct responses. This MVP benchmark suite provides objective evaluation across multiple legal analysis dimensions.

## 🎯 Purpose

This benchmark system:
- Runs your Legal Discovery system on a set of legal questions
- Runs GPT-4 directly on the same questions
- Uses an LLM judge to compare results objectively
- Generates detailed visualizations and reports

## 📋 Prerequisites

1. **OpenAI API Key**: Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Python Dependencies**: Install required packages:
   ```bash
   pip install -r requirements_benchmark.txt
   ```

3. **Legal Discovery System**: Ensure your legal discovery system is properly set up and configured.

## 🏗️ System Architecture

The benchmark suite consists of several components:

### Core Files

- **`benchmark_questions.csv`** - Set of diverse legal questions for testing
- **`run_benchmark.py`** - Main orchestrator script
- **`legal_discovery_runner.py`** - Runs your legal discovery system
- **`gpt4_runner.py`** - Runs GPT-4 for comparison
- **`llm_judge.py`** - LLM judge for objective comparison
- **`visualizer.py`** - Creates charts and graphs

### Evaluation Criteria

The LLM judge evaluates both systems on:

1. **Comprehensiveness** (25 points) - Coverage of relevant legal issues
2. **Accuracy** (25 points) - Legal correctness and soundness
3. **Practical Utility** (25 points) - Actionability for attorneys
4. **Organization & Clarity** (15 points) - Structure and readability
5. **Specificity** (10 points) - Concrete vs. general guidance

## 🚀 Quick Start

### Basic Usage

Run the complete benchmark suite:

```bash
python run_benchmark.py
```

This will:
1. Run Legal Discovery system on all questions
2. Run GPT-4 on the same questions
3. Judge all comparisons
4. Generate visualizations and reports

### Advanced Usage

Skip specific phases:

```bash
# Skip legal discovery (use existing results)
python run_benchmark.py --skip-legal

# Skip GPT-4 benchmark
python run_benchmark.py --skip-gpt4

# Skip LLM judge
python run_benchmark.py --skip-judge

# Only generate visualizations
python run_benchmark.py --only-viz
```

## 📊 Generated Outputs

After running the benchmark, you'll get:

### JSON Results
- `legal_discovery_results.json` - Raw Legal Discovery system results
- `gpt4_results.json` - Raw GPT-4 results
- `judge_results.json` - Detailed LLM judge evaluations
- `benchmark_analysis.json` - Statistical analysis summary

### Visualizations
All charts are saved to `benchmark_charts/`:
- `win_rates.png` - Overall win rate comparison
- `score_comparison.png` - Quality score comparison
- `category_breakdown.png` - Performance by question type/complexity
- `detailed_scores_heatmap.png` - Criterion-by-criterion scores
- `execution_times.png` - Performance timing comparison
- `summary_dashboard.png` - Comprehensive overview

### Reports
- `benchmark_report.md` - Final comprehensive report

## 🔧 Customization

### Adding Questions

Edit `benchmark_questions.csv` to add more test cases:

```csv
question_id,question,question_type,complexity,expected_focus
11,"Your new legal question here","custom_type","medium","key legal areas"
```

### Modifying Evaluation Criteria

Edit the `judge_prompt` in `llm_judge.py` to adjust scoring criteria or add new dimensions.

### Changing Models

Edit configuration in `legal_discovery_runner.py` and `gpt4_runner.py` to use different models:

```python
# In legal_discovery_runner.py
config = {
    "configurable": {
        "planner_provider": "anthropic",  # Change provider
        "planner_model": "claude-3-sonnet",  # Change model
        # ... other settings
    }
}
```

## 📈 Interpreting Results

### Win Rates
- Shows which system won more head-to-head comparisons
- Includes ties when both systems perform similarly

### Quality Scores
- Average scores out of 100 across all evaluation criteria
- Shows performance gap between systems

### Category Analysis
- Performance breakdown by question type (liability, discovery, etc.)
- Performance by complexity level (low, medium, high)

### Detailed Metrics
- Criterion-by-criterion comparison
- Execution time analysis
- Success rates and error analysis

## 🛠️ Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: OPENAI_API_KEY not found
   ```
   Solution: Set your OpenAI API key environment variable

2. **Missing Dependencies**
   ```
   ModuleNotFoundError: No module named 'matplotlib'
   ```
   Solution: Install requirements: `pip install -r requirements_benchmark.txt`

3. **Legal Discovery System Errors**
   - Check that your legal discovery system is properly configured
   - Verify database connections and API endpoints
   - Review error messages in the results JSON

4. **Rate Limits**
   - The system includes built-in delays to avoid rate limits
   - For heavy usage, consider upgrading your OpenAI plan

### Debug Mode

For debugging, run individual components:

```bash
# Test legal discovery only
python legal_discovery_runner.py

# Test GPT-4 only  
python gpt4_runner.py

# Test judge only (requires existing results)
python llm_judge.py

# Test visualizations only
python visualizer.py
```

## 📝 Example Questions

The benchmark includes diverse legal scenarios:

- **Liability Analysis**: Slip and fall, negligence cases
- **Discovery Strategy**: Document preservation, witness identification
- **Damages Assessment**: Product liability, economic losses
- **Procedural Issues**: Statute of limitations, jurisdiction
- **Expert Witnesses**: Patent disputes, medical malpractice
- **Defense Analysis**: Comparative negligence, affirmative defenses

## 🎯 Use Cases

### For Development Teams
- Validate improvements to the legal discovery system
- Identify strengths and weaknesses
- Track performance over time

### For Legal Professionals
- Understand system capabilities
- Make informed adoption decisions
- Identify areas for human oversight

### For Researchers
- Study AI system performance in legal domains
- Compare different approaches to legal analysis
- Develop better evaluation methodologies

## 🚧 Limitations (MVP Version)

- Limited to 10 sample questions (easily expandable)
- Single judge model (could use multiple judges)
- English language only
- No specialized legal domain focus
- Static question set (no adaptive testing)

## 🔮 Future Enhancements

- **Multi-judge evaluation** for more robust scoring
- **Domain-specific question sets** (contracts, litigation, etc.)
- **Real case integration** with actual legal documents
- **Human expert validation** of judge decisions
- **Performance tracking** over time
- **A/B testing** capabilities
- **Custom evaluation metrics** for specific use cases

## 📄 License

This benchmark system is provided as-is for evaluation purposes. Please ensure compliance with your legal discovery system's license and OpenAI's usage policies.

## 🤝 Contributing

To improve the benchmark system:

1. Add more diverse legal questions
2. Enhance evaluation criteria
3. Improve visualizations
4. Add new comparison dimensions
5. Optimize performance and reliability

---

**Note**: This is an MVP benchmark system designed to provide initial comparison capabilities. Results should be interpreted in context and used to guide further development and evaluation. 