#!/usr/bin/env python3
"""
Quick Health Check for Combot Backend
"""

import requests
import json
import time

def test_endpoint(url, method="GET", data=None, expected_status=200):
    """Test a single endpoint"""
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        response_time = (time.time() - start_time) * 1000
        success = response.status_code == expected_status
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {url} - {response.status_code} ({response_time:.1f}ms)")
        
        if success and response.status_code == 200:
            try:
                response_data = response.json()
                if 'message' in response_data:
                    print(f"   Message: {response_data['message'][:50]}...")
                elif 'reply' in response_data:
                    print(f"   Reply: {response_data['reply'][:50]}...")
            except:
                pass
                
        return success
        
    except Exception as e:
        print(f"❌ {url} - Error: {str(e)}")
        return False

def main():
    print("🏥 COMBOT BACKEND HEALTH CHECK")
    print("=" * 50)
    
    # Test local server
    print("\n📍 LOCAL SERVER (localhost:8000)")
    print("-" * 30)
    
    local_tests = [
        ("GET", "/api/random/initial/", None),
        ("GET", "/api/lulu/initial/", None),
        ("GET", "/api/random/reset/", None),
        ("POST", "/api/random/", {"message": "Test message", "index": 0}),
    ]
    
    local_success = 0
    for method, endpoint, data in local_tests:
        if test_endpoint(f"http://localhost:8000{endpoint}", method, data):
            local_success += 1
    
    # Test remote server
    print("\n🌐 REMOTE SERVER (18.222.168.169:8000)")
    print("-" * 30)
    
    remote_tests = [
        ("GET", "/api/random/initial/", None),
        ("GET", "/api/lulu/initial/", None),
        ("GET", "/api/random/reset/", None),
        ("POST", "/api/random/", {"message": "Test message", "index": 0}),
    ]
    
    remote_success = 0
    for method, endpoint, data in remote_tests:
        if test_endpoint(f"http://18.222.168.169:8000{endpoint}", method, data):
            remote_success += 1
    
    # Summary
    print("\n📊 HEALTH CHECK SUMMARY")
    print("=" * 50)
    print(f"Local Server:  {local_success}/4 tests passed")
    print(f"Remote Server: {remote_success}/4 tests passed")
    
    if local_success == 4 and remote_success == 4:
        print("🎉 All systems operational!")
    elif local_success == 4:
        print("⚠️  Local server OK, remote server has issues")
    elif remote_success == 4:
        print("⚠️  Remote server OK, local server has issues")
    else:
        print("🚨 Multiple issues detected")

if __name__ == "__main__":
    main() 