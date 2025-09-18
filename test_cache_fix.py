#!/usr/bin/env python3
"""
Test script to verify cache isolation fix
"""

import requests
import json
import time

def test_cache_isolation():
    """Test if ML cache isolation is working"""
    
    print("🧪 Testing Cache Isolation Fix...")
    print("=" * 50)
    
    # Test 1: First conversation
    print("\n📝 Test 1: 'The product was defective'")
    payload1 = {
        "message": "The product was defective",
        "index": 0,
        "timer": 0,
        "chatLog": "[]",
        "classType": "A",
        "messageTypeLog": "[]",
        "scenario": {
            "brand": "Basic",
            "problem_type": "A",
            "think_level": "High",
            "feel_level": "High"
        }
    }
    
    try:
        response1 = requests.post(
            "http://localhost:8000/api/chatbot/",
            headers={"Content-Type": "application/json"},
            json=payload1,
            timeout=30
        )
        
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"✅ Response 1: class_type = {result1.get('class_type')}")
        else:
            print(f"❌ Response 1 failed: {response1.status_code}")
            
    except Exception as e:
        print(f"❌ Request 1 failed: {e}")
        result1 = None
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Second conversation with different text
    print("\n📝 Test 2: 'The customer service was rude'")
    payload2 = {
        "message": "The customer service was rude",
        "index": 0,
        "timer": 0,
        "chatLog": "[]",
        "classType": "C",
        "messageTypeLog": "[]",
        "scenario": {
            "brand": "Basic",
            "problem_type": "C",
            "think_level": "Low",
            "feel_level": "Low"
        }
    }
    
    try:
        response2 = requests.post(
            "http://localhost:8000/api/chatbot/",
            headers={"Content-Type": "application/json"},
            json=payload2,
            timeout=30
        )
        
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"✅ Response 2: class_type = {result2.get('class_type')}")
        else:
            print(f"❌ Response 2 failed: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ Request 2 failed: {e}")
        result2 = None
    
    # Analysis
    print("\n🔍 ANALYSIS:")
    if result1 and result2:
        class_type1 = result1.get('class_type')
        class_type2 = result2.get('class_type')
        
        if class_type1 == class_type2:
            print("❌ CACHE ISOLATION FAILED: Both responses have same class_type")
            print(f"   Both returned: {class_type1}")
        else:
            print("✅ CACHE ISOLATION WORKING: Different responses have different class_types")
            print(f"   Response 1: {class_type1}")
            print(f"   Response 2: {class_type2}")
    else:
        print("❌ Cannot analyze - some requests failed")
    
    print("\n" + "=" * 50)
    print("🏁 Test Complete!")

if __name__ == "__main__":
    test_cache_isolation()
