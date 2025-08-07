#!/usr/bin/env python3
"""
Advanced Load Testing Script for Combot Backend (t3.large)
Tests 8 users per session with cleanups between sessions indefinitely
Designed for advanced memory management system
"""

import requests
import time
import threading
import json
import random
import psutil
import subprocess
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test_results.log'),
        logging.StreamHandler()
    ]
)

class AdvancedLoadTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.session_count = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.memory_usage = []
        self.lock = threading.Lock()
        
        # Test scenarios
        self.scenarios = [
            {
                "brand": "Nike",
                "problem_type": "A",
                "think_level": "Low",
                "feel_level": "Low"
            },
            {
                "brand": "Lulu",
                "problem_type": "B", 
                "think_level": "Medium",
                "feel_level": "High"
            },
            {
                "brand": "Nike",
                "problem_type": "C",
                "think_level": "High",
                "feel_level": "Medium"
            },
            {
                "brand": "Lulu",
                "problem_type": "A",
                "think_level": "Low",
                "feel_level": "High"
            }
        ]
        
        # Test messages
        self.test_messages = [
            "I received a defective Nike shoe that fell apart after 2 weeks",
            "My Lulu package was delayed by 3 weeks and customer service was rude",
            "The Nike app crashed and I lost my order",
            "Lulu sent me the wrong size and refused to exchange it",
            "My Nike shoes have a manufacturing defect in the sole",
            "Lulu's website charged me twice for the same order",
            "The Nike store employee was very unhelpful with my return",
            "Lulu's delivery was late and the package was damaged"
        ]

    def get_memory_usage(self):
        """Get current memory usage from the server"""
        try:
            # Get local memory usage
            memory = psutil.virtual_memory()
            return {
                'local_percent': memory.percent,
                'local_used_gb': memory.used / (1024**3),
                'local_available_gb': memory.available / (1024**3)
            }
        except Exception as e:
            logging.error(f"Error getting memory usage: {e}")
            return None

    def get_server_memory(self):
        """Get memory usage from the server via SSH"""
        try:
            result = subprocess.run([
                'ssh', '-i', '~/.ssh/ec2-key.pem', 
                'ec2-user@3.144.114.76',
                'free -m | grep Mem'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    total = int(parts[1])
                    used = int(parts[2])
                    percent = (used / total) * 100
                    return {
                        'server_total_mb': total,
                        'server_used_mb': used,
                        'server_percent': percent
                    }
        except Exception as e:
            logging.error(f"Error getting server memory: {e}")
        return None

    def simulate_user_session(self, user_id, scenario):
        """Simulate a complete user session"""
        session_data = {
            'session_id': f"user_{user_id}_{int(time.time())}",
            'scenario': scenario,
            'messages': [],
            'start_time': time.time()
        }
        
        try:
            # Step 1: Get initial message
            if scenario['brand'] == 'Nike':
                initial_url = f"{self.base_url}/api/chatbot/initial/"
            else:
                initial_url = f"{self.base_url}/api/lulu/initial/"
            
            start_time = time.time()
            response = requests.get(initial_url, timeout=30)
            response_time = time.time() - start_time
            
            with self.lock:
                self.total_requests += 1
                self.response_times.append(response_time)
                
            if response.status_code == 200:
                with self.lock:
                    self.successful_requests += 1
                session_data['messages'].append({
                    'type': 'initial',
                    'response_time': response_time,
                    'status': 'success'
                })
                logging.info(f"User {user_id}: Initial message successful ({response_time:.2f}s)")
            else:
                with self.lock:
                    self.failed_requests += 1
                session_data['messages'].append({
                    'type': 'initial',
                    'response_time': response_time,
                    'status': 'failed',
                    'error': response.text
                })
                logging.error(f"User {user_id}: Initial message failed ({response.status_code})")
                return session_data
            
            # Step 2: Send multiple messages
            for i, message in enumerate(random.sample(self.test_messages, 3)):
                time.sleep(random.uniform(1, 3))  # Simulate user thinking time
                
                message_data = {
                    'message': message,
                    'index': i + 1,
                    'timer': random.randint(30, 120),
                    'chatLog': json.dumps(session_data['messages']),
                    'classType': scenario['brand'],
                    'messageTypeLog': json.dumps([{'type': 'user', 'timestamp': time.time()}])
                }
                
                if scenario['brand'] == 'Nike':
                    chat_url = f"{self.base_url}/api/chatbot/"
                else:
                    chat_url = f"{self.base_url}/api/lulu/"
                
                start_time = time.time()
                response = requests.post(chat_url, json=message_data, timeout=30)
                response_time = time.time() - start_time
                
                with self.lock:
                    self.total_requests += 1
                    self.response_times.append(response_time)
                
                if response.status_code == 200:
                    with self.lock:
                        self.successful_requests += 1
                    session_data['messages'].append({
                        'type': 'chat',
                        'message': message,
                        'response_time': response_time,
                        'status': 'success'
                    })
                    logging.info(f"User {user_id}: Message {i+1} successful ({response_time:.2f}s)")
                else:
                    with self.lock:
                        self.failed_requests += 1
                    session_data['messages'].append({
                        'type': 'chat',
                        'message': message,
                        'response_time': response_time,
                        'status': 'failed',
                        'error': response.text
                    })
                    logging.error(f"User {user_id}: Message {i+1} failed ({response.status_code})")
            
            session_data['end_time'] = time.time()
            session_data['duration'] = session_data['end_time'] - session_data['start_time']
            
        except Exception as e:
            logging.error(f"User {user_id}: Session error: {e}")
            with self.lock:
                self.failed_requests += 1
        
        return session_data

    def run_session_cleanup(self):
        """Run cleanup between sessions"""
        logging.info("🔄 Running session cleanup...")
        
        # Get memory usage before cleanup
        memory_before = self.get_server_memory()
        logging.info(f"Memory before cleanup: {memory_before}")
        
        # Wait for cleanup
        time.sleep(5)
        
        # Get memory usage after cleanup
        memory_after = self.get_server_memory()
        logging.info(f"Memory after cleanup: {memory_after}")
        
        if memory_before and memory_after:
            memory_freed = memory_before['server_used_mb'] - memory_after['server_used_mb']
            logging.info(f"Memory freed during cleanup: {memory_freed} MB")
        
        logging.info("✅ Session cleanup completed")

    def run_load_test(self, sessions=10, users_per_session=8):
        """Run the main load test"""
        logging.info(f"🚀 Starting Advanced Load Test")
        logging.info(f"Target: {sessions} sessions, {users_per_session} users per session")
        logging.info(f"Backend: {self.base_url}")
        logging.info(f"Advanced Memory Management: ENABLED")
        
        all_sessions = []
        session_start_time = time.time()
        
        for session_num in range(sessions):
            session_start = time.time()
            logging.info(f"\n📊 SESSION {session_num + 1}/{sessions}")
            logging.info(f"Starting session with {users_per_session} concurrent users...")
            
            # Create threads for concurrent users
            threads = []
            session_results = []
            
            for user_id in range(users_per_session):
                scenario = random.choice(self.scenarios)
                thread = threading.Thread(
                    target=lambda u=user_id, s=scenario: session_results.append(
                        self.simulate_user_session(u, s)
                    )
                )
                threads.append(thread)
            
            # Start all threads
            for thread in threads:
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            session_duration = time.time() - session_start
            logging.info(f"Session {session_num + 1} completed in {session_duration:.2f}s")
            
            # Calculate session statistics
            successful_in_session = sum(1 for r in session_results if r['messages'] and all(m['status'] == 'success' for m in r['messages']))
            failed_in_session = len(session_results) - successful_in_session
            
            logging.info(f"Session {session_num + 1} Results:")
            logging.info(f"  ✅ Successful users: {successful_in_session}/{users_per_session}")
            logging.info(f"  ❌ Failed users: {failed_in_session}/{users_per_session}")
            
            all_sessions.append({
                'session_num': session_num + 1,
                'duration': session_duration,
                'successful_users': successful_in_session,
                'failed_users': failed_in_session,
                'results': session_results
            })
            
            # Run cleanup between sessions
            if session_num < sessions - 1:  # Don't cleanup after last session
                self.run_session_cleanup()
            
            # Brief pause between sessions
            time.sleep(2)
        
        # Calculate overall statistics
        total_duration = time.time() - session_start_time
        total_successful = sum(s['successful_users'] for s in all_sessions)
        total_failed = sum(s['failed_users'] for s in all_sessions)
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        # Print final results
        logging.info(f"\n🎯 LOAD TEST COMPLETED")
        logging.info(f"Total Duration: {total_duration:.2f}s")
        logging.info(f"Total Requests: {self.total_requests}")
        logging.info(f"Successful Requests: {self.successful_requests}")
        logging.info(f"Failed Requests: {self.failed_requests}")
        logging.info(f"Success Rate: {(self.successful_requests/self.total_requests*100):.2f}%")
        logging.info(f"Average Response Time: {avg_response_time:.2f}s")
        logging.info(f"Total Successful Users: {total_successful}")
        logging.info(f"Total Failed Users: {total_failed}")
        logging.info(f"Overall User Success Rate: {(total_successful/(total_successful+total_failed)*100):.2f}%")
        
        # Save detailed results
        results = {
            'test_config': {
                'base_url': self.base_url,
                'sessions': sessions,
                'users_per_session': users_per_session,
                'advanced_memory_management': True
            },
            'summary': {
                'total_duration': total_duration,
                'total_requests': self.total_requests,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'success_rate': self.successful_requests/self.total_requests*100,
                'avg_response_time': avg_response_time,
                'total_successful_users': total_successful,
                'total_failed_users': total_failed,
                'user_success_rate': total_successful/(total_successful+total_failed)*100
            },
            'sessions': all_sessions,
            'response_times': self.response_times
        }
        
        with open('load_test_detailed_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"Detailed results saved to: load_test_detailed_results.json")
        
        return results

def main():
    """Main function to run the load test"""
    tester = AdvancedLoadTester()
    
    print("🚀 Advanced Load Testing for t3.large with Memory Management")
    print("=" * 60)
    
    # Run the load test
    results = tester.run_load_test(sessions=5, users_per_session=8)
    
    print("\n" + "=" * 60)
    print("📊 LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Backend: {tester.base_url}")
    print(f"Sessions: 5")
    print(f"Users per Session: 8")
    print(f"Total Users: 40")
    print(f"Success Rate: {results['summary']['success_rate']:.2f}%")
    print(f"Average Response Time: {results['summary']['avg_response_time']:.2f}s")
    print(f"User Success Rate: {results['summary']['user_success_rate']:.2f}%")
    
    if results['summary']['user_success_rate'] >= 95:
        print("✅ LOAD TEST PASSED - Backend can handle 8 users per session!")
    else:
        print("❌ LOAD TEST FAILED - Backend needs optimization")

if __name__ == "__main__":
    main() 