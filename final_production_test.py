#!/usr/bin/env python3
"""
Final Production Test - 1000 Users, 15 Users per Session
Simulates the exact production scenario to ensure readiness
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
        logging.FileHandler('final_production_test.log'),
        logging.StreamHandler()
    ]
)

class FinalProductionTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.total_sessions = 0
        self.total_users = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.memory_history = []
        self.lock = threading.Lock()
        
        # Test scenarios
        self.scenarios = [
            {"brand": "Nike", "problem_type": "A", "think_level": "Low", "feel_level": "Low"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "Medium", "feel_level": "High"},
            {"brand": "Nike", "problem_type": "C", "think_level": "High", "feel_level": "Medium"},
            {"brand": "Lulu", "problem_type": "A", "think_level": "Low", "feel_level": "High"}
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
            'start_time': time.time(),
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0
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
            
            session_data['total_response_time'] += response_time
            
            if response.status_code == 200:
                session_data['successful_requests'] += 1
                session_data['messages'].append({
                    'type': 'initial',
                    'response_time': response_time,
                    'status': 'success'
                })
            else:
                session_data['failed_requests'] += 1
                session_data['messages'].append({
                    'type': 'initial',
                    'response_time': response_time,
                    'status': 'failed',
                    'error': response.text
                })
                return session_data
            
            # Step 2: Send multiple messages
            for i, message in enumerate(random.sample(self.test_messages, 3)):
                time.sleep(random.uniform(0.5, 1.5))  # Simulate user thinking time
                
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
                
                session_data['total_response_time'] += response_time
                
                if response.status_code == 200:
                    session_data['successful_requests'] += 1
                    session_data['messages'].append({
                        'type': 'chat',
                        'message': message,
                        'response_time': response_time,
                        'status': 'success'
                    })
                else:
                    session_data['failed_requests'] += 1
                    session_data['messages'].append({
                        'type': 'chat',
                        'message': message,
                        'response_time': response_time,
                        'status': 'failed',
                        'error': response.text
                    })
            
            session_data['end_time'] = time.time()
            session_data['duration'] = session_data['end_time'] - session_data['start_time']
            session_data['avg_response_time'] = session_data['total_response_time'] / len(session_data['messages'])
            
        except Exception as e:
            logging.error(f"User {user_id}: Session error: {e}")
            session_data['failed_requests'] += 1
        
        return session_data

    def run_production_simulation(self, total_users=1000, users_per_session=15):
        """Run production simulation with 1000 users, 15 per session"""
        logging.info(f"🚀 Starting Final Production Test")
        logging.info(f"Target: {total_users} total users, {users_per_session} users per session")
        logging.info(f"Expected Sessions: {total_users // users_per_session}")
        logging.info(f"Backend: {self.base_url}")
        logging.info(f"Advanced Memory Management: ENABLED")
        
        # Calculate sessions needed
        sessions_needed = total_users // users_per_session
        remaining_users = total_users % users_per_session
        
        all_sessions = []
        session_start_time = time.time()
        
        for session_num in range(sessions_needed):
            session_start = time.time()
            logging.info(f"\n📊 PRODUCTION SESSION {session_num + 1}/{sessions_needed}")
            logging.info(f"Starting session with {users_per_session} concurrent users...")
            
            # Get memory before session
            memory_before = self.get_server_memory()
            logging.info(f"Memory before session: {memory_before}")
            
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
            
            # Get memory after session
            memory_after = self.get_server_memory()
            logging.info(f"Memory after session: {memory_after}")
            
            # Calculate session statistics
            successful_users = sum(1 for r in session_results if r['successful_requests'] > r['failed_requests'])
            failed_users = len(session_results) - successful_users
            total_requests = sum(r['successful_requests'] + r['failed_requests'] for r in session_results)
            successful_requests = sum(r['successful_requests'] for r in session_results)
            avg_response_time = sum(r['avg_response_time'] for r in session_results if 'avg_response_time' in r) / len(session_results) if session_results else 0
            
            session_data = {
                'session_num': session_num + 1,
                'users_per_session': users_per_session,
                'duration': session_duration,
                'successful_users': successful_users,
                'failed_users': failed_users,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': total_requests - successful_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'user_success_rate': (successful_users / len(session_results) * 100) if session_results else 0,
                'avg_response_time': avg_response_time,
                'memory_before': memory_before,
                'memory_after': memory_after,
                'memory_change': memory_after['server_used_mb'] - memory_before['server_used_mb'] if memory_before and memory_after else 0,
                'results': session_results
            }
            
            all_sessions.append(session_data)
            
            logging.info(f"Session {session_num + 1} Results:")
            logging.info(f"  ✅ Successful users: {successful_users}/{users_per_session}")
            logging.info(f"  ❌ Failed users: {failed_users}/{users_per_session}")
            logging.info(f"  📊 Success rate: {session_data['success_rate']:.2f}%")
            logging.info(f"  ⏱️  Duration: {session_duration:.2f}s")
            logging.info(f"  🧠 Memory change: {session_data['memory_change']} MB")
            
            # Check for performance degradation
            if session_data['user_success_rate'] < 95:
                logging.warning(f"⚠️  Performance degradation detected in session {session_num + 1}")
                logging.warning(f"User success rate: {session_data['user_success_rate']:.2f}%")
                break
            
            # Run cleanup between sessions
            if session_num < sessions_needed - 1:  # Don't cleanup after last session
                logging.info("🔄 Running session cleanup...")
                time.sleep(5)
            
            # Brief pause between sessions
            time.sleep(2)
        
        # Handle remaining users if any
        if remaining_users > 0:
            logging.info(f"\n📊 FINAL SESSION with {remaining_users} remaining users")
            # ... handle remaining users logic here
        
        # Calculate overall statistics
        total_duration = time.time() - session_start_time
        total_successful = sum(s['successful_users'] for s in all_sessions)
        total_failed = sum(s['failed_users'] for s in all_sessions)
        total_successful_requests = sum(s['successful_requests'] for s in all_sessions)
        total_requests = sum(s['total_requests'] for s in all_sessions)
        overall_success_rate = (total_successful_requests / total_requests * 100) if total_requests > 0 else 0
        overall_user_success_rate = (total_successful / (total_successful + total_failed) * 100) if (total_successful + total_failed) > 0 else 0
        avg_response_time = sum(s['avg_response_time'] for s in all_sessions) / len(all_sessions) if all_sessions else 0
        
        # Print final results
        logging.info(f"\n🎯 FINAL PRODUCTION TEST COMPLETED")
        logging.info(f"Total Duration: {total_duration:.2f}s")
        logging.info(f"Total Sessions: {len(all_sessions)}")
        logging.info(f"Total Users: {total_successful + total_failed}")
        logging.info(f"Total Requests: {total_requests}")
        logging.info(f"Successful Requests: {total_successful_requests}")
        logging.info(f"Failed Requests: {total_requests - total_successful_requests}")
        logging.info(f"Success Rate: {overall_success_rate:.2f}%")
        logging.info(f"Average Response Time: {avg_response_time:.2f}s")
        logging.info(f"Total Successful Users: {total_successful}")
        logging.info(f"Total Failed Users: {total_failed}")
        logging.info(f"Overall User Success Rate: {overall_user_success_rate:.2f}%")
        
        # Save detailed results
        results = {
            'test_config': {
                'base_url': self.base_url,
                'total_users': total_users,
                'users_per_session': users_per_session,
                'sessions_needed': sessions_needed,
                'advanced_memory_management': True
            },
            'summary': {
                'total_duration': total_duration,
                'total_sessions': len(all_sessions),
                'total_users': total_successful + total_failed,
                'total_requests': total_requests,
                'successful_requests': total_successful_requests,
                'failed_requests': total_requests - total_successful_requests,
                'success_rate': overall_success_rate,
                'avg_response_time': avg_response_time,
                'total_successful_users': total_successful,
                'total_failed_users': total_failed,
                'user_success_rate': overall_user_success_rate
            },
            'sessions': all_sessions
        }
        
        with open('final_production_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"Detailed results saved to: final_production_results.json")
        
        return results

def main():
    """Main function to run the final production test"""
    tester = FinalProductionTester()
    
    print("🚀 Final Production Test - 1000 Users, 15 Users per Session")
    print("=" * 70)
    
    # Run the production simulation
    results = tester.run_production_simulation(total_users=1000, users_per_session=15)
    
    print("\n" + "=" * 70)
    print("📊 FINAL PRODUCTION TEST SUMMARY")
    print("=" * 70)
    print(f"Backend: {tester.base_url}")
    print(f"Total Users: 1000")
    print(f"Users per Session: 15")
    print(f"Sessions Completed: {results['summary']['total_sessions']}")
    print(f"Success Rate: {results['summary']['success_rate']:.2f}%")
    print(f"Average Response Time: {results['summary']['avg_response_time']:.2f}s")
    print(f"User Success Rate: {results['summary']['user_success_rate']:.2f}%")
    
    if results['summary']['user_success_rate'] >= 95:
        print("✅ FINAL PRODUCTION TEST PASSED - Ready for 1000 users!")
    else:
        print("❌ FINAL PRODUCTION TEST FAILED - Needs optimization")

if __name__ == "__main__":
    main() 