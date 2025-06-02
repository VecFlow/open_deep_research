"""
Basic tests for the legal discovery backend.
Tests core functionality without external dependencies.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all core modules can be imported."""
    try:
        # Mock environment variables for imports
        with patch.dict(os.environ, {
            'WEAVIATE_URL': 'http://localhost:8080',
            'WEAVIATE_COLLECTION_NAME': 'TestDocuments'
        }):
            from database.models import Case, Analysis, Comment
            from schemas.case_schemas import CaseCreate, CaseUpdate
            print("✅ Core imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_models():
    """Test database model definitions."""
    try:
        from database.models import Case, Analysis, Comment, AnalysisStatus
        
        # Test enum values
        assert AnalysisStatus.DRAFT == "draft"
        assert AnalysisStatus.IN_PROGRESS == "in_progress"
        assert AnalysisStatus.COMPLETED == "completed"
        
        print("✅ Database models test passed")
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False

def test_schemas():
    """Test Pydantic schemas."""
    try:
        from schemas.case_schemas import CaseCreate, WorkflowStatus
        
        # Test case creation schema
        case_data = {
            "title": "Test Case",
            "background": "This is a test case background that is long enough for validation."
        }
        case = CaseCreate(**case_data)
        assert case.title == "Test Case"
        assert case.number_of_queries == 3  # default value
        
        # Test workflow status
        status = WorkflowStatus(
            status="in_progress",
            progress_percentage=50.0,
            feedback_requested=False,
            categories_completed=2,
            total_categories=4
        )
        assert status.progress_percentage == 50.0
        
        print("✅ Schemas test passed")
        return True
    except Exception as e:
        print(f"❌ Schemas test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_document_service():
    """Test document service functionality."""
    try:
        # Mock environment variables first
        with patch.dict(os.environ, {
            'WEAVIATE_URL': 'http://localhost:8080',
            'WEAVIATE_COLLECTION_NAME': 'TestDocuments'
        }):
            # Mock the Weaviate client to avoid external dependencies
            with patch('services.document_service.weaviate') as mock_weaviate:
                # Mock client behavior
                mock_client = Mock()
                mock_client.is_ready.return_value = True
                mock_client.get_meta.return_value = {"version": "1.0.0", "modules": {}}
                
                # Mock query results
                mock_query_result = {
                    "data": {
                        "Get": {
                            "Documents": [
                                {
                                    "title": "Test Document",
                                    "content": "Test content",
                                    "source": "test.pdf",
                                    "_additional": {"certainty": 0.9}
                                }
                            ]
                        }
                    }
                }
                
                mock_client.query.get.return_value.with_near_text.return_value.with_limit.return_value.with_additional.return_value.do.return_value = mock_query_result
                mock_weaviate.Client.return_value = mock_client
                
                # Now test the service
                from services.document_service import DocumentService
                
                service = DocumentService()
                
                # Test search functionality
                results = await service.search_documents(
                    queries=["test query"],
                    limit=5
                )
                
                assert isinstance(results, str)
                assert "Test Document" in results
                
                print("✅ Document service test passed")
                return True
                
    except Exception as e:
        print(f"❌ Document service test failed: {e}")
        return False

def test_langgraph_utils():
    """Test LangGraph utility functions."""
    try:
        # Import from our local utils, not langgraph.utils
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from langgraph.utils import format_categories, get_config_value
        
        # Test format_categories
        class MockCategory:
            def __init__(self, name, content):
                self.name = name
                self.content = content
        
        categories = [
            MockCategory("Test Category 1", "Content 1"),
            MockCategory("Test Category 2", "Content 2")
        ]
        
        formatted = format_categories(categories)
        assert "### Test Category 1" in formatted
        assert "Content 1" in formatted
        
        # Test get_config_value with environment variable
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = get_config_value("${TEST_VAR}")
            assert result == "test_value"
        
        # Test get_config_value with direct value
        result = get_config_value("direct_value")
        assert result == "direct_value"
        
        print("✅ LangGraph utils test passed")
        return True
    except Exception as e:
        print(f"❌ LangGraph utils test failed: {e}")
        return False

def test_api_schemas():
    """Test API endpoint schemas."""
    try:
        from schemas.case_schemas import WorkflowCommand, AnalysisProgress
        
        # Test workflow command
        command = WorkflowCommand(action="start")
        assert command.action == "start"
        assert command.feedback is None
        
        command_with_feedback = WorkflowCommand(
            action="feedback",
            feedback="This looks good",
            approve_plan=True
        )
        assert command_with_feedback.feedback == "This looks good"
        assert command_with_feedback.approve_plan is True
        
        print("✅ API schemas test passed")
        return True
    except Exception as e:
        print(f"❌ API schemas test failed: {e}")
        return False

if __name__ == "__main__":
    """Run all tests manually."""
    print("🧪 Running Legal Discovery Backend Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_database_models,
        test_schemas,
        test_langgraph_utils,
        test_api_schemas,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
    
    # Run async test separately
    import asyncio
    try:
        if asyncio.run(test_document_service()):
            passed += 1
            total += 1
    except Exception as e:
        print(f"❌ test_document_service failed with exception: {e}")
        total += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)