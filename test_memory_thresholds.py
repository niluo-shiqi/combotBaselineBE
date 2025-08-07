#!/usr/bin/env python3
"""
Test Memory Thresholds and Automatic Cleanup
Tests the enhanced memory management with automatic cleanup
"""

import requests
import time
import json
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://3.144.114.76:8000"
TEST_USERS = 20  # Test with 20 users to trigger memory thresholds
MEMORY_CHECK_INTERVAL = 5  # Check memory every 5 seconds

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

def get_server_logs():
    """Get recent server logs to check for memory cleanup messages"""
    try:
        result = subprocess.run([
            "ssh", "-i", "~/.ssh/ec2-key.pem", 
            "ec2-user@3.144.114.76", 
            "sudo journalctl -u combot-enhanced --since '2 minutes ago' | grep -i 'memory\|cleanup\|threshold'"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting server logs: {e}")
    
    return None

def simulate_user_session(user_id):
    """Simulate a user session that triggers ML classification"""
    session_data = {
        'success': False,
        'response_times': [],
        'errors': [],
        'user_id': user_id
    }
    
    try:
        # Get initial message
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/chatbot/initial/", timeout=30)
        response_time = time.time() - start_time
        session_data['response_times'].append(response_time)
        
        if response.status_code != 200:
            session_data['errors'].append(f"Initial message failed: {response.status_code}")
            return session_data
        
        initial_data = response.json()
        
        # Send user message (triggers ML classification)
        user_input = f"Test user {user_id}: I want to return my shoes for a smaller size because they don't fit properly"
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
            session_data['errors'].append(f"User message failed: {response.status_code}")
            return session_data
        
        response_data = response.json()
        session_data['reply'] = response_data.get('reply', '')
        session_data['class_type'] = response_data.get('classType', '')
        
        session_data['success'] = True
        session_data['total_time'] = sum(session_data['response_times'])
        
    except requests.exceptions.Timeout:
        session_data['errors'].append("Request timeout")
    except requests.exceptions.ConnectionError:
        session_data['errors'].append("Connection error")
    except Exception as e:
        session_data['errors'].append(f"Unexpected error: {str(e)}")
    
    return session_data

def monitor_memory_during_test():
    """Monitor memory usage during the test"""
    memory_readings = []
    start_time = time.time()
    
    while True:
        memory = get_server_memory()
        if memory:
            current_time = time.time()
            memory_readings.append({
                'timestamp': current_time,
                'elapsed': current_time - start_time,
                'memory_mb': memory['used_mb'],
                'memory_percent': memory['usage_percent']
            })
            
            print(f"Memory: {memory['used_mb']}/{memory['total_mb']} MB ({memory['usage_percent']:.1f}%)")
            
            # Check for memory threshold triggers
            if memory['usage_percent'] > 75:
                print(f"⚠️  WARNING: Memory usage above 75% threshold")
            if memory['usage_percent'] > 85:
                print(f"🚨 CRITICAL: Memory usage above 85% threshold")
            if memory['usage_percent'] > 95:
                print(f"💥 EMERGENCY: Memory usage above 95% threshold")
        
        time.sleep(MEMORY_CHECK_INTERVAL)

def run_memory_threshold_test():
    """Run test to verify memory threshold monitoring"""
    print("MEMORY THRESHOLD TEST")
    print("Testing automatic memory cleanup with enhanced thresholds")
    print(f"Target server: {BASE_URL}")
    print(f"Test users: {TEST_USERS}")
    
    # Get initial memory state
    initial_memory = get_server_memory()
    if initial_memory:
        print(f"Initial memory: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
    
    # Start memory monitoring in background
    monitor_thread = threading.Thread(target=monitor_memory_during_test, daemon=True)
    monitor_thread.start()
    
    print(f"\nStarting {TEST_USERS} concurrent users...")
    start_time = time.time()
    
    # Execute user sessions
    with ThreadPoolExecutor(max_workers=TEST_USERS) as executor:
        future_to_user = {
            executor.submit(simulate_user_session, user_id): user_id
            for user_id in range(TEST_USERS)
        }
        
        all_sessions = []
        for future in as_completed(future_to_user):
            user_id = future_to_user[future]
            try:
                result = future.result()
                all_sessions.append(result)
                print(f"Completed user {user_id}")
            except Exception as e:
                print(f"User {user_id} failed: {e}")
    
    end_time = time.time()
    total_test_time = end_time - start_time
    
    # Get final memory state
    final_memory = get_server_memory()
    if final_memory:
        print(f"\nFinal memory: {final_memory['used_mb']}/{final_memory['total_mb']} MB ({final_memory['usage_percent']:.1f}%)")
    
    # Calculate statistics
    successful_sessions = [s for s in all_sessions if s['success']]
    failed_sessions = [s for s in all_sessions if not s['success']]
    
    print(f"\nTEST RESULTS:")
    print(f"  Total sessions: {len(all_sessions)}")
    print(f"  Successful: {len(successful_sessions)}")
    print(f"  Failed: {len(failed_sessions)}")
    print(f"  Success rate: {(len(successful_sessions) / len(all_sessions)) * 100:.1f}%")
    print(f"  Total test time: {total_test_time:.2f}s")
    
    if successful_sessions:
        all_response_times = []
        for session in successful_sessions:
            all_response_times.extend(session['response_times'])
        
        avg_response_time = sum(all_response_times) / len(all_response_times)
        print(f"  Average response time: {avg_response_time:.2f}s")
    
    # Check for cleanup messages in logs
    print(f"\nChecking for cleanup messages in logs...")
    logs = get_server_logs()
    if logs:
        print("Recent cleanup messages:")
        for line in logs.split('\n'):
            if line.strip():
                print(f"  {line}")
    else:
        print("  No cleanup messages found in recent logs")
    
    # Memory analysis
    if initial_memory and final_memory:
        memory_change = final_memory['used_mb'] - initial_memory['used_mb']
        memory_change_percent = final_memory['usage_percent'] - initial_memory['usage_percent']
        
        print(f"\nMEMORY ANALYSIS:")
        print(f"  Memory change: {memory_change:+d} MB ({memory_change_percent:+.1f}%)")
        
        if memory_change > 200:
            print("  ⚠️  WARNING: Large memory increase detected")
        elif memory_change < -100:
            print("  ✅ Good: Memory cleanup working")
        else:
            print("  ✅ Stable: Memory usage within normal range")
    
    # Check for errors
    if failed_sessions:
        print(f"\nERRORS:")
        error_counts = {}
        for session in failed_sessions:
            for error in session['errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        for error, count in error_counts.items():
            print(f"  {error}: {count} times")
    
    print(f"\n✅ Memory threshold test completed!")

if __name__ == "__main__":
    run_memory_threshold_test() 