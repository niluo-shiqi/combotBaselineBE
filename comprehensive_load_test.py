#!/usr/bin/env python3
"""
Comprehensive Load Test for Combot Backend
Tests the server with OpenAI API and ML classification working
"""

import requests
import time
import json
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import subprocess
import sys

# Configuration
BASE_URL = "http://3.144.114.76:8000"
TEST_SCENARIOS = [
    {"users": 4, "sessions": 3},
    {"users": 8, "sessions": 3},
    {"users": 12, "sessions": 3},
    {"users": 16, "sessions": 3},
    {"users": 20, "sessions": 3},
    {"users": 25, "sessions": 2},
    {"users": 30, "sessions": 2},
    {"users": 35, "sessions": 2},
    {"users": 40, "sessions": 1},
    {"users": 50, "sessions": 1}
]

def get_server_memory():
    """Get current server memory usage via SSH"""
    try:
        result = subprocess.run([
            "ssh", "-i", "~/.ssh/ec2-key.pem", 
            "ec2-user@3.144.114.76", 
            "free -m | grep Mem"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 3:
                total = int(parts[1])
                used = int(parts[2])
                return {
                    'total_mb': total,
                    'used_mb': used,
                    'usage_percent': (used / total) * 100
                }
    except Exception as e:
        print(f"Error getting server memory: {e}")
    
    return None

def simulate_user_session(user_id, session_id):
    """Simulate a complete user session with multiple interactions"""
    session_data = {
        'success': False,
        'response_times': [],
        'errors': [],
        'user_id': user_id,
        'session_id': session_id
    }
    
    try:
        # Step 1: Get initial message
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
        response_time = time.time() - start_time
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"Initial message failed: {response.status_code}")
            return session_data
        
        initial_data = response.json()
        session_data['initial_message'] = initial_data.get('message', '')
        
        # Step 2: Send first user message (triggers ML classification)
        user_input = "I want to report a rude employee who was very disrespectful to me"
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
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"First message failed: {response.status_code}")
            return session_data
        
        first_response = response.json()
        session_data['first_response'] = first_response.get('reply', '')
        
        # Step 3: Send second user message
        user_input2 = "The employee smacked me in the face at the store"
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/chatbot/", 
                               json={
                                   'message': user_input2,
                                   'index': 2,
                                   'chatLog': [
                                       {'text': initial_data.get('message', ''), 'sender': 'combot'},
                                       {'text': user_input, 'sender': 'user'},
                                       {'text': first_response.get('reply', ''), 'sender': 'combot'}
                                   ],
                                   'timer': 0,
                                   'classType': 'A',
                                   'messageTypeLog': ''
                               }, timeout=30)
        response_time = time.time() - start_time
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"Second message failed: {response.status_code}")
            return session_data
        
        second_response = response.json()
        session_data['second_response'] = second_response.get('reply', '')
        
        # Step 4: Send third user message
        user_input3 = "This happened at the mall location yesterday"
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/chatbot/", 
                               json={
                                   'message': user_input3,
                                   'index': 3,
                                   'chatLog': [
                                       {'text': initial_data.get('message', ''), 'sender': 'combot'},
                                       {'text': user_input, 'sender': 'user'},
                                       {'text': first_response.get('reply', ''), 'sender': 'combot'},
                                       {'text': user_input2, 'sender': 'user'},
                                       {'text': second_response.get('reply', ''), 'sender': 'combot'}
                                   ],
                                   'timer': 0,
                                   'classType': 'A',
                                   'messageTypeLog': ''
                               }, timeout=30)
        response_time = time.time() - start_time
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"Third message failed: {response.status_code}")
            return session_data
        
        third_response = response.json()
        session_data['third_response'] = third_response.get('reply', '')
        
        # Step 5: Get closing message
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/chatbot/closing/", timeout=30)
        response_time = time.time() - start_time
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"Closing message failed: {response.status_code}")
            return session_data
        
        closing_data = response.json()
        session_data['closing_message'] = closing_data.get('message', '')
        
        session_data['success'] = True
        session_data['total_time'] = sum(session_data['response_times'])
        
    except requests.exceptions.Timeout:
        session_data['errors'].append("Request timeout")
    except requests.exceptions.ConnectionError:
        session_data['errors'].append("Connection error")
    except Exception as e:
        session_data['errors'].append(f"Unexpected error: {str(e)}")
    
    return session_data

def run_load_test(concurrent_users, num_sessions):
    """Run a load test with specified number of concurrent users"""
    print(f"\n{'='*60}")
    print(f"LOAD TEST: {concurrent_users} concurrent users, {num_sessions} sessions each")
    print(f"{'='*60}")
    
    # Get initial server memory
    initial_memory = get_server_memory()
    if initial_memory:
        print(f"Initial server memory: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
    
    start_time = time.time()
    all_sessions = []
    
    # Create all session tasks
    tasks = []
    for session in range(num_sessions):
        for user in range(concurrent_users):
            user_id = session * concurrent_users + user
            tasks.append((user_id, session))
    
    # Execute sessions with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(simulate_user_session, user_id, session_id): (user_id, session_id)
            for user_id, session_id in tasks
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_task):
            user_id, session_id = future_to_task[future]
            try:
                result = future.result()
                all_sessions.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    print(f"Completed {completed}/{len(tasks)} sessions...")
                    
            except Exception as e:
                print(f"Session {user_id}-{session_id} failed: {e}")
    
    end_time = time.time()
    total_test_time = end_time - start_time
    
    # Get final server memory
    final_memory = get_server_memory()
    
    # Calculate statistics
    successful_sessions = [s for s in all_sessions if s['success']]
    failed_sessions = [s for s in all_sessions if not s['success']]
    
    if successful_sessions:
        all_response_times = []
        for session in successful_sessions:
            all_response_times.extend(session['response_times'])
        
        stats = {
            'total_sessions': len(all_sessions),
            'successful_sessions': len(successful_sessions),
            'failed_sessions': len(failed_sessions),
            'success_rate': (len(successful_sessions) / len(all_sessions)) * 100,
            'avg_response_time': statistics.mean(all_response_times),
            'median_response_time': statistics.median(all_response_times),
            'min_response_time': min(all_response_times),
            'max_response_time': max(all_response_times),
            'total_test_time': total_test_time,
            'sessions_per_second': len(all_sessions) / total_test_time,
            'initial_memory': initial_memory,
            'final_memory': final_memory
        }
        
        if final_memory and initial_memory:
            stats['memory_increase_mb'] = final_memory['used_mb'] - initial_memory['used_mb']
            stats['memory_increase_percent'] = final_memory['usage_percent'] - initial_memory['usage_percent']
        
        # Print results
        print(f"\nRESULTS:")
        print(f"  Total sessions: {stats['total_sessions']}")
        print(f"  Successful: {stats['successful_sessions']}")
        print(f"  Failed: {stats['failed_sessions']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Average response time: {stats['avg_response_time']:.2f}s")
        print(f"  Median response time: {stats['median_response_time']:.2f}s")
        print(f"  Min response time: {stats['min_response_time']:.2f}s")
        print(f"  Max response time: {stats['max_response_time']:.2f}s")
        print(f"  Total test time: {stats['total_test_time']:.2f}s")
        print(f"  Sessions per second: {stats['sessions_per_second']:.2f}")
        
        if 'memory_increase_mb' in stats:
            print(f"  Memory increase: {stats['memory_increase_mb']} MB ({stats['memory_increase_percent']:.1f}%)")
        
        # Print errors if any
        if failed_sessions:
            print(f"\nERRORS:")
            error_counts = {}
            for session in failed_sessions:
                for error in session['errors']:
                    error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error}: {count} times")
        
        return stats
    else:
        print("No successful sessions!")
        return None

def main():
    """Run comprehensive load tests"""
    print("COMPREHENSIVE LOAD TEST FOR COMBOT BACKEND")
    print("Testing with OpenAI API and ML classification enabled")
    print(f"Target server: {BASE_URL}")
    
    all_results = []
    
    for scenario in TEST_SCENARIOS:
        users = scenario['users']
        sessions = scenario['sessions']
        
        result = run_load_test(users, sessions)
        if result:
            result['concurrent_users'] = users
            result['sessions_per_user'] = sessions
            all_results.append(result)
        
        # Wait between tests
        print(f"\nWaiting 30 seconds before next test...")
        time.sleep(30)
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY OF ALL TESTS")
    print(f"{'='*80}")
    
    for result in all_results:
        users = result['concurrent_users']
        success_rate = result['success_rate']
        avg_response = result['avg_response_time']
        sessions_per_sec = result['sessions_per_second']
        
        print(f"{users:2d} users: {success_rate:5.1f}% success, {avg_response:5.2f}s avg, {sessions_per_sec:5.2f} sessions/sec")
    
    # Save detailed results
    with open('comprehensive_load_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to comprehensive_load_test_results.json")

if __name__ == "__main__":
    main() 