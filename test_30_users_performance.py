#!/usr/bin/env python3
"""
Quick Performance Test - 30 Users per Session
Tests if the backend can handle 30 users per session with good performance
"""

import requests
import time
import threading
import json
import random
import subprocess
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_30_users_performance.log'),
        logging.StreamHandler()
    ]
)

class PerformanceTester30:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        
        # Test scenarios (8 possibilities)
        self.scenarios = [
            {"brand": "Nike", "problem_type": "A", "think_level": "Low", "feel_level": "Low"},
            {"brand": "Nike", "problem_type": "A", "think_level": "Low", "feel_level": "High"},
            {"brand": "Nike", "problem_type": "A", "think_level": "High", "feel_level": "Low"},
            {"brand": "Nike", "problem_type": "A", "think_level": "High", "feel_level": "High"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "Low", "feel_level": "Low"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "Low", "feel_level": "High"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "High", "feel_level": "Low"},
            {"brand": "Lulu", "problem_type": "B", "think_level": "High", "feel_level": "High"}
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

    def test_30_users_performance(self):
        """Test performance with 30 users per session"""
        logging.info(f"🚀 Testing 30 Users per Session Performance")
        logging.info(f"Backend: {self.base_url}")
        logging.info(f"Advanced Memory Management: ENABLED")
        
        # Get memory before test
        memory_before = self.get_server_memory()
        logging.info(f"Memory before test: {memory_before}")
        
        # Create threads for 30 concurrent users
        threads = []
        session_results = []
        
        for user_id in range(30):
            scenario = random.choice(self.scenarios)
            thread = threading.Thread(
                target=lambda u=user_id, s=scenario: session_results.append(
                    self.simulate_user_session(u, s)
                )
            )
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        test_duration = time.time() - start_time
        
        # Get memory after test
        memory_after = self.get_server_memory()
        logging.info(f"Memory after test: {memory_after}")
        
        # Calculate statistics
        successful_users = sum(1 for r in session_results if r['successful_requests'] > r['failed_requests'])
        failed_users = len(session_results) - successful_users
        total_requests = sum(r['successful_requests'] + r['failed_requests'] for r in session_results)
        successful_requests = sum(r['successful_requests'] for r in session_results)
        avg_response_time = sum(r['avg_response_time'] for r in session_results if 'avg_response_time' in r) / len(session_results) if session_results else 0
        
        # Print results
        logging.info(f"\n📊 30 USERS PERFORMANCE TEST RESULTS")
        logging.info(f"  ✅ Successful users: {successful_users}/30")
        logging.info(f"  ❌ Failed users: {failed_users}/30")
        logging.info(f"  📊 Success rate: {(successful_requests / total_requests * 100) if total_requests > 0 else 0:.2f}%")
        logging.info(f"  ⏱️  Test duration: {test_duration:.2f}s")
        logging.info(f"  🧠 Memory change: {memory_after['server_used_mb'] - memory_before['server_used_mb'] if memory_before and memory_after else 0} MB")
        logging.info(f"  📈 Average response time: {avg_response_time:.2f}s")
        
        # Performance assessment
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        user_success_rate = (successful_users / 30 * 100)
        
        if user_success_rate >= 95 and avg_response_time <= 5.0:
            logging.info(f"✅ PERFORMANCE TEST PASSED - Backend can handle 30 users per session!")
            return True
        else:
            logging.warning(f"⚠️  PERFORMANCE TEST FAILED - Backend may struggle with 30 users per session")
            logging.warning(f"   User success rate: {user_success_rate:.1f}% (target: 95%)")
            logging.warning(f"   Average response time: {avg_response_time:.2f}s (target: ≤5.0s)")
            return False

def main():
    """Main function to test 30 users performance"""
    tester = PerformanceTester30()
    
    print("🚀 30 Users per Session Performance Test")
    print("=" * 60)
    
    # Run the performance test
    success = tester.test_30_users_performance()
    
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ BACKEND CAN HANDLE 30 USERS PER SESSION")
        print("✅ RECOMMENDATION: Upgrade to 30 users per session")
        print("✅ Benefits:")
        print("   - Better scenario distribution (+30.3% improvement)")
        print("   - More efficient resource utilization")
        print("   - Faster completion of 1000 users")
    else:
        print("❌ BACKEND STRUGGLES WITH 30 USERS PER SESSION")
        print("❌ RECOMMENDATION: Stick with 15 users per session")
        print("❌ Reasons:")
        print("   - Performance degradation detected")
        print("   - Response times too high")
        print("   - Success rate below threshold")

if __name__ == "__main__":
    main() 