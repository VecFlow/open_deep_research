from typing import Annotated, List, TypedDict, Literal
from pydantic import BaseModel, Field
import operator

class AnalysisCategory(BaseModel):
    name: str = Field(
        description="Name for this category of legal analysis.",
    )
    description: str = Field(
        description="Brief overview of the main legal issues and analysis to be covered in this category.",
    )
    requires_document_search: bool = Field(
        description="Whether to perform document search for this category of analysis."
    )
    content: str = Field(
        description="The content of the analysis for this category."
    )   

class AnalysisCategories(BaseModel):
    categories: List[AnalysisCategory] = Field(
        description="Categories of legal analysis.",
    )

class DocumentQuery(BaseModel):
    search_query: str = Field(None, description="Query for document search.")

class DocumentQueries(BaseModel):
    queries: List[DocumentQuery] = Field(
        description="List of document search queries.",
    )

class CategoryFeedback(BaseModel):
    grade: Literal["pass","fail"] = Field(
        description="Evaluation result indicating whether the analysis meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[DocumentQuery] = Field(
        description="List of follow-up document search queries.",
    )

class DepositionQuestion(BaseModel):
    question: str = Field(
        description="The deposition question to ask."
    )
    purpose: str = Field(
        description="The legal purpose or goal of asking this question."
    )
    expected_areas: List[str] = Field(
        description="Expected areas of testimony or evidence this question might reveal.",
        default_factory=list
    )

class WitnessQuestions(BaseModel):
    witness_name: str = Field(
        description="Name or description of the witness to be deposed."
    )
    witness_role: str = Field(
        description="The witness's role in the case or relevance to the litigation."
    )
    questions: List[DepositionQuestion] = Field(
        description="List of strategic deposition questions for this witness."
    )

class DepositionQuestions(BaseModel):
    witness_questions: List[WitnessQuestions] = Field(
        description="Deposition questions organized by witness."
    )

class LegalAnalysisInput(TypedDict):
    background_on_case: str  # Background information on the legal case
    
class LegalAnalysisOutput(TypedDict):
    final_analysis: str  # Final legal analysis with deposition questions

class LegalAnalysisState(TypedDict):
    background_on_case: str  # Background information on the legal case
    feedback_on_analysis_plan: Annotated[list[str], operator.add]  # List of feedback on the analysis plan
    categories: list[AnalysisCategory]  # List of analysis categories 
    completed_categories: Annotated[list, operator.add]  # Send() API key
    analysis_categories_from_documents: str  # String of completed categories from document analysis
    deposition_questions: DepositionQuestions  # Generated deposition questions
    final_analysis: str  # Final legal analysis

class CategoryState(TypedDict):
    background_on_case: str  # Background information on the legal case
    category: AnalysisCategory  # Analysis category
    search_iterations: int  # Number of document search iterations done
    document_queries: list[DocumentQuery]  # List of document queries
    source_docs: str  # String of formatted source content from document search
    analysis_categories_from_documents: str  # String of completed categories for context
    completed_categories: list[AnalysisCategory]  # Final key we duplicate in outer state for Send() API

class CategoryOutputState(TypedDict):
    completed_categories: list[AnalysisCategory]  # Final key we duplicate in outer state for Send() API 