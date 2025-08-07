#!/usr/bin/env python3
"""
Quick Server Test
Simple test to diagnose server connectivity and API issues
"""

import requests
import json
import time

def test_server_connectivity():
    """Test basic server connectivity"""
    print("🔍 Testing server connectivity...")
    
    # Test 1: Basic connectivity
    try:
        response = requests.get("http://3.144.114.76:8000/api/chatbot/initial/", timeout=10)
        print(f"✅ Initial endpoint: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data.get('message', 'No message')[:100]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Initial endpoint failed: {e}")
    
    # Test 2: Chat endpoint (corrected URL)
    try:
        response = requests.post("http://3.144.114.76:8000/api/chatbot/", 
                               json={'message': 'test', 'index': 0, 'timer': 0, 'chatLog': '', 'classType': '', 'messageTypeLog': ''}, 
                               timeout=10)
        print(f"✅ Chat endpoint: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data.get('reply', 'No reply')[:100]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
    
    # Test 3: Server health
    try:
        response = requests.get("http://3.144.114.76:8000/", timeout=10)
        print(f"✅ Root endpoint: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")

def test_single_user_session():
    """Test a single user session"""
    print("\n🧪 Testing single user session...")
    
    try:
        # Step 1: Get initial message
        print("1. Getting initial message...")
        response = requests.get("http://3.144.114.76:8000/api/chatbot/initial/", timeout=30)
        if response.status_code != 200:
            print(f"   ❌ Failed: {response.status_code} - {response.text[:200]}")
            return False
        data = response.json()
        print(f"   ✅ Success: {data.get('message', '')[:50]}...")
        
        # Step 2: Send first message (corrected URL)
        print("2. Sending first message...")
        user_input = "I have a problem with my order."
        response = requests.post("http://3.144.114.76:8000/api/chatbot/", 
                               json={'message': user_input, 'index': 0, 'timer': 0, 'chatLog': '', 'classType': '', 'messageTypeLog': ''}, 
                               timeout=30)
        if response.status_code != 200:
            print(f"   ❌ Failed: {response.status_code} - {response.text[:200]}")
            return False
        data = response.json()
        print(f"   ✅ Success: {data.get('reply', '')[:50]}...")
        
        print("✅ Single user session completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Session failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick Server Test")
    print("=" * 40)
    
    test_server_connectivity()
    test_single_user_session()
    
    print("\n🎉 Quick test completed!") 