#!/usr/bin/env python3
"""
Optimal User Load Testing for t3.large Backend
Tests different user loads to find maximum and optimal users per session
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
        logging.FileHandler('optimal_user_test.log'),
        logging.StreamHandler()
    ]
)

class OptimalUserTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.results = {}
        
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

    def test_user_load(self, users_per_session, sessions=3):
        """Test a specific user load"""
        logging.info(f"🧪 Testing {users_per_session} users per session ({sessions} sessions)")
        
        all_sessions = []
        total_start_time = time.time()
        
        for session_num in range(sessions):
            session_start = time.time()
            logging.info(f"📊 Session {session_num + 1}/{sessions} with {users_per_session} users")
            
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
            
            # Cleanup between sessions
            if session_num < sessions - 1:
                logging.info("🔄 Running cleanup between sessions...")
                time.sleep(5)
        
        total_duration = time.time() - total_start_time
        
        # Calculate overall statistics
        total_successful_users = sum(s['successful_users'] for s in all_sessions)
        total_failed_users = sum(s['failed_users'] for s in all_sessions)
        total_successful_requests = sum(s['successful_requests'] for s in all_sessions)
        total_requests = sum(s['total_requests'] for s in all_sessions)
        overall_success_rate = (total_successful_requests / total_requests * 100) if total_requests > 0 else 0
        overall_user_success_rate = (total_successful_users / (total_successful_users + total_failed_users) * 100) if (total_successful_users + total_failed_users) > 0 else 0
        avg_response_time = sum(s['avg_response_time'] for s in all_sessions) / len(all_sessions) if all_sessions else 0
        
        result = {
            'users_per_session': users_per_session,
            'sessions': sessions,
            'total_duration': total_duration,
            'total_successful_users': total_successful_users,
            'total_failed_users': total_failed_users,
            'total_successful_requests': total_successful_requests,
            'total_requests': total_requests,
            'overall_success_rate': overall_success_rate,
            'overall_user_success_rate': overall_user_success_rate,
            'avg_response_time': avg_response_time,
            'sessions_data': all_sessions
        }
        
        logging.info(f"🎯 {users_per_session} users per session - Final Results:")
        logging.info(f"  📊 Overall success rate: {overall_success_rate:.2f}%")
        logging.info(f"  👥 User success rate: {overall_user_success_rate:.2f}%")
        logging.info(f"  ⏱️  Average response time: {avg_response_time:.2f}s")
        logging.info(f"  🕐 Total duration: {total_duration:.2f}s")
        
        return result

    def find_optimal_load(self):
        """Find the optimal user load"""
        logging.info("🚀 Starting Optimal User Load Testing")
        logging.info(f"Backend: {self.base_url}")
        logging.info(f"Advanced Memory Management: ENABLED")
        
        # Test different user loads
        user_loads = [4, 8, 12, 16, 20, 24, 32, 40, 50]
        
        for user_load in user_loads:
            logging.info(f"\n{'='*60}")
            logging.info(f"🧪 TESTING {user_load} USERS PER SESSION")
            logging.info(f"{'='*60}")
            
            try:
                result = self.test_user_load(user_load, sessions=2)
                self.results[user_load] = result
                
                # Check if we've hit the breaking point
                if result['overall_user_success_rate'] < 95:
                    logging.warning(f"⚠️  {user_load} users per session shows degradation (<95% success)")
                    break
                    
            except Exception as e:
                logging.error(f"❌ Error testing {user_load} users: {e}")
                break
        
        # Analyze results
        self.analyze_results()

    def analyze_results(self):
        """Analyze the test results to find optimal load"""
        logging.info(f"\n{'='*60}")
        logging.info("📊 OPTIMAL LOAD ANALYSIS")
        logging.info(f"{'='*60}")
        
        if not self.results:
            logging.error("No results to analyze")
            return
        
        # Find optimal load
        optimal_load = None
        max_success_rate = 0
        best_response_time = float('inf')
        
        for user_load, result in self.results.items():
            success_rate = result['overall_user_success_rate']
            response_time = result['avg_response_time']
            
            logging.info(f"\n👥 {user_load} users per session:")
            logging.info(f"  ✅ Success rate: {success_rate:.2f}%")
            logging.info(f"  ⏱️  Avg response time: {response_time:.2f}s")
            logging.info(f"  🕐 Total duration: {result['total_duration']:.2f}s")
            
            # Find optimal based on success rate and response time
            if success_rate >= 95 and response_time < best_response_time:
                optimal_load = user_load
                max_success_rate = success_rate
                best_response_time = response_time
        
        # Find maximum load
        max_load = max(self.results.keys()) if self.results else 0
        max_load_success = self.results[max_load]['overall_user_success_rate'] if max_load in self.results else 0
        
        logging.info(f"\n🎯 OPTIMAL LOAD RECOMMENDATIONS:")
        logging.info(f"  🏆 Optimal users per session: {optimal_load}")
        logging.info(f"  📈 Optimal success rate: {max_success_rate:.2f}%")
        logging.info(f"  ⚡ Optimal response time: {best_response_time:.2f}s")
        logging.info(f"  🚀 Maximum users per session: {max_load}")
        logging.info(f"  📊 Maximum load success rate: {max_load_success:.2f}%")
        
        # Save detailed results
        with open('optimal_user_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logging.info(f"Detailed results saved to: optimal_user_results.json")

def main():
    """Main function to run the optimal user load test"""
    tester = OptimalUserTester()
    
    print("🚀 Optimal User Load Testing for t3.large with Memory Management")
    print("=" * 70)
    
    # Run the optimal load test
    tester.find_optimal_load()
    
    print("\n" + "=" * 70)
    print("📊 OPTIMAL USER LOAD TESTING COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main() 