#!/usr/bin/env python3
"""
Consecutive 15 Users Test
Tests the server with multiple batches of 15 users to ensure proper cleanup and stability
"""

import requests
import time
import json
import threading
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://3.144.114.76:8000"
BATCH_SIZE = 15
NUM_BATCHES = 5
CLEANUP_DELAY = 30  # seconds between batches

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

def get_server_processes():
    """Get server process information"""
    try:
        result = subprocess.run([
            "ssh", "-i", "~/.ssh/ec2-key.pem", 
            "ec2-user@3.144.114.76", 
            "ps aux | grep -E '(gunicorn|python)' | grep -v grep"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting server processes: {e}")
    
    return None

def simulate_user_session(user_id, batch_id):
    """Simulate a complete user session"""
    session_data = {
        'success': False,
        'response_times': [],
        'errors': [],
        'user_id': user_id,
        'batch_id': batch_id
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
        user_input = f"Test user {user_id} from batch {batch_id}: I want to return my shoes for a smaller size"
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
        session_data['class_type'] = first_response.get('classType', '')
        
        # Step 3: Send second user message
        user_input2 = f"I want a size 6 instead of a size 9"
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
        
        # Step 4: Get closing message
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

def run_batch(batch_id, num_users):
    """Run a batch of user sessions"""
    print(f"\n{'='*60}")
    print(f"BATCH {batch_id}: {num_users} concurrent users")
    print(f"{'='*60}")
    
    # Get initial server state
    initial_memory = get_server_memory()
    initial_processes = get_server_processes()
    
    if initial_memory:
        print(f"Initial server memory: {initial_memory['used_mb']}/{initial_memory['total_mb']} MB ({initial_memory['usage_percent']:.1f}%)")
    
    if initial_processes:
        print(f"Initial server processes: {len(initial_processes.splitlines())} processes")
    
    start_time = time.time()
    all_sessions = []
    
    # Execute sessions with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        # Submit all tasks
        future_to_user = {
            executor.submit(simulate_user_session, user_id, batch_id): user_id
            for user_id in range(num_users)
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_user):
            user_id = future_to_user[future]
            try:
                result = future.result()
                all_sessions.append(result)
                completed += 1
                
                if completed % 5 == 0:
                    print(f"Completed {completed}/{num_users} sessions...")
                    
            except Exception as e:
                print(f"Session {user_id} failed: {e}")
    
    end_time = time.time()
    total_batch_time = end_time - start_time
    
    # Get final server state
    final_memory = get_server_memory()
    final_processes = get_server_processes()
    
    # Calculate statistics
    successful_sessions = [s for s in all_sessions if s['success']]
    failed_sessions = [s for s in all_sessions if not s['success']]
    
    if successful_sessions:
        all_response_times = []
        for session in successful_sessions:
            all_response_times.extend(session['response_times'])
        
        stats = {
            'batch_id': batch_id,
            'total_sessions': len(all_sessions),
            'successful_sessions': len(successful_sessions),
            'failed_sessions': len(failed_sessions),
            'success_rate': (len(successful_sessions) / len(all_sessions)) * 100,
            'avg_response_time': statistics.mean(all_response_times),
            'median_response_time': statistics.median(all_response_times),
            'min_response_time': min(all_response_times),
            'max_response_time': max(all_response_times),
            'total_batch_time': total_batch_time,
            'sessions_per_second': len(all_sessions) / total_batch_time,
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'initial_processes': initial_processes,
            'final_processes': final_processes
        }
        
        if final_memory and initial_memory:
            stats['memory_increase_mb'] = final_memory['used_mb'] - initial_memory['used_mb']
            stats['memory_increase_percent'] = final_memory['usage_percent'] - initial_memory['usage_percent']
        
        # Print results
        print(f"\nBATCH {batch_id} RESULTS:")
        print(f"  Total sessions: {stats['total_sessions']}")
        print(f"  Successful: {stats['successful_sessions']}")
        print(f"  Failed: {stats['failed_sessions']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Average response time: {stats['avg_response_time']:.2f}s")
        print(f"  Median response time: {stats['median_response_time']:.2f}s")
        print(f"  Min response time: {stats['min_response_time']:.2f}s")
        print(f"  Max response time: {stats['max_response_time']:.2f}s")
        print(f"  Total batch time: {stats['total_batch_time']:.2f}s")
        print(f"  Sessions per second: {stats['sessions_per_second']:.2f}")
        
        if 'memory_increase_mb' in stats:
            print(f"  Memory change: {stats['memory_increase_mb']:+d} MB ({stats['memory_increase_percent']:+.1f}%)")
        
        # Check for memory leaks
        if 'memory_increase_mb' in stats and stats['memory_increase_mb'] > 100:
            print(f"⚠️  WARNING: Large memory increase detected: {stats['memory_increase_mb']} MB")
        
        # Check for process leaks
        if final_processes and initial_processes:
            initial_count = len(initial_processes.splitlines())
            final_count = len(final_processes.splitlines())
            if final_count > initial_count + 5:
                print(f"⚠️  WARNING: Process count increased: {initial_count} → {final_count}")
        
        # Print errors if any
        if failed_sessions:
            print(f"\nERRORS in batch {batch_id}:")
            error_counts = {}
            for session in failed_sessions:
                for error in session['errors']:
                    error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error}: {count} times")
        
        return stats
    else:
        print(f"❌ BATCH {batch_id}: No successful sessions!")
        return None

def main():
    """Run consecutive batches of 15 users"""
    print("CONSECUTIVE 15 USERS TEST")
    print("Testing server stability and cleanup with multiple batches")
    print(f"Target server: {BASE_URL}")
    print(f"Batch size: {BATCH_SIZE} users")
    print(f"Number of batches: {NUM_BATCHES}")
    print(f"Cleanup delay between batches: {CLEANUP_DELAY} seconds")
    
    all_batch_results = []
    
    for batch_id in range(1, NUM_BATCHES + 1):
        print(f"\n{'='*80}")
        print(f"STARTING BATCH {batch_id}/{NUM_BATCHES}")
        print(f"{'='*80}")
        
        # Run the batch
        batch_result = run_batch(batch_id, BATCH_SIZE)
        
        if batch_result:
            all_batch_results.append(batch_result)
        
        # Wait between batches for cleanup
        if batch_id < NUM_BATCHES:
            print(f"\nWaiting {CLEANUP_DELAY} seconds for cleanup before next batch...")
            time.sleep(CLEANUP_DELAY)
            
            # Check server health after cleanup
            print("Checking server health after cleanup...")
            health_memory = get_server_memory()
            health_processes = get_server_processes()
            
            if health_memory:
                print(f"Post-cleanup memory: {health_memory['used_mb']}/{health_memory['total_mb']} MB ({health_memory['usage_percent']:.1f}%)")
            
            if health_processes:
                print(f"Post-cleanup processes: {len(health_processes.splitlines())} processes")
    
    # Print summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    
    if all_batch_results:
        total_sessions = sum(r['total_sessions'] for r in all_batch_results)
        total_successful = sum(r['successful_sessions'] for r in all_batch_results)
        total_failed = sum(r['failed_sessions'] for r in all_batch_results)
        overall_success_rate = (total_successful / total_sessions) * 100 if total_sessions > 0 else 0
        
        print(f"Total sessions across all batches: {total_sessions}")
        print(f"Total successful: {total_successful}")
        print(f"Total failed: {total_failed}")
        print(f"Overall success rate: {overall_success_rate:.1f}%")
        
        # Check for memory trends
        memory_changes = [r.get('memory_increase_mb', 0) for r in all_batch_results if 'memory_increase_mb' in r]
        if memory_changes:
            avg_memory_change = statistics.mean(memory_changes)
            print(f"Average memory change per batch: {avg_memory_change:+.1f} MB")
            
            if avg_memory_change > 50:
                print("⚠️  WARNING: Consistent memory increase detected - potential memory leak")
            elif avg_memory_change < -50:
                print("✅ Good: Memory is being cleaned up between batches")
            else:
                print("✅ Stable: Memory usage is consistent between batches")
        
        # Check for stability
        success_rates = [r['success_rate'] for r in all_batch_results]
        if len(success_rates) > 1:
            success_rate_std = statistics.stdev(success_rates)
            print(f"Success rate stability (std dev): {success_rate_std:.1f}%")
            
            if success_rate_std < 5:
                print("✅ Excellent: Very stable performance across batches")
            elif success_rate_std < 10:
                print("✅ Good: Stable performance across batches")
            else:
                print("⚠️  WARNING: Inconsistent performance across batches")
    
    # Save detailed results
    with open('consecutive_15_users_results.json', 'w') as f:
        json.dump(all_batch_results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to consecutive_15_users_results.json")
    
    # Final server health check
    print(f"\n{'='*40}")
    print("FINAL SERVER HEALTH CHECK")
    print(f"{'='*40}")
    
    final_memory = get_server_memory()
    final_processes = get_server_processes()
    
    if final_memory:
        print(f"Final memory: {final_memory['used_mb']}/{final_memory['total_mb']} MB ({final_memory['usage_percent']:.1f}%)")
    
    if final_processes:
        print(f"Final processes: {len(final_processes.splitlines())} processes")
    
    print("✅ Test completed successfully!")

if __name__ == "__main__":
    main() 