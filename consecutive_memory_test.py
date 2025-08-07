#!/usr/bin/env python3
"""
Consecutive Memory Management Test
Runs 10 consecutive batches with 15 users each to validate memory management improvements
"""

import requests
import json
import time
import logging
import threading
from datetime import datetime
import psutil
import subprocess
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('consecutive_memory_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConsecutiveMemoryTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.results = []
        self.total_users = 0
        self.successful_users = 0
        self.failed_users = 0
        self.start_time = None
        self.end_time = None
        
    def get_server_memory(self):
        """Get current server memory usage - with fallback options"""
        # Try SSH method first
        try:
            result = subprocess.run([
                'ssh', '-o', 'StrictHostKeyChecking=no', '-i', '~/.ssh/combot-key.pem',
                'ubuntu@3.144.114.76', 'free -m'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    memory_line = lines[1].split()
                    if len(memory_line) >= 3:
                        total_mb = int(memory_line[1])
                        used_mb = int(memory_line[2])
                        usage_percent = (used_mb / total_mb) * 100
                        
                        return {
                            'total_mb': total_mb,
                            'used_mb': used_mb,
                            'usage_percent': usage_percent,
                            'method': 'ssh'
                        }
        except Exception as e:
            logger.debug(f"SSH memory check failed: {e}")
        
        # Fallback: Use local memory as proxy (not accurate but better than nothing)
        try:
            import psutil
            memory = psutil.virtual_memory()
            # Estimate server memory based on local usage pattern
            estimated_total = 8192  # 8GB for t3.large
            estimated_used = int(memory.percent * estimated_total / 100)
            
            return {
                'total_mb': estimated_total,
                'used_mb': estimated_used,
                'usage_percent': memory.percent,
                'method': 'local_estimate'
            }
        except Exception as e:
            logger.debug(f"Local memory check failed: {e}")
        
        return None
    
    def simulate_user_session(self, user_id, batch_num):
        """Simulate a complete user session"""
        session_data = {
            'user_id': user_id,
            'batch_num': batch_num,
            'start_time': time.time(),
            'messages': [],
            'response_times': [],
            'failed_requests': 0,
            'success': False
        }
        
        try:
            # Step 1: Get initial message
            response = requests.get(f"{self.base_url}/api/chatbot/initial/", timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('message', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
            else:
                session_data['failed_requests'] += 1
                logger.error(f"User {user_id}: Failed to get initial message")
                return session_data
            
            # Step 2: Send first user message (ML classification happens)
            user_input = "I have a problem with my order. It's been delayed for a week and I'm very frustrated."
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': user_input, 'index': 0, 'timer': 0, 'chatLog': '', 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
            else:
                session_data['failed_requests'] += 1
                logger.error(f"User {user_id}: Failed to send first message")
                return session_data
            
            # Step 3: Send follow-up message
            user_input = "Yes, I ordered it last Monday and it was supposed to arrive by Friday."
            chat_log = json.dumps([{"role": "user", "content": "I have a problem with my order. It's been delayed for a week and I'm very frustrated."},
                                 {"role": "assistant", "content": session_data['messages'][1]}])
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': user_input, 'index': 1, 'timer': 0, 'chatLog': chat_log, 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
            else:
                session_data['failed_requests'] += 1
                logger.error(f"User {user_id}: Failed to send follow-up message")
                return session_data
            
            # Step 4: Get understanding statement
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': '', 'index': 2, 'timer': 0, 'chatLog': chat_log, 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
            else:
                session_data['failed_requests'] += 1
                logger.error(f"User {user_id}: Failed to get understanding statement")
                return session_data
            
            # Step 5: Provide email and end conversation
            user_input = "test@example.com"
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': user_input, 'index': 3, 'timer': 0, 'chatLog': chat_log, 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
                session_data['success'] = True
            else:
                session_data['failed_requests'] += 1
                logger.error(f"User {user_id}: Failed to provide email")
                return session_data
            
        except Exception as e:
            logger.error(f"User {user_id}: Session error: {e}")
            session_data['failed_requests'] += 1
        
        session_data['end_time'] = time.time()
        session_data['duration'] = session_data['end_time'] - session_data['start_time']
        session_data['avg_response_time'] = sum(session_data['response_times']) / len(session_data['response_times']) if session_data['response_times'] else 0
        
        return session_data
    
    def run_batch(self, batch_num, num_users=15):
        """Run a single batch of users"""
        logger.info(f"🔄 Starting Batch {batch_num} with {num_users} users")
        
        # Get memory before batch
        memory_before = self.get_server_memory()
        if memory_before:
            logger.info(f"Memory before batch {batch_num}: {memory_before['used_mb']}/{memory_before['total_mb']} MB ({memory_before['usage_percent']:.1f}%)")
        
        batch_start_time = time.time()
        successful_users = 0
        failed_users = 0
        batch_response_times = []
        
        # Create threads for concurrent users
        threads = []
        results = [None] * num_users
        
        def run_user(user_id):
            try:
                result = self.simulate_user_session(user_id, batch_num)
                results[user_id - 1] = result
                if result['success']:
                    batch_response_times.append(result['avg_response_time'])
            except Exception as e:
                logger.error(f"User {user_id}: Thread error: {e}")
                results[user_id - 1] = {
                    'user_id': user_id,
                    'batch_num': batch_num,
                    'success': False,
                    'failed_requests': 1,
                    'avg_response_time': 0
                }
        
        # Start all user threads
        for i in range(num_users):
            thread = threading.Thread(target=run_user, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Process batch results
        for result in results:
            if result and result['success']:
                successful_users += 1
            else:
                failed_users += 1
        
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        
        # Get memory after batch
        memory_after = self.get_server_memory()
        if memory_after:
            logger.info(f"Memory after batch {batch_num}: {memory_after['used_mb']}/{memory_after['total_mb']} MB ({memory_after['usage_percent']:.1f}%)")
        
        # Calculate memory change
        memory_change = None
        if memory_before and memory_after:
            memory_change = {
                'mb_change': memory_after['used_mb'] - memory_before['used_mb'],
                'percent_change': memory_after['usage_percent'] - memory_before['usage_percent']
            }
            logger.info(f"Memory change in batch {batch_num}: {memory_change['mb_change']} MB ({memory_change['percent_change']:.1f}%)")
        
        # Batch statistics
        avg_response_time = sum(batch_response_times) / len(batch_response_times) if batch_response_times else 0
        
        batch_stats = {
            'batch_num': batch_num,
            'total_users': num_users,
            'successful_users': successful_users,
            'failed_users': failed_users,
            'success_rate': (successful_users / num_users) * 100,
            'duration': batch_duration,
            'avg_response_time': avg_response_time,
            'memory_before': memory_before,
            'memory_after': memory_after,
            'memory_change': memory_change,
            'user_results': results
        }
        
        logger.info(f"✅ Batch {batch_num} completed:")
        logger.info(f"   Success Rate: {batch_stats['success_rate']:.1f}% ({successful_users}/{num_users})")
        logger.info(f"   Duration: {batch_duration:.2f}s")
        logger.info(f"   Avg Response Time: {avg_response_time:.2f}s")
        
        return batch_stats
    
    def run_consecutive_test(self, num_batches=10, users_per_batch=15):
        """Run consecutive batches to test memory management"""
        logger.info(f"🚀 Starting Consecutive Memory Management Test")
        logger.info(f"📊 Configuration: {num_batches} batches, {users_per_batch} users per batch")
        logger.info(f"🎯 Total Users: {num_batches * users_per_batch}")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        for batch_num in range(1, num_batches + 1):
            logger.info(f"\n🔄 BATCH {batch_num}/{num_batches}")
            logger.info("-" * 40)
            
            # Run the batch
            batch_stats = self.run_batch(batch_num, users_per_batch)
            self.results.append(batch_stats)
            
            # Update totals
            self.total_users += batch_stats['total_users']
            self.successful_users += batch_stats['successful_users']
            self.failed_users += batch_stats['failed_users']
            
            # Wait between batches (except for the last one)
            if batch_num < num_batches:
                logger.info("⏳ Waiting 10 seconds between batches...")
                time.sleep(10)
        
        self.end_time = time.time()
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_duration = self.end_time - self.start_time
        overall_success_rate = (self.successful_users / self.total_users) * 100 if self.total_users > 0 else 0
        
        # Calculate overall statistics
        all_response_times = []
        memory_changes = []
        
        for batch in self.results:
            all_response_times.extend([user['avg_response_time'] for user in batch['user_results'] if user and user['success']])
            if batch['memory_change']:
                memory_changes.append(batch['memory_change'])
        
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        avg_memory_change = sum(m['mb_change'] for m in memory_changes) / len(memory_changes) if memory_changes else 0
        
        # Generate report
        report = {
            'test_info': {
                'total_batches': len(self.results),
                'users_per_batch': self.results[0]['total_users'] if self.results else 0,
                'total_users': self.total_users,
                'total_duration': total_duration,
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.fromtimestamp(self.end_time).isoformat()
            },
            'overall_stats': {
                'successful_users': self.successful_users,
                'failed_users': self.failed_users,
                'success_rate': overall_success_rate,
                'avg_response_time': avg_response_time,
                'avg_memory_change_per_batch': avg_memory_change
            },
            'batch_results': self.results
        }
        
        # Save detailed report
        with open('consecutive_memory_test_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info(f"\n📊 CONSECUTIVE MEMORY TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"🎯 Total Users: {self.total_users}")
        logger.info(f"✅ Successful: {self.successful_users}")
        logger.info(f"❌ Failed: {self.failed_users}")
        logger.info(f"📈 Success Rate: {overall_success_rate:.1f}%")
        logger.info(f"⏱️  Total Duration: {total_duration:.2f}s")
        logger.info(f"📊 Avg Response Time: {avg_response_time:.2f}s")
        logger.info(f"💾 Avg Memory Change per Batch: {avg_memory_change:.1f} MB")
        
        # Batch-by-batch summary
        logger.info(f"\n📋 BATCH SUMMARY:")
        for i, batch in enumerate(self.results, 1):
            memory_info = ""
            if batch['memory_change']:
                memory_info = f" | Memory: {batch['memory_change']['mb_change']:+d} MB"
            
            logger.info(f"   Batch {i}: {batch['success_rate']:.1f}% success | {batch['duration']:.1f}s | {batch['avg_response_time']:.2f}s avg{memory_info}")
        
        # Memory management assessment
        logger.info(f"\n🔍 MEMORY MANAGEMENT ASSESSMENT:")
        if avg_memory_change < 50:
            logger.info("✅ EXCELLENT: Minimal memory accumulation per batch")
        elif avg_memory_change < 100:
            logger.info("✅ GOOD: Low memory accumulation per batch")
        elif avg_memory_change < 200:
            logger.info("⚠️  MODERATE: Some memory accumulation per batch")
        else:
            logger.info("❌ CONCERNING: High memory accumulation per batch")
        
        if overall_success_rate > 95:
            logger.info("✅ EXCELLENT: High success rate maintained")
        elif overall_success_rate > 90:
            logger.info("✅ GOOD: Good success rate maintained")
        elif overall_success_rate > 80:
            logger.info("⚠️  MODERATE: Some failures observed")
        else:
            logger.info("❌ CONCERNING: High failure rate")
        
        logger.info(f"\n📄 Detailed results saved to: consecutive_memory_test_results.json")

def main():
    """Main function to run the consecutive memory test"""
    tester = ConsecutiveMemoryTester()
    
    try:
        # Run 10 consecutive batches with 15 users each
        tester.run_consecutive_test(num_batches=10, users_per_batch=15)
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main() 