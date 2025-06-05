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

# Simplified unified thinking structure
class Thinking(BaseModel):
    what_i_found: str  # Specific evidence pieces analyzed
    insight: str  # What this evidence reveals (contradictions, gaps, smoking guns)
    reasoning: str  # Why this matters for deposition strategy
    confidence: float  # 0-1 based on evidence strength
    strategic_value: str  # How devastating this could be
    next_focus: str  # What to investigate next and why

# Simplified state for intelligent agent
class DepositionAgentState(TypedDict):
    case_background: str
    
    # AI's actual thinking and discoveries
    thinking_log: Annotated[List[Thinking], operator.add]
    current_investigation: str  # What AI is currently investigating and why
    
    # Evidence and insights the AI has actually found
    evidence_gathered: Annotated[List[str], operator.add]  # All evidence found
    key_insights: Annotated[List[str], operator.add]  # Actual discoveries made
    
    # AI decision making and rounds tracking
    next_action: Literal["investigate_deeper", "switch_focus", "generate_questions"]
    research_assessment: str  # AI's evaluation of research completeness
    question_readiness: bool  # AI decides if ready to generate questions
    research_rounds: int  # Track how many research rounds completed
    max_rounds: int  # Maximum research rounds allowed
    
    # Final output
    final_questions: List[dict]

# Input/Output schemas (simplified)
class DepositionAgentInput(BaseModel):
    case_background: str = Field(description="Background information about the legal case")

class DepositionAgentOutput(BaseModel):
    final_questions: List[dict] = Field(description="Organized deposition questions with insights")
    key_insights: List[str] = Field(description="Key discoveries made during investigation")
    total_questions: int = Field(description="Total number of questions generated")

# Simplified LLM response schemas
class InvestigationPlan(BaseModel):
    search_queries: List[str] = Field(description="Specific searches to conduct")
    investigation_focus: str = Field(description="What to investigate and why")

class EvidenceAnalysis(BaseModel):
    thinking: Thinking = Field(description="AI's analysis of the evidence")
    high_value_leads: List[str] = Field(description="Specific leads to follow up on")

class NextActionDecision(BaseModel):
    next_action: Literal["investigate_deeper", "switch_focus", "generate_questions"]
    reasoning: str = Field(description="Why this action was chosen")
    investigation_target: str = Field(description="What to investigate next if continuing research")
    readiness_assessment: str = Field(description="Assessment of whether ready for questions")

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

# Simplified Graph Construction

def route_by_ai_decision(state: DepositionAgentState) -> str:
    """Route based on AI's decision about what to do next"""
    next_action = state.get("next_action", "investigate_deeper")
    question_ready = state.get("question_readiness", False)
    research_rounds = state.get("research_rounds", 0)
    max_rounds = state.get("max_rounds", 10)
    
    # AI decides the routing - prioritize question readiness
    if question_ready:
        return "generate_questions"
    elif next_action == "generate_questions":
        return "continue_research"
    else:
        return "continue_research"  # Either investigate_deeper or switch_focus



# Enhanced utility function for running with intelligent progress display
async def run_intelligent_deposition_agent(case_background: str, config: RunnableConfig):
    """Run the intelligent agent with real-time thinking display"""
    
    input_data = {"case_background": case_background}
    
    final_result = None
    
    # Stream the execution and show AI thinking
    async for chunk in deposition_graph.astream(input_data, config):
        for node_name, node_output in chunk.items():
            
            # Show research progress
            if "research_rounds" in node_output:
                rounds = node_output["research_rounds"]
                max_rounds = node_output.get("max_rounds", 10)
                print(f"RESEARCH PROGRESS: Round {rounds}/{max_rounds}")
                print()
            
            # Show AI's key insights only (simplified)
            if "thinking_log" in node_output:
                for thinking in node_output["thinking_log"]:
                    print(f"INSIGHT: {thinking.insight}")
                    print(f"Confidence: {thinking.confidence:.2f} | Value: {thinking.strategic_value}")
                    print()
            
            # Show key insights discovered  
            if "key_insights" in node_output:
                for insight in node_output["key_insights"]:
                    print(f"KEY DISCOVERY: {insight}")
                    print()
            
            # Show final results
            if "final_questions" in node_output:
                final_result = node_output["final_questions"]
                if final_result and len(final_result) > 0:
                    total_questions = len(final_result[0].get("questions", []))
                    confidence = final_result[0].get("confidence_level", 0)
                    print("FINAL DEPOSITION STRATEGY READY!")
                    print(f"   Generated {total_questions} strategic questions")
                    print(f"   Average confidence: {confidence:.2f}")
                print()
    
    return final_result

# Core intelligent functions

async def analyze_evidence_intelligently(evidence_batch: List[str], current_focus: str, case_background: str, config) -> EvidenceAnalysis:
    """AI analyzes evidence to find real insights and decide what to investigate next"""
    
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Combine evidence for analysis
    evidence_text = "\n\n".join([f"Evidence {i+1}: {evidence}" for i, evidence in enumerate(evidence_batch)])
    
    analysis_prompt = f"""You are an expert litigation attorney analyzing evidence for deposition preparation.

Case Background: {case_background}
Current Investigation Focus: {current_focus}

Evidence Found:
{evidence_text}

Analyze this evidence carefully and provide:

1. What specific contradictions, timeline issues, or credibility problems did you find?
2. What does this evidence reveal that could be used to impeach or corner a witness?
3. How confident are you in this evidence (0.0 to 1.0)?
4. How strategically valuable is this finding for depositions?
5. What specific leads should be investigated next?

Focus on SPECIFIC findings - actual quotes, dates, names, contradictions. Be concrete about what makes this evidence valuable or weak."""

    try:
        structured_llm = writer_model.with_structured_output(EvidenceAnalysis)
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who finds specific contradictions and credibility issues in evidence."),
            HumanMessage(content=analysis_prompt)
        ])
        
        return result
        
    except Exception as e:
        print(f"Error in evidence analysis: {e}")
        # Fallback with basic analysis
        return EvidenceAnalysis(
            thinking=Thinking(
                what_i_found=f"Analyzed {len(evidence_batch)} pieces of evidence about {current_focus}",
                insight="Basic evidence review completed",
                reasoning="Need more sophisticated analysis",
                confidence=0.3,
                strategic_value="Unknown - needs deeper analysis",
                next_focus="Continue investigating with different approach"
            ),
            high_value_leads=[f"Search for more evidence about {current_focus}"]
        )

async def decide_next_action_intelligently(state: DepositionAgentState, config) -> NextActionDecision:
    """AI looks at all discoveries and decides what to do next"""
    
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Summarize current state for LLM
    thinking_summary = []
    for thinking in state.get("thinking_log", []):
        thinking_summary.append(f"Found: {thinking.what_i_found} | Insight: {thinking.insight} | Confidence: {thinking.confidence}")
    
    insights_summary = "\n".join(state.get("key_insights", []))
    current_investigation = state.get("current_investigation", "Initial investigation")
    research_rounds = state.get("research_rounds", 0)
    max_rounds = state.get("max_rounds", 10)
    
    # Count high-confidence insights
    high_confidence_insights = sum(1 for t in state.get("thinking_log", []) if t.confidence > 0.7)
    total_insights = len(state.get("thinking_log", []))
    
    decision_prompt = f"""You are an expert litigation attorney making strategic decisions about deposition preparation research.

Case Background: {state["case_background"]}
Current Investigation: {current_investigation}
Research Round: {research_rounds}/{max_rounds}

Analysis History:
{chr(10).join(thinking_summary) if thinking_summary else "No analysis completed yet"}

Key Insights Discovered:
{insights_summary if insights_summary else "No key insights identified yet"}

Evidence Quality Assessment:
- Total insights found: {total_insights}
- High-confidence insights (>0.7): {high_confidence_insights}
- Research rounds completed: {research_rounds}

IMPORTANT: You should be VERY conservative about moving to question generation. Only choose "generate_questions" if you have:
1. At least 3-4 high-confidence insights with strong evidence
2. Multiple contradictions or smoking gun pieces of evidence
3. Comprehensive evidence that would devastate the witness
4. Strong confidence that you have enough ammunition for an effective deposition

Otherwise, continue researching. Better to over-investigate than under-investigate.

Based on your analysis so far, decide what to do next:

1. investigate_deeper: Continue researching the current focus area because you need more evidence (PREFERRED - be thorough!)
2. switch_focus: Move to a different area because current area is exhausted or unproductive  
3. generate_questions: Start generating questions ONLY if you have overwhelming evidence

Consider:
- Do you have multiple devastating contradictions or smoking gun evidence?
- Are there obvious gaps that need filling?
- Would more research likely uncover additional damaging evidence?
- Is the current evidence quality sufficient for devastating cross-examination?

BE THOROUGH - better to over-research than generate weak questions."""

    try:
        structured_llm = writer_model.with_structured_output(NextActionDecision)
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who is VERY conservative about moving to question generation. You prefer thorough research over rushing to questions."),
            HumanMessage(content=decision_prompt)
        ])
        
        return result
        
    except Exception as e:
        print(f"Error in decision making: {e}")
        # Fallback decision - default to more research
        return NextActionDecision(
            next_action="investigate_deeper",
            reasoning="Continuing research due to analysis error - better to over-investigate",
            investigation_target="Continue current investigation",
            readiness_assessment="Need more evidence before generating questions"
        )

async def generate_strategic_questions(state: DepositionAgentState, config) -> List[dict]:
    """Generate questions based on actual insights discovered"""
    
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Compile all insights for question generation
    insights_for_questions = []
    for thinking in state.get("thinking_log", []):
        if thinking.confidence > 0.4:  # Only use confident insights
            insights_for_questions.append({
                "evidence": thinking.what_i_found,
                "insight": thinking.insight,
                "strategic_value": thinking.strategic_value
            })
    
    if not insights_for_questions:
        return [{"questions": ["What is your knowledge of this case?"], "basis": "General inquiry"}]
    
    question_prompt = f"""You are an expert litigation attorney generating strategic deposition questions based on specific evidence and insights.

Case Background: {state["case_background"]}

Evidence and Insights Discovered:
{chr(10).join([f"Evidence: {insight['evidence']} | Insight: {insight['insight']} | Value: {insight['strategic_value']}" for insight in insights_for_questions])}

Generate 8-12 strategic deposition questions that:
1. Build on the specific evidence and insights found
2. Create logical sequences that corner the witness
3. Reference specific documents, dates, communications discovered
4. Expose the contradictions and credibility issues identified

Return the questions as a simple list of strings. Make each question tactical and based on the actual evidence found."""

    try:
        response = await writer_model.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who generates strategic deposition questions based on specific evidence."),
            HumanMessage(content=question_prompt)
        ])
        
        # Parse response into question list
        question_text = response.content
        questions = [q.strip() for q in question_text.split('\n') if q.strip() and not q.strip().startswith('#')]
        
        return [{
            "questions": questions,
            "basis": f"Based on {len(insights_for_questions)} key insights discovered",
            "evidence_sources": len(state.get("evidence_gathered", [])),
            "confidence_level": sum(t.confidence for t in state.get("thinking_log", [])) / max(len(state.get("thinking_log", [])), 1)
        }]
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        return [{"questions": ["What is your role in this matter?", "What documents have you reviewed?"], "basis": "Fallback questions"}] 

# Simplified intelligent nodes

async def initial_investigation(state: DepositionAgentState, config: RunnableConfig):
    """Start investigation by identifying key areas to explore"""
    
    case_background = state["case_background"]
    configurable = Configuration.from_runnable_config(config)
    
    # AI plans initial investigation
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model_kwargs = get_config_value(configurable.writer_model_kwargs or {})
    writer_model = init_chat_model(
        model=writer_model_name, 
        model_provider=writer_provider, 
        model_kwargs=writer_model_kwargs
    )
    
    # Manus-like strategic overview
    print("Let me analyze this case and explain my approach...")
    print()
    
    overview_prompt = f"""You are an expert litigation attorney about to begin deposition preparation research. 

Case Background: {case_background}

Provide a concise but thoughtful strategic overview (2-3 sentences) explaining:
1. What you see as the key opportunities and vulnerabilities in this case
2. Your overall approach for finding devastating deposition evidence
3. What kind of contradictions or smoking guns you'll be hunting for

Only output 2 to 3 sentances. Start witgs omething like "I'll help you find the evidence to make this happen..."

Be conversational and strategic, like you're explaining your game plan to a colleague. Focus on the specific details of this case, not generic deposition advice."""

    try:
        overview_response = await writer_model.ainvoke([
            SystemMessage(content="You are an expert litigation attorney who provides strategic overviews before beginning deposition research. Be concise, insightful, and case-specific."),
            HumanMessage(content=overview_prompt)
        ])
        
        strategic_overview = overview_response.content
        print(f"AGENT_INTRO: {strategic_overview}")
        print()
        print("Now let me get to work finding the evidence to make this happen...")
        print()
        
    except Exception as e:
        print("AGENT_INTRO: I'm going to systematically investigate this case to find contradictions, timeline issues, and credibility problems that will give us devastating deposition questions.")
        print()
        print("Let me start my investigation...")
        print()
    
    planning_prompt = f"""You are an expert litigation attorney planning a deposition preparation investigation.

Case Background: {case_background}

Create an initial investigation plan:
1. What are 4-5 specific search queries that would uncover the most valuable evidence for depositions?
2. What should be the primary investigation focus (what vulnerability to explore first)?

Focus on finding contradictions, credibility issues, timeline problems, document gaps, and smoking gun evidence."""

    structured_llm = writer_model.with_structured_output(InvestigationPlan)
    
    plan = await structured_llm.ainvoke([
        SystemMessage(content="You are an expert litigation attorney who plans strategic deposition research."),
        HumanMessage(content=planning_prompt)
    ])
    
    print(f"Starting investigation: {plan.investigation_focus}")
    print(f"Conducting {len(plan.search_queries)} targeted searches...")
    
    # Execute initial searches
    initial_evidence = []
    for query in plan.search_queries:
        results = await search_documents_with_azure_ai([query], configurable)
        initial_evidence.append(results)
        print(f"Searched: {query}")
    
    return {
        "current_investigation": plan.investigation_focus,
        "evidence_gathered": initial_evidence,
        "next_action": "investigate_deeper",
        "research_assessment": f"Started investigation into {plan.investigation_focus}. Found {len(initial_evidence)} evidence sets to analyze.",
        "question_readiness": False,
        "research_rounds": 0,  # Initialize rounds counter
        "max_rounds": 2  # Set max rounds to 10
    }

async def adaptive_researcher(state: DepositionAgentState, config: RunnableConfig):
    """Analyze current evidence and adaptively decide what to do next"""
    
    current_focus = state["current_investigation"]
    evidence_gathered = state.get("evidence_gathered", [])
    case_background = state["case_background"]
    research_rounds = state.get("research_rounds", 0)
    max_rounds = state.get("max_rounds", 10)
    
    # Increment research rounds
    new_research_rounds = research_rounds + 1
    
    print(f"Research Round {new_research_rounds}/{max_rounds} - Analyzing evidence about: {current_focus}")
    
    # Check if we've hit max rounds
    if new_research_rounds >= max_rounds:
        print(f"Reached maximum research rounds ({max_rounds}). Moving to question generation.")
        return {
            "research_rounds": new_research_rounds,
            "next_action": "generate_questions",
            "question_readiness": True,
            "research_assessment": f"Completed maximum research rounds ({max_rounds}). Proceeding with available evidence."
        }
    
    # AI analyzes current evidence for insights
    if evidence_gathered:
        analysis = await analyze_evidence_intelligently(evidence_gathered, current_focus, case_background, config)
        
        # Display AI's thinking (simplified)
        thinking = analysis.thinking
        print(f"{thinking.insight}")
        print(f"Confidence: {thinking.confidence:.1f} | Strategic Value: {thinking.strategic_value}")
        
        # AI decides what to do next (with conservative bias)
        decision = await decide_next_action_intelligently(state, config)
        print(f"Decision: {decision.next_action}")
        
        # Prepare updates based on AI decision
        updates = {
            "thinking_log": [thinking],
            "next_action": decision.next_action,
            "research_assessment": decision.readiness_assessment,
            "research_rounds": new_research_rounds
        }
        
        # Be VERY conservative about question readiness
        # Only set to True if AI explicitly chooses generate_questions AND we have strong evidence
        high_confidence_insights = sum(1 for t in state.get("thinking_log", []) if t.confidence > 0.7)
        
        if decision.next_action == "generate_questions" and high_confidence_insights >= 2 and new_research_rounds >= 3:
            updates["question_readiness"] = True
            print(f"AI determined ready for questions after {new_research_rounds} rounds with {high_confidence_insights} high-confidence insights")
        else:
            updates["question_readiness"] = False
            if decision.next_action == "generate_questions":
                print(f"AI wanted questions but forcing more research: rounds={new_research_rounds}, high_conf_insights={high_confidence_insights}")
                updates["next_action"] = "investigate_deeper"  # Override to force more research
        
        # If continuing research, gather more evidence
        if updates["next_action"] == "investigate_deeper":
            configurable = Configuration.from_runnable_config(config)
            new_evidence = []
            print(f"Conducting {len(analysis.high_value_leads[:3])} additional searches...")
            for lead in analysis.high_value_leads[:3]:  # Limit to 3 searches
                results = await search_documents_with_azure_ai([lead], configurable)
                new_evidence.append(results)
            
            updates["evidence_gathered"] = new_evidence
            
        elif updates["next_action"] == "switch_focus":
            updates["current_investigation"] = decision.investigation_target
            updates["evidence_gathered"] = []  # Reset evidence for new focus
            
        # Add key insights if they're strong enough
        if thinking.confidence > 0.6:
            insight_summary = f"{thinking.insight} (Evidence: {thinking.what_i_found[:100]}...)"
            updates["key_insights"] = [insight_summary]
            
        return updates
    
    else:
        # No evidence yet, need to start research
        return {
            "next_action": "investigate_deeper",
            "research_assessment": "No evidence gathered yet, need to start research",
            "question_readiness": False,
            "research_rounds": new_research_rounds
        }

async def question_compiler(state: DepositionAgentState, config: RunnableConfig):
    """Generate final questions based on insights discovered"""
    
    print("Compiling deposition questions based on discoveries...")
    
    questions = await generate_strategic_questions(state, config)
    
    # Display results
    if questions and questions[0].get("questions"):
        question_count = len(questions[0]["questions"])
        confidence = questions[0].get("confidence_level", 0)
        print(f"Generated {question_count} strategic questions")
        print(f"Average confidence: {confidence:.2f}")
        print(f"Based on {len(state.get('key_insights', []))} key insights")
    
    return {
        "final_questions": questions,
        "question_readiness": True
    } 

# Create simplified but intelligent graph
deposition_agent = StateGraph(
    DepositionAgentState, 
    input=DepositionAgentInput, 
    output=DepositionAgentOutput,
    config_schema=Configuration
)

# Add the new intelligent nodes
deposition_agent.add_node("initial_investigation", initial_investigation)
deposition_agent.add_node("adaptive_researcher", adaptive_researcher) 
deposition_agent.add_node("question_compiler", question_compiler)

# Simple but adaptive routing
deposition_agent.add_edge(START, "initial_investigation")
deposition_agent.add_edge("initial_investigation", "adaptive_researcher")

# AI-driven routing - the AI decides what to do next
deposition_agent.add_conditional_edges(
    "adaptive_researcher",
    route_by_ai_decision,
    {
        "continue_research": "adaptive_researcher",  # Self-loop for continued research
        "generate_questions": "question_compiler"     # AI decides it's ready for questions
    }
)

deposition_agent.add_edge("question_compiler", END)

# Compile the intelligent graph
deposition_graph = deposition_agent.compile()