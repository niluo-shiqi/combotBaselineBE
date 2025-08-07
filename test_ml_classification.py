#!/usr/bin/env python3
"""
Test script to verify ML classification is working for return requests
"""

import requests
import json
import time

BASE_URL = "http://3.144.114.76:8000"

def test_ml_classification():
    """Test ML classification for return requests"""
    print("Testing ML classification for return requests...")
    
    # Test cases
    test_cases = [
        "I want to return my shoes for a smaller size",
        "I need a refund for defective product",
        "Can I send back this item?",
        "I want to exchange my order",
        "The product arrived damaged"
    ]
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {user_input} ---")
        
        # Get initial message
        response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
        if response.status_code != 200:
            print(f"Initial message failed: {response.status_code}")
            continue
        
        initial_data = response.json()
        initial_message = initial_data.get('message', '')
        
        # Send user message
        chat_log = [{'text': initial_message, 'sender': 'combot'}]
        
        response = requests.post(f"{BASE_URL}/api/chatbot/", 
                               json={
                                   'message': user_input,
                                   'index': 1,
                                   'chatLog': chat_log,
                                   'timer': 0,
                                   'classType': 'A',
                                   'messageTypeLog': ''
                               }, timeout=30)
        
        if response.status_code != 200:
            print(f"Message failed: {response.status_code}")
            continue
        
        response_data = response.json()
        reply = response_data.get('reply', '')
        class_type = response_data.get('classType', '')
        scenario = response_data.get('scenario', {})
        
        print(f"Response: {reply[:100]}...")
        print(f"Class Type: {class_type}")
        print(f"Problem Type: {scenario.get('problem_type', 'N/A')}")
        print(f"Product Type Breakdown: {scenario.get('product_type_breakdown', 'N/A')}")
        
        # Check if product_type_breakdown is not empty
        product_breakdown = scenario.get('product_type_breakdown', {})
        if product_breakdown and product_breakdown != {}:
            print("✅ ML classification working - product_type_breakdown populated")
        else:
            print("❌ ML classification failed - product_type_breakdown empty")
        
        time.sleep(2)  # Wait between tests

if __name__ == "__main__":
    test_ml_classification() 