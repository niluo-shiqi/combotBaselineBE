#!/usr/bin/env python3
"""
Simple test script to isolate API issues
"""

import requests
import json
import time

def test_endpoint(url, method="GET", data=None, headers=None):
    """Test a single endpoint"""
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        response_time = (time.time() - start_time) * 1000
        print(f"✅ {url} - {response.status_code} ({response_time:.1f}ms)")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        else:
            print(f"   Error: {response.text[:200]}...")
            
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print(f"❌ {url} - Timeout")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {url} - Connection Error")
        return False
    except Exception as e:
        print(f"❌ {url} - Error: {str(e)}")
        return False

def main():
    base_url = "http://18.222.168.169:8000"
    headers = {"Content-Type": "application/json"}
    
    print("🧪 SIMPLE API TEST")
    print("=" * 50)
    
    # Test basic endpoints
    endpoints = [
        ("GET", "/api/random/initial/"),
        ("GET", "/api/lulu/initial/"),
        ("GET", "/api/random/reset/"),
    ]
    
    for method, endpoint in endpoints:
        test_endpoint(f"{base_url}{endpoint}", method, headers=headers)
        time.sleep(1)  # Small delay between requests
    
    # Test POST endpoints
    post_data = {
        "message": "My product is defective",
        "index": 0
    }
    
    post_endpoints = [
        ("POST", "/api/random/", post_data),
    ]
    
    for method, endpoint, data in post_endpoints:
        test_endpoint(f"{base_url}{endpoint}", method, data, headers)
        time.sleep(1)

if __name__ == "__main__":
    main() 