from typing import TypedDict, Annotated, List, Literal
import operator

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from open_deep_research.configuration import Configuration
from open_deep_research.utils import (
    get_config_value, 
    search_documents_with_azure_ai
)

from pydantic import BaseModel, Field

# State definition for the deposition agent
class DepositionAgentState(TypedDict):
    case_background: str
    current_research_phase: str  # For progress display
    
    # Simplified tracking
    all_search_results: List[str]  # All search results (set once, not accumulated)
    key_topics: List[str]  # LLM-identified key topics  
    exhausted_topics: Annotated[List[str], operator.add]
    
    # Question generation
    topic_questions: Annotated[List[dict], operator.add]  # Questions per topic
    final_questions: List[dict]  # Organized final output
    
    # Progress reporting (like Manus)
    progress_log: Annotated[List[str], operator.add]
    current_status: str

# Input/Output schemas
class DepositionAgentInput(BaseModel):
    case_background: str = Field(description="Background information about the legal case")

class DepositionAgentOutput(BaseModel):
    final_questions: List[dict] = Field(description="Organized deposition questions with sources")
    case_summary: str = Field(description="Summary of the case background")
    total_questions: int = Field(description="Total number of questions generated")
    question_topics: int = Field(description="Number of topics covered")

# Structured output schemas for LLM responses
class InitialQueries(BaseModel):
    queries: List[str] = Field(description="List of initial research queries")

class KeyTopics(BaseModel):
    topics: List[str] = Field(description="List of 3-5 key topics for deposition questioning")

class TopicQuestions(BaseModel):
    questions: List[str] = Field(description="List of deposition questions for this topic")

class FollowUpQueries(BaseModel):
    queries: List[str] = Field(description="List of follow-up search queries to find more evidence")
    needs_more_search: bool = Field(description="Whether more searching is needed for this topic")

# Simplified helper functions

async def identify_key_topics_with_llm(all_search_results: List[str], case_background: str, config) -> List[str]:
    """Use LLM to analyze all search results and identify 3-5 key topics for deposition questioning"""
    
    if not all_search_results:
        return []
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Format search results for LLM analysis (limit to avoid token limits)
    results_sample = all_search_results[:20]  # Take first 20 results
    results_text = "\n\n".join([f"Result {i+1}: {result[:300]}..." for i, result in enumerate(results_sample)])
    
    topic_identification_prompt = f"""You are an expert litigation attorney analyzing search results to identify key topics for deposition questioning.

Case Background: {case_background}

Search Results from Document Review:
{results_text}

Based on these search results, identify 3-5 key topics that would be most valuable for deposition questioning. Focus on topics that:
- Have multiple pieces of evidence or documentation
- Show potential contradictions or inconsistencies  
- Involve witness knowledge, actions, or credibility
- Could lead to admissions or impeachment
- Are central to the case's key disputes

For each topic, provide a clear, concise name (2-4 words) that captures the deposition focus area."""

    try:
        structured_llm = writer_model.with_structured_output(KeyTopics)
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who identifies key deposition topics from evidence."),
            HumanMessage(content=topic_identification_prompt)
        ])
        
        return result.topics[:5]  # Limit to max 5 topics
        
    except Exception as e:
        print(f"Error in topic identification: {e}")
        # Fallback to simple topics
        return ["Witness Knowledge", "Document Awareness", "Timeline Issues"]

async def exhaust_search_on_topic_simple(topic: str, config) -> List[str]:
    """Exhaustively search for all evidence related to a specific topic"""
    
    # Generate expanded search queries for this specific topic
    search_queries = [
        f"All documents related to {topic}",
        f"Timeline of events involving {topic}",
        f"Communications about {topic}",
        f"Evidence contradicting {topic}",
        f"Witness statements about {topic}"
    ]
    
    all_evidence = []
    for query in search_queries:
        results = await search_documents_with_azure_ai([query], config)
        print(f"🔍 {query} found results")
        print(f"results: {results}")
        # Results is always a string, so append it as one item
        all_evidence.append(results)
    
    # Remove duplicates
    all_evidence = ["\n".join(all_evidence)]
    print(f"🔍 all_evidence: {all_evidence}")
    print(f"🔍 all_evidence length: {len(all_evidence)}")
    return all_evidence

async def adaptive_search_on_topic(topic: str, case_background: str, config) -> List[str]:
    """Iteratively search for evidence on a topic, generating new search queries based on findings"""
    
    # Get configuration for LLM
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    all_evidence = []
    search_round = 0
    max_rounds = 3  # Limit iterations to prevent infinite loops
    
    # Initial search queries
    current_queries = [
        f"All documents related to {topic}",
        f"Timeline of events involving {topic}",
        f"Communications about {topic}",
        f"Evidence contradicting {topic}",
        f"Witness statements about {topic}"
    ]
    
    while search_round < max_rounds:
        search_round += 1
        print(f"🔍 Search Round {search_round} for topic: {topic}")
        
        # Execute current search queries
        round_evidence = []
        for query in current_queries:
            results = await search_documents_with_azure_ai([query], configurable)
            # Results is always a string, so append it as one item
            round_evidence.append(results)
            print(f"   🔍 '{query}' found results")
        
        # Add to total evidence
        all_evidence.extend(round_evidence)
        
        # If this is the final round, stop
        if search_round >= max_rounds:
            break
            
        # Use LLM to analyze current evidence and determine if more searching is needed
        evidence_sample = round_evidence  # Sample recent findings
        
        follow_up_prompt = f"""You are an expert litigation attorney analyzing evidence for deposition preparation.

Case Background: {case_background}
Current Topic: {topic}
Current Search Round: {search_round}

Recent Evidence Found:
{evidence_sample}

Based on the evidence found so far, determine:
1. Do we need to search for more evidence on this topic?
2. If yes, what specific search queries would help find additional relevant evidence?

Focus on identifying:
- Gaps in the evidence that need to be filled
- Related people, documents, or events mentioned that need investigation
- Contradictions that need more evidence to explore
- Timeline gaps that need clarification

Generate 3-5 specific follow-up search queries if more searching is needed."""

        try:
            structured_llm = writer_model.with_structured_output(FollowUpQueries)
            
            follow_up_result = await structured_llm.ainvoke([
                SystemMessage(content="You are an expert litigation attorney who determines what additional evidence is needed for deposition preparation."),
                HumanMessage(content=follow_up_prompt)
            ])
            
            if not follow_up_result.needs_more_search:
                print(f"   ✅ LLM determined sufficient evidence found for {topic}")
                break
                
            current_queries = follow_up_result.queries
            print(f"   🎯 Generated {len(current_queries)} follow-up queries for next round")
            
        except Exception as e:
            print(f"   ⚠️ Error in follow-up analysis: {e}")
            break  # Stop if LLM fails
    
    
    print(f"🔍 Adaptive search completed for {topic}: {len(all_evidence)} unique pieces of evidence across {search_round} rounds")
    
    return all_evidence

async def generate_questions_with_llm(topic: str, evidence: List[str], case_background: str, config) -> List[str]:
    """Generate deposition questions using LLM based on complete evidence for a topic"""
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )

    evidence_context = evidence
    
    question_prompt = f"""You are an expert litigation attorney generating strategic deposition questions.

Case Background: {case_background}
Topic: {topic}

Evidence Found:
{evidence_context}

Generate 5-8 strategic deposition questions for this topic that:
1. Establish foundation and knowledge
2. Explore contradictions or inconsistencies 
3. Pin down specific facts and timeline
4. Confront the witness with evidence
5. Impeach if appropriate

Focus on questions that use the specific evidence found. Make them precise and tactical. Reference specific documents, dates, names, and facts from the evidence above."""

    try:
        structured_llm = writer_model.with_structured_output(TopicQuestions)
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who generates strategic deposition questions based on specific evidence."),
            HumanMessage(content=question_prompt)
        ])
        
        return result.questions
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Fallback simple questions
        return [
            f"What is your knowledge of {topic}?",
            f"Can you explain the circumstances surrounding {topic}?",
            f"Are you aware of any documents related to {topic}?",
            f"Did you have any communications about {topic}?",
            f"Is your testimony regarding {topic} consistent with the evidence?"
        ]

# Main nodes

async def initial_research(state: DepositionAgentState, config: RunnableConfig):
    """Broad exploration of case background to identify key topics for deposition questioning"""
    
    case_background = state["case_background"]
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    
    # Set up LLM for generating initial queries
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Progress update
    progress_update = "Starting comprehensive case analysis to identify key areas for deposition questioning."
    
    # Generate initial research queries using LLM
    query_generation_prompt = f"""Based on the following case background, generate 5-7 strategic research queries that would help identify the most important areas for deposition questioning.

Case Background: {case_background}

Focus on queries that would help discover:
- Key factual disputes and inconsistencies
- Important witnesses and their potential credibility issues
- Critical documents and evidence
- Timeline inconsistencies or contradictions
- Areas where witnesses might be vulnerable to impeachment
- Potential smoking gun evidence

Generate specific, targeted search queries that would uncover evidence useful for depositions."""

    structured_llm = writer_model.with_structured_output(InitialQueries)
    
    initial_queries_result = await structured_llm.ainvoke([
        SystemMessage(content="You are an expert litigation attorney who generates strategic research queries for deposition preparation."),
        HumanMessage(content=query_generation_prompt)
    ])
    
    initial_queries = initial_queries_result.queries
    
    print(f"🎯 Generated {len(initial_queries)} initial research queries")
    for i, query in enumerate(initial_queries, 1):
        print(f"   {i}. {query}")
    
    # Search documents with each query and collect ALL results
    all_search_results = []
    for query in initial_queries:
        results = await search_documents_with_azure_ai([query], configurable)
        # Results is always a string, so append it as one item
        all_search_results.append(results)
    
    print(f"📊 Collected {len(all_search_results)} total search results")
    
    # Use LLM to identify key topics from all search results
    key_topics = await identify_key_topics_with_llm(all_search_results, case_background, config)
    
    print(f"🎯 Identified {len(key_topics)} key topics for deposition questioning:")
    for i, topic in enumerate(key_topics, 1):
        print(f"   {i}. {topic}")
    
    return {
        "all_search_results": all_search_results,
        "key_topics": key_topics,
        "current_research_phase": "discovery_loop" if key_topics else "compilation",
        "progress_log": [progress_update],
        "current_status": f"Identified {len(key_topics)} key topics for deposition questioning."
    }

async def discovery_loop(state: DepositionAgentState, config: RunnableConfig):
    """Process each key topic: exhaust search and generate deposition questions"""
    
    # Get next unprocessed topic (simple sequential processing)
    key_topics = state["key_topics"]
    exhausted_topics = state["exhausted_topics"]
    
    # Find next topic to process
    unprocessed_topics = [topic for topic in key_topics if topic not in exhausted_topics]
    
    if not unprocessed_topics:
        # No more topics to process - move to compilation
        return {
            "current_research_phase": "compilation",
            "progress_log": ["Completed deep research on all key topics. Moving to question compilation."],
            "current_status": f"Research complete. Organizing {len(state['topic_questions'])} question sets into final deposition outline."
        }
    
    # Process the next topic (first in list)
    current_topic = unprocessed_topics[0]
    
    # Progress update
    progress_update = f"Deep diving into '{current_topic}' - searching for all related evidence and generating questions."
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    
    # EXHAUST SEARCH on this specific topic
    complete_evidence = await adaptive_search_on_topic(current_topic, state["case_background"], config)
    
    print(f"🔍 Found {len(complete_evidence)} pieces of evidence for topic: {current_topic}")
    
    # Generate questions based on COMPLETE evidence using LLM
    topic_questions = await generate_questions_with_llm(
        current_topic, 
        complete_evidence, 
        state["case_background"],
        config
    )
    
    return {
        "exhausted_topics": [current_topic],
        "topic_questions": [{
            "topic": current_topic,
            "questions": topic_questions,
            "evidence_sources": complete_evidence
        }],
        "progress_log": [progress_update],
        "current_status": f"Generated {len(topic_questions)} questions for '{current_topic}'. Continuing research on remaining topics."
    }

async def final_compilation(state: DepositionAgentState, config: RunnableConfig):
    """Organize and order all questions into logical deposition flow"""
    
    all_topic_questions = state["topic_questions"]
    case_background = state["case_background"]
    
    # Progress update
    progress_update = "Organizing all questions into strategic deposition sequence with source citations."
    
    # Simple organization by topic - no complex logic
    organized_questions = []
    for topic_set in all_topic_questions:
        organized_questions.append({
            "topic": topic_set["topic"],
            "questions": topic_set["questions"],
            "question_count": len(topic_set["questions"]),
            "evidence_count": len(topic_set.get("evidence_sources", []))
        })
    
    # Calculate totals
    total_questions = sum(len(tq["questions"]) for tq in all_topic_questions)
    
    return {
        "final_questions": organized_questions,
        "progress_log": [progress_update],
        "current_status": f"Deposition outline complete! Generated {total_questions} strategic questions across {len(all_topic_questions)} key topics."
    }

# Graph construction

# Create the graph
deposition_agent = StateGraph(
    DepositionAgentState, 
    input=DepositionAgentInput, 
    output=DepositionAgentOutput,
    config_schema=Configuration
)

# Add nodes
deposition_agent.add_node("initial_research", initial_research)
deposition_agent.add_node("discovery_loop", discovery_loop) 
deposition_agent.add_node("final_compilation", final_compilation)

# Add edges
deposition_agent.add_edge(START, "initial_research")

# Conditional edge from initial_research
deposition_agent.add_conditional_edges(
    "initial_research",
    lambda state: state["current_research_phase"],
    {
        "discovery_loop": "discovery_loop",
        "compilation": "final_compilation"  # If no findings
    }
)

# Self-loop for discovery until exhausted
deposition_agent.add_conditional_edges(
    "discovery_loop", 
    lambda state: state["current_research_phase"],
    {
        "discovery_loop": "discovery_loop",  # Continue processing
        "compilation": "final_compilation"   # Done with discovery
    }
)

deposition_agent.add_edge("final_compilation", END)

# Compile the graph
deposition_graph = deposition_agent.compile()

# Utility function for running with progress display
async def run_deposition_agent_with_display(case_background: str, config: RunnableConfig):
    """Run the agent with real-time progress display like Manus"""
    
    input_data = {"case_background": case_background}
    
    print("🎯 Deposition Question Generator")
    print("=" * 50)
    print(f"Case: {case_background[:100]}...")
    print()
    
    final_result = None
    
    # Stream the execution
    async for chunk in deposition_graph.astream(input_data, config):
        for node_name, node_output in chunk.items():
            if "progress_log" in node_output:
                for progress in node_output["progress_log"]:
                    print(f"🔍 {progress}")
            
            if "current_status" in node_output:
                print(f"📊 {node_output['current_status']}")
                print()
            
            if "final_questions" in node_output:
                final_result = node_output["final_questions"]
    
    return final_result 