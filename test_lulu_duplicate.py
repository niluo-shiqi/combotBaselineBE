#!/usr/bin/env python3
"""
Test script to verify Lulu brand duplicate response issue
"""

import requests
import json

BASE_URL = "http://3.144.114.76:8000"

def test_lulu_duplicate_responses():
    """Test for duplicate responses with Lulu brand"""
    print("Testing Lulu brand for duplicate responses...")
    
    # Get Lulu initial message
    response = requests.get(f"{BASE_URL}/api/chatbot/lulu/initial/", timeout=30)
    if response.status_code != 200:
        print(f"Lulu initial message failed: {response.status_code}")
        return
    
    initial_data = response.json()
    initial_message = initial_data.get('message', '')
    print(f"Lulu initial message: {initial_message[:100]}...")
    
    # First user message
    user_input1 = "I want to return my shoes for a smaller size"
    chat_log1 = [{'text': initial_message, 'sender': 'combot'}]
    
    response1 = requests.post(f"{BASE_URL}/api/chatbot/lulu/", 
                             json={
                                 'message': user_input1,
                                 'index': 1,
                                 'chatLog': chat_log1,
                                 'timer': 0,
                                 'classType': 'A',
                                 'messageTypeLog': ''
                             }, timeout=30)
    
    if response1.status_code != 200:
        print(f"First Lulu message failed: {response1.status_code}")
        return
    
    response1_data = response1.json()
    reply1 = response1_data.get('reply', '')
    print(f"First Lulu response: {reply1}")
    
    # Second user message (exactly as user reported)
    user_input2 = "I want a size 6 instead of a size 9"
    chat_log2 = [
        {'text': initial_message, 'sender': 'combot'},
        {'text': user_input1, 'sender': 'user'},
        {'text': reply1, 'sender': 'combot'}
    ]
    
    response2 = requests.post(f"{BASE_URL}/api/chatbot/lulu/", 
                             json={
                                 'message': user_input2,
                                 'index': 2,
                                 'chatLog': chat_log2,
                                 'timer': 0,
                                 'classType': 'A',
                                 'messageTypeLog': ''
                             }, timeout=30)
    
    if response2.status_code != 200:
        print(f"Second Lulu message failed: {response2.status_code}")
        return
    
    response2_data = response2.json()
    reply2 = response2_data.get('reply', '')
    print(f"Second Lulu response: {reply2}")
    
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
    
    # Also check if the responses are very similar (partial duplicates)
    similarity = len(set(reply1.split()) & set(reply2.split())) / len(set(reply1.split()) | set(reply2.split()))
    print(f"Response similarity: {similarity:.2%}")
    
    if similarity > 0.8:
        print("⚠️  HIGH SIMILARITY DETECTED - Responses are very similar")

if __name__ == "__main__":
    test_lulu_duplicate_responses() 