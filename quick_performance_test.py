#!/usr/bin/env python3
"""
Quick Performance Test for Optimized OpenAI API
Tests response times with gpt-3.5-turbo and shortened prompts
"""

import requests
import time
import json
import statistics

# Configuration
BASE_URL = "http://3.144.114.76:8000"
TEST_MESSAGES = [
    "I want to report a rude employee who was very disrespectful to me",
    "The employee smacked me in the face at the store",
    "This happened at the mall location yesterday"
]

def test_single_response():
    """Test a single response to measure baseline performance"""
    print("Testing single response performance...")
    
    # Get initial message
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
    initial_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"Initial message failed: {response.status_code}")
        return
    
    initial_data = response.json()
    print(f"Initial message time: {initial_time:.2f}s")
    
    # Test first user message (triggers ML classification + OpenAI)
    user_input = TEST_MESSAGES[0]
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/api/chatbot/", 
                           json={
                               'message': user_input,
                               'index': 1,
                               'chatLog': [{'text': initial_data.get('message', ''), 'sender': 'combot'}],
                               'timer': 0,
                               'classType': 'A',
                               'messageTypeLog': ''
                           }, timeout=30)
    first_response_time = time.time() - start_time
    
    if response.status_code != 200:
        print(f"First message failed: {response.status_code}")
        return
    
    first_response = response.json()
    print(f"First response time: {first_response_time:.2f}s")
    print(f"Response: {first_response.get('reply', '')[:100]}...")
    
    return {
        'initial_time': initial_time,
        'first_response_time': first_response_time,
        'total_time': initial_time + first_response_time
    }

def test_concurrent_responses(num_concurrent=5):
    """Test multiple concurrent responses"""
    print(f"\nTesting {num_concurrent} concurrent responses...")
    
    import threading
    import queue
    
    results = queue.Queue()
    
    def make_request(request_id):
        try:
            # Get initial message
            start_time = time.time()
            response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
            initial_time = time.time() - start_time
            
            if response.status_code != 200:
                results.put({'request_id': request_id, 'error': f"Initial failed: {response.status_code}"})
                return
            
            initial_data = response.json()
            
            # Send user message
            user_input = f"Test message {request_id}: I want to report a rude employee"
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/api/chatbot/", 
                                   json={
                                       'message': user_input,
                                       'index': 1,
                                       'chatLog': [{'text': initial_data.get('message', ''), 'sender': 'combot'}],
                                       'timer': 0,
                                       'classType': 'A',
                                       'messageTypeLog': ''
                                   }, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code != 200:
                results.put({'request_id': request_id, 'error': f"Response failed: {response.status_code}"})
                return
            
            results.put({
                'request_id': request_id,
                'initial_time': initial_time,
                'response_time': response_time,
                'total_time': initial_time + response_time
            })
            
        except Exception as e:
            results.put({'request_id': request_id, 'error': str(e)})
    
    # Start concurrent requests
    threads = []
    for i in range(num_concurrent):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Collect results
    all_results = []
    while not results.empty():
        all_results.append(results.get())
    
    # Calculate statistics
    successful_results = [r for r in all_results if 'error' not in r]
    failed_results = [r for r in all_results if 'error' in r]
    
    if successful_results:
        response_times = [r['response_time'] for r in successful_results]
        total_times = [r['total_time'] for r in successful_results]
        
        stats = {
            'total_requests': len(all_results),
            'successful': len(successful_results),
            'failed': len(failed_results),
            'success_rate': (len(successful_results) / len(all_results)) * 100,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'avg_total_time': statistics.mean(total_times),
            'median_total_time': statistics.median(total_times)
        }
        
        print(f"\nRESULTS:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Average response time: {stats['avg_response_time']:.2f}s")
        print(f"  Median response time: {stats['median_response_time']:.2f}s")
        print(f"  Min response time: {stats['min_response_time']:.2f}s")
        print(f"  Max response time: {stats['max_response_time']:.2f}s")
        print(f"  Average total time: {stats['avg_total_time']:.2f}s")
        print(f"  Median total time: {stats['median_total_time']:.2f}s")
        
        if failed_results:
            print(f"\nERRORS:")
            for result in failed_results:
                print(f"  Request {result['request_id']}: {result['error']}")
        
        return stats
    else:
        print("No successful requests!")
        return None

def main():
    """Run performance tests"""
    print("QUICK PERFORMANCE TEST FOR OPTIMIZED OPENAI API")
    print("Testing with gpt-3.5-turbo and shortened prompts")
    print(f"Target server: {BASE_URL}")
    
    # Test single response
    single_result = test_single_response()
    
    # Test concurrent responses
    concurrent_result = test_concurrent_responses(8)
    
    # Summary
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    
    if single_result:
        print(f"Single response total time: {single_result['total_time']:.2f}s")
        print(f"First response time: {single_result['first_response_time']:.2f}s")
    
    if concurrent_result:
        print(f"Concurrent (8 users) average response time: {concurrent_result['avg_response_time']:.2f}s")
        print(f"Concurrent (8 users) success rate: {concurrent_result['success_rate']:.1f}%")
    
    # Save results
    results = {
        'single_result': single_result,
        'concurrent_result': concurrent_result,
        'timestamp': time.time()
    }
    
    with open('quick_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to quick_performance_results.json")

if __name__ == "__main__":
    main() 