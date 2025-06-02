#!/usr/bin/env python3
"""
Backend API Test Script
Comprehensive testing of all Legal Discovery Backend endpoints
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.created_case_id = None
        self.created_analysis_id = None
    
    def print_test(self, test_name: str, method: str, endpoint: str):
        """Print test header"""
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_name}")
        print(f"📡 {method} {endpoint}")
        print(f"{'='*60}")
    
    def print_result(self, response: requests.Response, expected_status: int = 200):
        """Print test result"""
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        
        print(f"{status_icon} Status: {response.status_code} (expected {expected_status})")
        
        try:
            data = response.json()
            print(f"📋 Response: {json.dumps(data, indent=2)}")
            return data
        except:
            print(f"📋 Response: {response.text}")
            return None
    
    def test_health(self):
        """Test health endpoints"""
        # Basic health
        self.print_test("Health Check", "GET", "/health")
        response = self.session.get(f"{BASE_URL}/health")
        self.print_result(response)
        
        # Detailed health
        self.print_test("Detailed Health Check", "GET", "/health/detailed")
        response = self.session.get(f"{BASE_URL}/health/detailed")
        self.print_result(response)
    
    def test_cases(self):
        """Test case management endpoints"""
        # List cases
        self.print_test("List Cases", "GET", "/api/v1/cases")
        response = self.session.get(f"{API_BASE}/cases")
        cases = self.print_result(response)
        
        # Create case
        self.print_test("Create Case", "POST", "/api/v1/cases")
        case_data = {
            "case_title": "API Test Case",
            "case_background": "This is a comprehensive test case created by the API test script to verify all backend functionality."
        }
        response = self.session.post(f"{API_BASE}/cases", json=case_data)
        created_case = self.print_result(response, 200)
        
        if created_case:
            self.created_case_id = created_case["id"]
            print(f"💾 Saved case ID: {self.created_case_id}")
        
        # Get specific case
        if self.created_case_id:
            self.print_test("Get Case", "GET", f"/api/v1/cases/{self.created_case_id}")
            response = self.session.get(f"{API_BASE}/cases/{self.created_case_id}")
            self.print_result(response)
    
    def test_analysis(self):
        """Test analysis workflow endpoints"""
        if not self.created_case_id:
            print("❌ Cannot test analysis - no case ID available")
            return
        
        # Start analysis
        self.print_test("Start Analysis", "POST", f"/api/v1/analysis/{self.created_case_id}/start")
        response = self.session.post(f"{API_BASE}/analysis/{self.created_case_id}/start")
        analysis_result = self.print_result(response)
        
        if analysis_result:
            self.created_analysis_id = analysis_result["analysis_id"]
            print(f"💾 Saved analysis ID: {self.created_analysis_id}")
        
        # Wait a moment for analysis to process
        print("\n⏳ Waiting 3 seconds for analysis to process...")
        time.sleep(3)
        
        # Get analysis status
        if self.created_analysis_id:
            self.print_test("Get Analysis", "GET", f"/api/v1/analysis/{self.created_analysis_id}")
            response = self.session.get(f"{API_BASE}/analysis/{self.created_analysis_id}")
            analysis_data = self.print_result(response)
            
            if analysis_data:
                print(f"\n📊 Analysis Status: {analysis_data['status']}")
                print(f"📈 Progress: {analysis_data['progress_percentage']}%")
                print(f"🔄 Current Step: {analysis_data['current_step']}")
                
                # If failed, show more details
                if analysis_data['status'] == 'failed':
                    print("⚠️  Analysis failed - this needs debugging!")
    
    def test_workflow_control(self):
        """Test workflow control endpoints"""
        if not self.created_analysis_id:
            print("❌ Cannot test workflow control - no analysis ID available")
            return
        
        # Test stop command
        self.print_test("Stop Workflow", "POST", f"/api/v1/analysis/{self.created_analysis_id}/control")
        control_data = {"action": "stop"}
        response = self.session.post(f"{API_BASE}/analysis/{self.created_analysis_id}/control", json=control_data)
        self.print_result(response)
    
    def test_case_with_analysis(self):
        """Test getting case with analysis included"""
        if not self.created_case_id:
            print("❌ Cannot test case with analysis - no case ID available")
            return
        
        self.print_test("Get Case with Analysis", "GET", f"/api/v1/cases/{self.created_case_id}")
        response = self.session.get(f"{API_BASE}/cases/{self.created_case_id}")
        case_data = self.print_result(response)
        
        if case_data and case_data.get("analyses"):
            print(f"\n📊 Case has {len(case_data['analyses'])} analysis(es)")
            for i, analysis in enumerate(case_data["analyses"]):
                print(f"   Analysis {i+1}: {analysis['status']} ({analysis['progress_percentage']}%)")
    
    def debug_langgraph_execution(self):
        """Debug LangGraph execution with detailed logging"""
        if not self.created_case_id:
            print("❌ Cannot debug LangGraph - no case ID available")
            return
        
        print(f"\n{'='*60}")
        print("🔧 DEBUGGING LANGGRAPH EXECUTION")
        print(f"{'='*60}")
        
        # Create a new analysis for debugging
        self.print_test("Debug Analysis Start", "POST", f"/api/v1/analysis/{self.created_case_id}/start")
        response = self.session.post(f"{API_BASE}/analysis/{self.created_case_id}/start")
        debug_analysis = self.print_result(response)
        
        if debug_analysis:
            debug_analysis_id = debug_analysis["analysis_id"]
            print(f"🐛 Debug analysis ID: {debug_analysis_id}")
            
            # Monitor analysis for 10 seconds
            print("\n🔍 Monitoring analysis progress for 10 seconds...")
            for i in range(10):
                time.sleep(1)
                response = self.session.get(f"{API_BASE}/analysis/{debug_analysis_id}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   {i+1}s: {data['status']} - {data['current_step']} ({data['progress_percentage']}%)")
                    
                    if data['status'] in ['completed', 'failed']:
                        break
                else:
                    print(f"   {i+1}s: Error getting analysis status")
            
            # Final status
            response = self.session.get(f"{API_BASE}/analysis/{debug_analysis_id}")
            if response.status_code == 200:
                final_data = response.json()
                print(f"\n🏁 Final Status: {final_data['status']}")
                if final_data['status'] == 'failed':
                    print("❌ LangGraph execution failed - check backend logs for detailed error messages")
                    print("💡 Look for logs with emoji markers: 🔥🚀📊🔍")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests")
        print(f"🌐 Testing: {BASE_URL}")
        
        try:
            # Test all endpoints
            self.test_health()
            self.test_cases()
            self.test_analysis()
            self.test_workflow_control()
            self.test_case_with_analysis()
            
            # Debug LangGraph if needed
            self.debug_langgraph_execution()
            
            print(f"\n{'='*60}")
            print("✅ Backend API Tests Complete!")
            print(f"{'='*60}")
            
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to backend - make sure it's running on http://localhost:8000")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n⏸️  Tests interrupted by user")
            sys.exit(1)

if __name__ == "__main__":
    tester = BackendTester()
    tester.run_all_tests()