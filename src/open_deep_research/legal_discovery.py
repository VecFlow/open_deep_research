from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langgraph.types import interrupt, Command

from open_deep_research.legal_state import (
    LegalAnalysisInput,
    LegalAnalysisOutput,
    AnalysisCategories,
    LegalAnalysisState,
    CategoryState,
    CategoryOutputState,
    DocumentQueries,
    CategoryFeedback,
    DepositionQuestions
)

from open_deep_research.legal_prompts import (
    case_analyzer_query_writer_instructions,
    case_analysis_planner_instructions,
    document_query_writer_instructions, 
    category_analyzer_instructions,
    final_category_analyzer_instructions,
    category_grader_instructions,
    deposition_question_generator_instructions,
    category_analyzer_inputs
)

from open_deep_research.configuration import Configuration
from open_deep_research.utils import (
    format_categories, 
    get_config_value, 
    search_documents_with_azure_ai
)

## Nodes -- 

async def generate_analysis_plan(state: LegalAnalysisState, config: RunnableConfig):
    """Generate the initial legal analysis plan with categories.
    
    This node:
    1. Gets configuration for the analysis structure
    2. Generates document queries to gather context for planning
    3. Searches through legal documents using those queries
    4. Uses an LLM to generate a structured analysis plan with categories
    
    Args:
        state: Current graph state containing the case background
        config: Configuration for models, document search, etc.
        
    Returns:
        Dict containing the generated analysis categories
    """

    # Inputs
    background_on_case = state["background_on_case"]

    # Get list of feedback on the analysis plan
    feedback_list = state.get("feedback_on_analysis_plan", [])

    # Concatenate feedback on the analysis plan into a single string
    feedback = " /// ".join(feedback_list) if feedback_list else ""

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    analysis_structure = configurable.analysis_structure or "liability analysis, damages assessment, key witnesses, timeline of events, document evidence, deposition strategy"
    number_of_queries = configurable.number_of_queries
    
    # Set writer model (model used for query writing)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    structured_llm = writer_model.with_structured_output(DocumentQueries)

    # Format system instructions
    system_instructions_query = case_analyzer_query_writer_instructions.format(
        background_on_case=background_on_case, 
        analysis_structure=analysis_structure, 
        number_of_queries=number_of_queries
    )

    # Generate queries  
    results = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="Generate document search queries that will help with planning the legal analysis categories.")
    ])

    # Document search
    query_list = [query.search_query for query in results.queries]

    # Search documents using Azure AI Search
    source_docs = await search_documents_with_azure_ai(query_list, configurable)

    # Format system instructions
    system_instructions_categories = case_analysis_planner_instructions.format(
        background_on_case=background_on_case, 
        analysis_structure=analysis_structure, 
        context=source_docs, 
        feedback=feedback
    )

    # Set the planner
    planner_provider = get_config_value(configurable.planner_provider)
    planner_model = get_config_value(configurable.planner_model)
    planner_model_kwargs = get_config_value(configurable.planner_model_kwargs or {})

    # Analysis planner instructions
    planner_message = """Generate the categories for legal analysis. Your response must include a 'categories' field containing a list of analysis categories. 
                        Each category must have: name, description, requires_document_search, and content fields."""

    # Run the planner
    if planner_model in ["claude-3-5-sonnet-latest", "claude-4-sonnet"]:
        # Allocate a thinking budget for claude-3-5-sonnet-latest and claude-4-sonnet as the planner model
        planner_llm = init_chat_model(model=planner_model, 
                                      model_provider=planner_provider, 
                                      max_tokens=20_000, 
                                      thinking={"type": "enabled", "budget_tokens": 16_000})

    else:
        # With other models, thinking tokens are not specifically allocated
        planner_llm = init_chat_model(model=planner_model, 
                                      model_provider=planner_provider,
                                      model_kwargs=planner_model_kwargs)
    
    # Generate the analysis categories
    structured_llm = planner_llm.with_structured_output(AnalysisCategories)
    analysis_categories = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions_categories),
        HumanMessage(content=planner_message)
    ])

    # Get categories
    categories = analysis_categories.categories

    return {"categories": categories}

def human_feedback(state: LegalAnalysisState, config: RunnableConfig) -> Command[Literal["generate_analysis_plan","analyze_category_with_documents"]]:
    """Get human feedback on the analysis plan and route to next steps.
    
    This node:
    1. Formats the current analysis plan for human review
    2. Gets feedback via an interrupt
    3. Routes to either:
       - Category analysis if plan is approved
       - Plan regeneration if feedback is provided
    
    Args:
        state: Current graph state with categories to review
        config: Configuration for the workflow
        
    Returns:
        Command to either regenerate plan or start category analysis
    """

    # Get categories
    background_on_case = state["background_on_case"]
    categories = state['categories']
    categories_str = "\n\n".join(
        f"Category: {category.name}\n"
        f"Description: {category.description}\n"
        f"Requires document search: {'Yes' if category.requires_document_search else 'No'}\n"
        for category in categories
    )

    # Get feedback on the analysis plan from interrupt
    interrupt_message = f"""Please provide feedback on the following legal analysis plan for the case. 
                        \n\n{categories_str}\n
                        \nDoes the analysis plan meet your needs for this litigation?\nPass 'true' to approve the analysis plan.\nOr, provide feedback to regenerate the analysis plan:"""
    
    feedback = interrupt(interrupt_message)

    # If the user approves the analysis plan, kick off category analysis
    if isinstance(feedback, bool) and feedback is True:
        # Treat this as approve and kick off category analysis
        return Command(goto=[
            Send("analyze_category_with_documents", {
                "background_on_case": background_on_case, 
                "category": c, 
                "search_iterations": 0
            }) 
            for c in categories 
            if c.requires_document_search
        ])
    
    # If the user provides feedback, regenerate the analysis plan 
    elif isinstance(feedback, str):
        # Treat this as feedback and append it to the existing list
        return Command(goto="generate_analysis_plan", 
                       update={"feedback_on_analysis_plan": [feedback]})
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")
    
async def generate_document_queries(state: CategoryState, config: RunnableConfig):
    """Generate document search queries for analyzing a specific category.
    
    This node uses an LLM to generate targeted search queries based on the 
    category topic and description for document discovery.
    
    Args:
        state: Current state containing category details
        config: Configuration including number of queries to generate
        
    Returns:
        Dict containing the generated document queries
    """

    # Get state 
    background_on_case = state["background_on_case"]
    category = state["category"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries

    # Generate queries 
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    structured_llm = writer_model.with_structured_output(DocumentQueries)

    # Format system instructions
    system_instructions = document_query_writer_instructions.format(
        background_on_case=background_on_case, 
        category_topic=category.description, 
        number_of_queries=number_of_queries
    )

    # Generate queries  
    queries = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate document search queries for this category of legal analysis.")
    ])

    return {"document_queries": queries.queries}

async def search_documents(state: CategoryState, config: RunnableConfig):
    """Execute document searches for the category queries.
    
    This node:
    1. Takes the generated queries
    2. Executes searches in Azure AI Search
    3. Formats results into usable context
    
    Args:
        state: Current state with document queries
        config: Document search configuration
        
    Returns:
        Dict with search results and updated iteration count
    """

    # Get state
    document_queries = state["document_queries"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Document search
    query_list = [query.search_query for query in document_queries]

    # Search documents using Azure AI Search
    source_docs = await search_documents_with_azure_ai(query_list, configurable)

    return {"source_docs": source_docs, "search_iterations": state["search_iterations"] + 1}

async def analyze_category(state: CategoryState, config: RunnableConfig) -> Command[Literal[END, "search_documents"]]:
    """Analyze a category of the legal case and evaluate if more research is needed.
    
    This node:
    1. Analyzes category content using document search results
    2. Evaluates the quality of the analysis
    3. Either:
       - Completes the category if quality passes
       - Triggers more document search if quality fails
    
    Args:
        state: Current state with search results and category info
        config: Configuration for analysis and evaluation
        
    Returns:
        Command to either complete category or do more research
    """

    # Get state 
    background_on_case = state["background_on_case"]
    category = state["category"]
    source_docs = state["source_docs"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Format system instructions
    category_analyzer_inputs_formatted = category_analyzer_inputs.format(
        background_on_case=background_on_case, 
        category_name=category.name, 
        category_topic=category.description, 
        context=source_docs, 
        category_content=category.content
    )

    # Generate analysis  
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 

    category_analysis = await writer_model.ainvoke([
        SystemMessage(content=category_analyzer_instructions),
        HumanMessage(content=category_analyzer_inputs_formatted)
    ])
    
    # Write content to the category object  
    category.content = category_analysis.content

    # Grade prompt 
    category_grader_message = ("Grade the analysis and consider follow-up queries for missing information. "
                              "If the grade is 'pass', return empty strings for all follow-up queries. "
                              "If the grade is 'fail', provide specific document search queries to gather missing information.")
    
    category_grader_instructions_formatted = category_grader_instructions.format(
        background_on_case=background_on_case, 
        category_topic=category.description,
        analysis=category.content, 
        number_of_follow_up_queries=configurable.number_of_queries
    )

    # Use planner model for reflection
    planner_provider = get_config_value(configurable.planner_provider)
    planner_model = get_config_value(configurable.planner_model)
    planner_model_kwargs = get_config_value(configurable.planner_model_kwargs or {})

    if planner_model in ["claude-3-5-sonnet-latest", "claude-4-sonnet"]:
        # Allocate a thinking budget for claude-3-5-sonnet-latest and claude-4-sonnet as the planner model
        reflection_model = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider, 
            max_tokens=20_000, 
            thinking={"type": "enabled", "budget_tokens": 16_000}
        ).with_structured_output(CategoryFeedback)
    else:
        reflection_model = init_chat_model(
            model=planner_model, 
            model_provider=planner_provider, 
            model_kwargs=planner_model_kwargs
        ).with_structured_output(CategoryFeedback)
    
    # Generate feedback
    feedback = await reflection_model.ainvoke([
        SystemMessage(content=category_grader_instructions_formatted),
        HumanMessage(content=category_grader_message)
    ])

    # If the category is passing or the max search depth is reached, publish the category to completed categories 
    if feedback.grade == "pass" or state["search_iterations"] >= configurable.max_search_depth:
        # Publish the category to completed categories 
        return Command(
            update={"completed_categories": [category]},
            goto=END
        )

    # Update the existing category with new content and update search queries
    else:
        return Command(
            update={"document_queries": feedback.follow_up_queries, "category": category},
            goto="search_documents"
        )
    
async def analyze_final_categories(state: CategoryState, config: RunnableConfig):
    """Analyze categories that don't require document search using completed categories as context.
    
    This node handles categories like overall case strategy or synthesis that build on
    the analyzed categories rather than requiring direct document search.
    
    Args:
        state: Current state with completed categories as context
        config: Configuration for the analysis model
        
    Returns:
        Dict containing the newly analyzed category
    """

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get state 
    background_on_case = state["background_on_case"]
    category = state["category"]
    completed_analysis_categories = state["analysis_categories_from_documents"]
    
    # Format system instructions
    system_instructions = final_category_analyzer_instructions.format(
        background_on_case=background_on_case, 
        category_name=category.name, 
        category_topic=category.description, 
        context=completed_analysis_categories
    )

    # Generate analysis  
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs) 
    
    category_analysis = await writer_model.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate analysis for this category based on the provided context.")
    ])
    
    # Write content to category 
    category.content = category_analysis.content

    # Write the updated category to completed categories
    return {"completed_categories": [category]}

async def generate_deposition_questions(state: LegalAnalysisState, config: RunnableConfig):
    """Generate deposition questions based on the completed legal analysis.
    
    This node:
    1. Takes all completed analysis categories
    2. Identifies key witnesses and areas of inquiry
    3. Generates strategic deposition questions
    
    Args:
        state: Current state with completed analysis
        config: Configuration for question generation
        
    Returns:
        Dict containing generated deposition questions
    """

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get state
    background_on_case = state["background_on_case"]
    completed_categories = state["completed_categories"]
    
    # Format completed categories for context
    analysis_context = format_categories(completed_categories)

    # Format system instructions
    system_instructions = deposition_question_generator_instructions.format(
        background_on_case=background_on_case,
        analysis_context=analysis_context
    )

    # Generate deposition questions
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider, model_kwargs=writer_model_kwargs)
    
    structured_llm = writer_model.with_structured_output(DepositionQuestions)
    
    deposition_questions = await structured_llm.ainvoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate strategic deposition questions based on the legal analysis.")
    ])

    return {"deposition_questions": deposition_questions}

def gather_completed_categories(state: LegalAnalysisState):
    """Format completed categories as context for writing final categories.
    
    This node takes all completed document-based analysis categories and formats them into
    a single context string for writing synthesis categories.
    
    Args:
        state: Current state with completed categories
        
    Returns:
        Dict with formatted categories as context
    """

    # List of completed categories
    completed_categories = state["completed_categories"]

    # Format completed categories to str to use as context for final categories
    completed_analysis_categories = format_categories(completed_categories)

    return {"analysis_categories_from_documents": completed_analysis_categories}

def compile_final_analysis(state: LegalAnalysisState):
    """Compile all categories and deposition questions into the final analysis.
    
    This node:
    1. Gets all completed categories
    2. Orders them according to original plan
    3. Adds deposition questions
    4. Combines them into the final legal analysis
    
    Args:
        state: Current state with all completed categories and questions
        
    Returns:
        Dict containing the complete legal analysis
    """

    # Get categories
    categories = state["categories"]
    completed_categories = {c.name: c.content for c in state["completed_categories"]}
    deposition_questions = state["deposition_questions"]

    # Update categories with completed content while maintaining original order
    for category in categories:
        category.content = completed_categories[category.name]

    # Compile final analysis
    all_categories = "\n\n".join([f"## {c.name}\n\n{c.content}" for c in categories])
    
    # Format deposition questions
    questions_section = "\n\n## Deposition Questions\n\n"
    for witness_questions in deposition_questions.witness_questions:
        questions_section += f"### {witness_questions.witness_name}\n\n"
        questions_section += f"**Role/Relevance:** {witness_questions.witness_role}\n\n"
        questions_section += "**Questions:**\n"
        for i, q in enumerate(witness_questions.questions, 1):
            questions_section += f"{i}. {q.question}\n"
            questions_section += f"   - *Purpose:* {q.purpose}\n"
            questions_section += f"   - *Expected areas:* {', '.join(q.expected_areas)}\n\n"

    final_analysis = f"# Legal Analysis: {state['background_on_case'][:100]}...\n\n{all_categories}{questions_section}"

    return {"final_analysis": final_analysis}

def initiate_final_category_analysis(state: LegalAnalysisState):
    """Create parallel tasks for analyzing non-document categories.
    
    This edge function identifies categories that don't need document search and
    creates parallel analysis tasks for each one.
    
    Args:
        state: Current state with all categories and document analysis context
        
    Returns:
        List of Send commands for parallel category analysis
    """

    # Kick off category analysis in parallel via Send() API for any categories that do not require document search
    return [
        Send("analyze_final_categories", {
            "background_on_case": state["background_on_case"], 
            "category": c, 
            "analysis_categories_from_documents": state["analysis_categories_from_documents"]
        }) 
        for c in state["categories"] 
        if not c.requires_document_search
    ]

# Legal analysis category sub-graph -- 

# Add nodes 
category_analyzer = StateGraph(CategoryState, output=CategoryOutputState)
category_analyzer.add_node("generate_document_queries", generate_document_queries)
category_analyzer.add_node("search_documents", search_documents)
category_analyzer.add_node("analyze_category", analyze_category)

# Add edges
category_analyzer.add_edge(START, "generate_document_queries")
category_analyzer.add_edge("generate_document_queries", "search_documents")
category_analyzer.add_edge("search_documents", "analyze_category")

# Outer graph for initial analysis plan compiling results from each category -- 

# Add nodes
builder = StateGraph(LegalAnalysisState, input=LegalAnalysisInput, output=LegalAnalysisOutput, config_schema=Configuration)
builder.add_node("generate_analysis_plan", generate_analysis_plan)
builder.add_node("human_feedback", human_feedback)
builder.add_node("analyze_category_with_documents", category_analyzer.compile())
builder.add_node("gather_completed_categories", gather_completed_categories)
builder.add_node("analyze_final_categories", analyze_final_categories)
builder.add_node("generate_deposition_questions", generate_deposition_questions)
builder.add_node("compile_final_analysis", compile_final_analysis)

# Add edges
builder.add_edge(START, "generate_analysis_plan")
builder.add_edge("generate_analysis_plan", "human_feedback")
builder.add_edge("analyze_category_with_documents", "gather_completed_categories")
builder.add_conditional_edges("gather_completed_categories", initiate_final_category_analysis, ["analyze_final_categories"])
builder.add_edge("analyze_final_categories", "generate_deposition_questions")
builder.add_edge("generate_deposition_questions", "compile_final_analysis")
builder.add_edge("compile_final_analysis", END)

legal_graph = builder.compile() 