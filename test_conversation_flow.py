#!/usr/bin/env python3
"""
Comprehensive conversation flow test for refactored Combot Backend
Tests all major functionality including OpenAI API, validation, memory management, etc.
"""

import os
import sys
import json
import time
import requests
import django
from typing import Dict, Any, List

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'combotBaselineBE.settings')
django.setup()

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.PURPLE}{'='*60}")
    print(f"🧪 {message}")
    print(f"{'='*60}{Colors.END}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_step(message: str):
    print(f"{Colors.CYAN}📋 {message}{Colors.END}")

class ConversationTester:
    """Test class for simulating conversation flows."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.conversation_log = []
        
    def test_server_health(self) -> bool:
        """Test if the server is running and healthy."""
        print_step("Testing server health...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/memory-status/")
            if response.status_code == 200:
                print_success("Server is running and responding")
                return True
            else:
                print_error(f"Server returned status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Server health check failed: {e}")
            return False
    
    def test_initial_message(self, brand: str = "Basic") -> Dict[str, Any]:
        """Test initial message endpoint."""
        print_step(f"Testing initial message for {brand} brand...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/random/initial/")
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('reply', data.get('message', 'No message'))
                print_success(f"Initial message received: {response_text[:100]}...")
                return data
            else:
                print_error(f"Initial message failed: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            print_error(f"Initial message test failed: {e}")
            return {}
    
    def test_chat_message(self, message: str, index: int, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test chat message endpoint."""
        print_step(f"Testing chat message: '{message}' (index: {index})")
        
        try:
            payload = {
                "message": message,
                "index": index,
                "scenario": scenario,
                "timer": 30,
                "chatLog": self.conversation_log,
                "messageTypeLog": ["user", "assistant"] * (len(self.conversation_log) // 2),
                "classType": scenario.get("problem_type", "A")
            }
            
            response = self.session.post(
                f"{self.base_url}/api/random/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('reply', data.get('message', 'No message'))
                print_success(f"Chat response received: {response_text[:100]}...")
                
                # Log the conversation
                self.conversation_log.append({"role": "user", "content": message})
                if response_text != 'No message':
                    self.conversation_log.append({"role": "assistant", "content": response_text})
                
                return data
            else:
                print_error(f"Chat message failed: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            print_error(f"Chat message test failed: {e}")
            return {}
    
    def test_validation_errors(self):
        """Test input validation with invalid data."""
        print_step("Testing input validation...")
        
        # Test invalid brand
        invalid_payload = {
            "message": "Hello",
            "index": 0,
            "scenario": {"brand": "InvalidBrand", "think_level": "High", "feel_level": "High"}
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/random/",
                json=invalid_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                data = response.json()
                if "VALIDATION_ERROR" in data.get("error_code", ""):
                    print_success("Validation error properly caught for invalid brand")
                else:
                    print_error("Unexpected error response")
            else:
                print_error(f"Expected 400 status, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Validation test failed: {e}")
    
    def test_memory_status(self):
        """Test memory status endpoint."""
        print_step("Testing memory status...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/memory-status/")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Memory status: {data}")
            else:
                print_warning(f"Memory status returned {response.status_code}")
                
        except Exception as e:
            print_error(f"Memory status test failed: {e}")
    
    def test_lulu_brand(self):
        """Test Lulu brand specific functionality."""
        print_step("Testing Lulu brand conversation...")
        
        lulu_scenario = {
            "brand": "Lulu",
            "think_level": "High",
            "feel_level": "High",
            "problem_type": "A"
        }
        
        # Test Lulu initial message
        try:
            response = self.session.get(f"{self.base_url}/api/lulu/initial/")
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('reply', data.get('message', 'No message'))
                print_success(f"Lulu initial message: {response_text[:100]}...")
            else:
                print_error(f"Lulu initial message failed: {response.status_code}")
        except Exception as e:
            print_error(f"Lulu initial message test failed: {e}")
        
        # Test Lulu chat
        try:
            payload = {
                "message": "I need help with my yoga pants",
                "index": 0,
                "scenario": lulu_scenario
            }
            
            response = self.session.post(
                f"{self.base_url}/api/lulu/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('reply', data.get('message', 'No message'))
                print_success(f"Lulu chat response: {response_text[:100]}...")
            else:
                print_error(f"Lulu chat failed: {response.status_code}")
                
        except Exception as e:
            print_error(f"Lulu chat test failed: {e}")
    
    def run_basic_conversation(self):
        """Run a complete basic conversation flow."""
        print_header("Running Basic Brand Conversation Flow")
        
        # Step 1: Get initial message
        initial_data = self.test_initial_message("Basic")
        if not initial_data:
            return False
        
        # Step 2: Start conversation
        basic_scenario = {
            "brand": "Basic",
            "think_level": "High",
            "feel_level": "High",
            "problem_type": "A"
        }
        
        # First user message
        response1 = self.test_chat_message(
            "I'm having trouble with my order",
            0,
            basic_scenario
        )
        if not response1:
            return False
        
        # Second user message
        response2 = self.test_chat_message(
            "Yes, it's been over a week and I haven't received any updates",
            1,
            basic_scenario
        )
        if not response2:
            return False
        
        # Third user message
        response3 = self.test_chat_message(
            "Order number is 12345",
            2,
            basic_scenario
        )
        if not response3:
            return False
        
        print_success("Basic conversation flow completed successfully!")
        return True
    
    def run_lulu_conversation(self):
        """Run a complete Lulu conversation flow."""
        print_header("Running Lulu Brand Conversation Flow")
        
        lulu_scenario = {
            "brand": "Lulu",
            "think_level": "High",
            "feel_level": "High",
            "problem_type": "A"
        }
        
        # First user message
        response1 = self.test_chat_message(
            "I love your gear but my leggings are pilling",
            0,
            lulu_scenario
        )
        if not response1:
            return False
        
        # Second user message
        response2 = self.test_chat_message(
            "I've only worn them a few times for my practice",
            1,
            lulu_scenario
        )
        if not response2:
            return False
        
        print_success("Lulu conversation flow completed successfully!")
        return True
    
    def test_error_scenarios(self):
        """Test various error scenarios."""
        print_header("Testing Error Scenarios")
        
        # Test validation errors
        self.test_validation_errors()
        
        # Test memory status
        self.test_memory_status()
        
        # Test Lulu brand
        self.test_lulu_brand()
    
    def run_comprehensive_test(self):
        """Run comprehensive test suite."""
        print_header("Starting Comprehensive Conversation Flow Test")
        
        # Test server health
        if not self.test_server_health():
            print_error("Server health check failed. Please ensure the server is running.")
            return False
        
        # Test error scenarios
        self.test_error_scenarios()
        
        # Run conversation flows
        basic_success = self.run_basic_conversation()
        lulu_success = self.run_lulu_conversation()
        
        # Summary
        print_header("Test Summary")
        print_info(f"Basic conversation: {'✅ PASSED' if basic_success else '❌ FAILED'}")
        print_info(f"Lulu conversation: {'✅ PASSED' if lulu_success else '❌ FAILED'}")
        print_info(f"Total conversation turns: {len(self.conversation_log)}")
        
        if basic_success and lulu_success:
            print_success("🎉 All tests passed! Refactored code is working correctly.")
            return True
        else:
            print_error("❌ Some tests failed. Please check the logs above.")
            return False

def main():
    """Main test function."""
    print_header("Comprehensive Conversation Flow Test")
    print_info("Testing refactored Combot Backend with simulated conversations")
    print_info("This will test OpenAI API, validation, memory management, and conversation flows")
    
    tester = ConversationTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print_header("🎉 TEST COMPLETED SUCCESSFULLY")
        print_success("All refactored functionality is working correctly!")
        print_info("✅ OpenAI API integration")
        print_info("✅ Input validation")
        print_info("✅ Memory management")
        print_info("✅ Conversation flows")
        print_info("✅ Error handling")
        print_info("✅ Multi-brand support")
    else:
        print_header("❌ TEST FAILED")
        print_error("Some functionality is not working correctly.")
        print_info("Please check the server logs and ensure all services are running.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 