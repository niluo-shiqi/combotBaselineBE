#!/usr/bin/env python3
"""
Validate Performance Improvements Test
Tests the server with 20 users to validate the timeout fixes
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
from datetime import datetime

# Configuration
BASE_URL = "http://3.144.114.76:8000"
TEST_USERS = 20
SESSIONS_PER_USER = 3
TOTAL_SESSIONS = TEST_USERS * SESSIONS_PER_USER

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
        'session_id': session_id,
        'start_time': time.time()
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
        
        # Session completed successfully
        session_data['success'] = True
        session_data['total_time'] = time.time() - session_data['start_time']
        
        return session_data
        
    except requests.exceptions.Timeout:
        session_data['errors'].append("Request timeout")
        session_data['total_time'] = time.time() - session_data['start_time']
        return session_data
    except Exception as e:
        session_data['errors'].append(f"Unexpected error: {str(e)}")
        session_data['total_time'] = time.time() - session_data['start_time']
        return session_data

def run_validation_test():
    """Run the validation test with 20 users"""
    print("=" * 80)
    print("VALIDATION TEST: Performance Improvements with 20 Users")
    print("=" * 80)
    print(f"Target server: {BASE_URL}")
    print(f"Test configuration: {TEST_USERS} users, {SESSIONS_PER_USER} sessions each")
    print(f"Total sessions: {TOTAL_SESSIONS}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get initial memory
    initial_memory = get_server_memory()
    if initial_memory:
        print(f"Initial server memory: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
    else:
        print("Could not get initial server memory")
    print()
    
    # Run all sessions concurrently
    all_sessions = []
    completed_sessions = 0
    successful_sessions = 0
    failed_sessions = 0
    timeout_errors = 0
    total_response_times = []
    
    print("Starting concurrent sessions...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=TEST_USERS) as executor:
        # Submit all sessions
        future_to_session = {}
        for user_id in range(1, TEST_USERS + 1):
            for session_id in range(1, SESSIONS_PER_USER + 1):
                future = executor.submit(simulate_user_session, user_id, session_id)
                future_to_session[future] = (user_id, session_id)
        
        # Collect results as they complete
        for future in as_completed(future_to_session):
            user_id, session_id = future_to_session[future]
            session_data = future.result()
            all_sessions.append(session_data)
            
            completed_sessions += 1
            
            if session_data['success']:
                successful_sessions += 1
                total_response_times.extend(session_data['response_times'])
            else:
                failed_sessions += 1
                if "timeout" in str(session_data['errors']).lower():
                    timeout_errors += 1
            
            # Progress update
            if completed_sessions % 10 == 0:
                print(f"Completed {completed_sessions}/{TOTAL_SESSIONS} sessions...")
    
    end_time = time.time()
    total_test_time = end_time - start_time
    
    # Get final memory
    final_memory = get_server_memory()
    
    # Calculate statistics
    success_rate = (successful_sessions / TOTAL_SESSIONS) * 100 if TOTAL_SESSIONS > 0 else 0
    avg_response_time = statistics.mean(total_response_times) if total_response_times else 0
    median_response_time = statistics.median(total_response_times) if total_response_times else 0
    min_response_time = min(total_response_times) if total_response_times else 0
    max_response_time = max(total_response_times) if total_response_times else 0
    
    # Memory change
    memory_change_mb = 0
    memory_change_percent = 0
    if initial_memory and final_memory:
        memory_change_mb = final_memory['used_mb'] - initial_memory['used_mb']
        memory_change_percent = (memory_change_mb / initial_memory['total_mb']) * 100
    
    # Print results
    print("\n" + "=" * 80)
    print("VALIDATION TEST RESULTS")
    print("=" * 80)
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("PERFORMANCE METRICS:")
    print(f"  Total sessions: {TOTAL_SESSIONS}")
    print(f"  Successful: {successful_sessions}")
    print(f"  Failed: {failed_sessions}")
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Timeout errors: {timeout_errors}")
    print()
    
    print("RESPONSE TIMES:")
    print(f"  Average response time: {avg_response_time:.2f}s")
    print(f"  Median response time: {median_response_time:.2f}s")
    print(f"  Min response time: {min_response_time:.2f}s")
    print(f"  Max response time: {max_response_time:.2f}s")
    print()
    
    print("TEST DURATION:")
    print(f"  Total test time: {total_test_time:.2f}s")
    print(f"  Sessions per second: {TOTAL_SESSIONS / total_test_time:.2f}")
    print()
    
    print("MEMORY USAGE:")
    if initial_memory and final_memory:
        print(f"  Initial memory: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
        print(f"  Final memory: {final_memory['used_mb']}/{final_memory['total_mb']} MB ({final_memory['usage_percent']:.1f}%)")
        print(f"  Memory change: {memory_change_mb:+d} MB ({memory_change_percent:+.1f}%)")
    else:
        print("  Memory monitoring unavailable")
    print()
    
    print("ERROR ANALYSIS:")
    if failed_sessions > 0:
        error_types = {}
        for session in all_sessions:
            if not session['success']:
                for error in session['errors']:
                    error_type = error.split(':')[0] if ':' in error else error
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in error_types.items():
            print(f"  {error_type}: {count} times")
    else:
        print("  No errors occurred")
    print()
    
    # Performance assessment
    print("PERFORMANCE ASSESSMENT:")
    if success_rate >= 95:
        print("  ✅ EXCELLENT: Success rate above 95%")
    elif success_rate >= 90:
        print("  ✅ GOOD: Success rate above 90%")
    elif success_rate >= 80:
        print("  ⚠️  ACCEPTABLE: Success rate above 80%")
    else:
        print("  ❌ POOR: Success rate below 80%")
    
    if timeout_errors == 0:
        print("  ✅ EXCELLENT: No timeout errors")
    elif timeout_errors <= 2:
        print("  ✅ GOOD: Minimal timeout errors")
    elif timeout_errors <= 5:
        print("  ⚠️  ACCEPTABLE: Some timeout errors")
    else:
        print("  ❌ POOR: Too many timeout errors")
    
    if avg_response_time <= 5:
        print("  ✅ EXCELLENT: Fast response times")
    elif avg_response_time <= 10:
        print("  ✅ GOOD: Reasonable response times")
    elif avg_response_time <= 15:
        print("  ⚠️  ACCEPTABLE: Slow response times")
    else:
        print("  ❌ POOR: Very slow response times")
    print()
    
    # Save detailed results
    results = {
        'test_config': {
            'users': TEST_USERS,
            'sessions_per_user': SESSIONS_PER_USER,
            'total_sessions': TOTAL_SESSIONS,
            'start_time': datetime.now().isoformat(),
            'base_url': BASE_URL
        },
        'performance_metrics': {
            'total_sessions': TOTAL_SESSIONS,
            'successful_sessions': successful_sessions,
            'failed_sessions': failed_sessions,
            'success_rate': success_rate,
            'timeout_errors': timeout_errors,
            'avg_response_time': avg_response_time,
            'median_response_time': median_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'total_test_time': total_test_time,
            'sessions_per_second': TOTAL_SESSIONS / total_test_time
        },
        'memory_usage': {
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'memory_change_mb': memory_change_mb,
            'memory_change_percent': memory_change_percent
        },
        'all_sessions': all_sessions
    }
    
    filename = f"validation_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Detailed results saved to: {filename}")
    print("=" * 80)

if __name__ == "__main__":
    run_validation_test() 