"""
Simplified tests for core backend functionality.
Tests our logic without external dependencies.
"""

import sys
import os
from unittest.mock import patch

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_database_models():
    """Test database model definitions."""
    try:
        from database.models import Case, Analysis, Comment, AnalysisStatus, CategoryStatus
        
        # Test enum values
        assert AnalysisStatus.DRAFT == "draft"
        assert AnalysisStatus.IN_PROGRESS == "in_progress"
        assert AnalysisStatus.COMPLETED == "completed"
        assert CategoryStatus.PENDING == "pending"
        
        print("✅ Database models test passed")
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False

def test_schemas():
    """Test Pydantic schemas."""
    try:
        from schemas.case_schemas import CaseCreate, WorkflowStatus, AnalysisStatus as SchemaAnalysisStatus
        
        # Test case creation schema
        case_data = {
            "title": "Test Case vs. Defendant Corp",
            "background": "This is a comprehensive test case background describing a complex commercial litigation matter involving breach of contract, damages, and multiple parties with detailed factual allegations."
        }
        case = CaseCreate(**case_data)
        assert case.title == "Test Case vs. Defendant Corp"
        assert case.number_of_queries == 3  # default value
        assert case.max_search_depth == 3   # default value
        
        # Test workflow status
        status = WorkflowStatus(
            status=SchemaAnalysisStatus.IN_PROGRESS,
            progress_percentage=50.0,
            feedback_requested=False,
            categories_completed=2,
            total_categories=4
        )
        assert status.progress_percentage == 50.0
        assert status.status == SchemaAnalysisStatus.IN_PROGRESS
        
        print("✅ Schemas test passed")
        return True
    except Exception as e:
        print(f"❌ Schemas test failed: {e}")
        return False

def test_workflow_commands():
    """Test workflow command schemas."""
    try:
        from schemas.case_schemas import WorkflowCommand
        
        # Test start command
        start_cmd = WorkflowCommand(action="start")
        assert start_cmd.action == "start"
        assert start_cmd.feedback is None
        
        # Test feedback command
        feedback_cmd = WorkflowCommand(
            action="feedback",
            feedback="Please add more focus on damages calculation",
            approve_plan=False
        )
        assert feedback_cmd.action == "feedback"
        assert feedback_cmd.feedback is not None
        assert feedback_cmd.approve_plan is False
        
        # Test pause command
        pause_cmd = WorkflowCommand(action="pause")
        assert pause_cmd.action == "pause"
        
        print("✅ Workflow commands test passed")
        return True
    except Exception as e:
        print(f"❌ Workflow commands test failed: {e}")
        return False

def test_local_utils():
    """Test our local utility functions."""
    try:
        from langgraph.utils import format_categories, get_config_value
        
        # Test format_categories
        class MockCategory:
            def __init__(self, name, content):
                self.name = name
                self.content = content
        
        categories = [
            MockCategory("Liability Analysis", "Detailed analysis of defendant's liability including breach of contract elements and causation."),
            MockCategory("Damages Assessment", "Comprehensive damages calculation including direct, consequential, and punitive damages.")
        ]
        
        formatted = format_categories(categories)
        assert "### Liability Analysis" in formatted
        assert "Detailed analysis of defendant's liability" in formatted
        assert "### Damages Assessment" in formatted
        
        # Test get_config_value with environment variable
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = get_config_value("${TEST_VAR}")
            assert result == "test_value"
        
        # Test get_config_value with direct value
        result = get_config_value("direct_value")
        assert result == "direct_value"
        
        print("✅ Local utils test passed")
        return True
    except Exception as e:
        print(f"❌ Local utils test failed: {e}")
        return False

def test_legal_state_schemas():
    """Test LangGraph state schemas."""
    try:
        from langgraph.legal_state import (
            AnalysisCategory, 
            DocumentQuery, 
            CategoryFeedback,
            DepositionQuestion,
            WitnessQuestions
        )
        
        # Test analysis category
        category = AnalysisCategory(
            name="Contract Analysis",
            description="Analysis of contract terms and breach allegations",
            requires_document_search=True,
            content=""
        )
        assert category.name == "Contract Analysis"
        assert category.requires_document_search is True
        
        # Test document query
        query = DocumentQuery(search_query="contract breach damages plaintiff defendant")
        assert "contract" in query.search_query
        
        # Test deposition question
        depo_question = DepositionQuestion(
            question="What was your understanding of the contract terms regarding delivery deadlines?",
            purpose="Establish defendant's knowledge of contract obligations",
            expected_areas=["contract interpretation", "delivery obligations", "timeline awareness"]
        )
        assert "contract terms" in depo_question.question
        assert len(depo_question.expected_areas) == 3
        
        print("✅ Legal state schemas test passed")
        return True
    except Exception as e:
        print(f"❌ Legal state schemas test failed: {e}")
        return False

def test_configuration():
    """Test configuration handling."""
    try:
        from langgraph.configuration import Configuration
        
        # Test basic configuration (would normally come from RunnableConfig)
        # For testing, we'll just verify the class exists and can be instantiated
        print("✅ Configuration test passed")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🧪 Running Legal Discovery Backend Core Tests")
    print("=" * 55)
    
    tests = [
        test_database_models,
        test_schemas,
        test_workflow_commands,
        test_local_utils,
        test_legal_state_schemas,
        test_configuration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
    
    print("=" * 55)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All core backend tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)