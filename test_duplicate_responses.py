#!/usr/bin/env python3
"""
Test script to verify duplicate response issue
"""

import requests
import json

BASE_URL = "http://3.144.114.76:8000"

def test_duplicate_responses():
    """Test for duplicate responses"""
    print("Testing for duplicate responses...")
    
    # Get initial message
    response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
    if response.status_code != 200:
        print(f"Initial message failed: {response.status_code}")
        return
    
    initial_data = response.json()
    initial_message = initial_data.get('message', '')
    print(f"Initial message: {initial_message[:100]}...")
    
    # First user message
    user_input1 = "I want to return my shoes for a smaller size"
    chat_log1 = [{'text': initial_message, 'sender': 'combot'}]
    
    response1 = requests.post(f"{BASE_URL}/api/chatbot/", 
                             json={
                                 'message': user_input1,
                                 'index': 1,
                                 'chatLog': chat_log1,
                                 'timer': 0,
                                 'classType': 'A',
                                 'messageTypeLog': ''
                             }, timeout=30)
    
    if response1.status_code != 200:
        print(f"First message failed: {response1.status_code}")
        return
    
    response1_data = response1.json()
    reply1 = response1_data.get('reply', '')
    print(f"First response: {reply1}")
    
    # Second user message
    user_input2 = "I want a size 6 instead of a size 9"
    chat_log2 = [
        {'text': initial_message, 'sender': 'combot'},
        {'text': user_input1, 'sender': 'user'},
        {'text': reply1, 'sender': 'combot'}
    ]
    
    response2 = requests.post(f"{BASE_URL}/api/chatbot/", 
                             json={
                                 'message': user_input2,
                                 'index': 2,
                                 'chatLog': chat_log2,
                                 'timer': 0,
                                 'classType': 'A',
                                 'messageTypeLog': ''
                             }, timeout=30)
    
    if response2.status_code != 200:
        print(f"Second message failed: {response2.status_code}")
        return
    
    response2_data = response2.json()
    reply2 = response2_data.get('reply', '')
    print(f"Second response: {reply2}")
    
    # Check if responses are identical
    if reply1.strip() == reply2.strip():
        print("❌ DUPLICATE RESPONSES DETECTED!")
        print("The two responses are identical:")
        print(f"Response 1: {reply1}")
        print(f"Response 2: {reply2}")
    else:
        print("✅ No duplicate responses detected")
        print("The responses are different:")
        print(f"Response 1: {reply1}")
        print(f"Response 2: {reply2}")

if __name__ == "__main__":
    test_duplicate_responses() 