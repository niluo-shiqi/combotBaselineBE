#!/usr/bin/env python3
"""
Memory Pressure Test
Creates realistic memory pressure to validate memory management improvements
"""

import requests
import json
import time
import logging
import threading
from datetime import datetime
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memory_pressure_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemoryPressureTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.results = []
        
    def create_memory_pressure_session(self, user_id, session_num):
        """Create a session designed to cause memory pressure"""
        session_data = {
            'user_id': user_id,
            'session_num': session_num,
            'start_time': time.time(),
            'messages': [],
            'response_times': [],
            'memory_impact': 0,
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
                logger.error(f"User {user_id}: Failed to get initial message")
                return session_data
            
            # Step 2: Send complex message that triggers ML classification
            # Use a longer, more complex message to create memory pressure
            complex_message = f"""
            I have a very serious problem with my order that has been causing me significant distress. 
            I ordered a high-end laptop computer worth $2,500 on Monday last week, and it was supposed 
            to arrive by Friday. The tracking information shows it was shipped but then got stuck in 
            transit for 5 days. When I called customer service, they were extremely rude and unhelpful. 
            The representative told me there was nothing they could do and that I should just wait. 
            This is completely unacceptable given the amount of money I spent. I need immediate assistance 
            to resolve this issue as I need this computer for my work. The order number is ORD-{user_id:04d}-{session_num:04d} 
            and I'm extremely frustrated with this entire experience. Can you please help me get this 
            resolved immediately?
            """
            
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': complex_message, 'index': 0, 'timer': 0, 'chatLog': '', 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
                # Estimate memory impact based on response time (longer = more memory)
                session_data['memory_impact'] = response.elapsed.total_seconds() * 10  # Rough estimate
            else:
                logger.error(f"User {user_id}: Failed to send complex message")
                return session_data
            
            # Step 3: Send follow-up with more complexity
            follow_up = f"""
            Thank you for your response. However, I need more specific information about what you're 
            going to do to resolve this issue. The laptop I ordered is a Dell XPS 15 with 32GB RAM 
            and 1TB SSD, and I specifically need it for video editing work. The delay is costing me 
            money as I have client projects waiting. I've already contacted your company three times 
            and each time I get a different story. The last representative said the package was lost, 
            but the tracking shows it's just sitting in a warehouse. This is completely unacceptable 
            for a premium order. I demand immediate escalation to a supervisor and a full refund if 
            this isn't resolved within 24 hours. My patience is completely exhausted.
            """
            
            chat_log = json.dumps([{"role": "user", "content": complex_message},
                                 {"role": "assistant", "content": session_data['messages'][1]}])
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': follow_up, 'index': 1, 'timer': 0, 'chatLog': chat_log, 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
                session_data['memory_impact'] += response.elapsed.total_seconds() * 10
            else:
                logger.error(f"User {user_id}: Failed to send follow-up")
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
                logger.error(f"User {user_id}: Failed to get understanding statement")
                return session_data
            
            # Step 5: Provide email and end conversation
            user_input = f"test{user_id:04d}@example.com"
            response = requests.post(f"{self.base_url}/api/chatbot/", 
                                  json={'message': user_input, 'index': 3, 'timer': 0, 'chatLog': chat_log, 'classType': '', 'messageTypeLog': ''}, 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                session_data['messages'].append(data.get('reply', ''))
                session_data['response_times'].append(response.elapsed.total_seconds())
                session_data['success'] = True
            else:
                logger.error(f"User {user_id}: Failed to provide email")
                return session_data
            
        except Exception as e:
            logger.error(f"User {user_id}: Session error: {e}")
        
        session_data['end_time'] = time.time()
        session_data['duration'] = session_data['end_time'] - session_data['start_time']
        session_data['avg_response_time'] = sum(session_data['response_times']) / len(session_data['response_times']) if session_data['response_times'] else 0
        
        return session_data
    
    def run_memory_pressure_test(self, num_sessions=20, concurrent_users=5):
        """Run memory pressure test with increasing load"""
        logger.info(f"🚀 Starting Memory Pressure Test")
        logger.info(f"📊 Configuration: {num_sessions} sessions, {concurrent_users} concurrent users")
        logger.info("=" * 60)
        
        start_time = time.time()
        successful_sessions = 0
        failed_sessions = 0
        total_memory_impact = 0
        response_times = []
        
        # Run sessions in batches to create memory pressure
        for batch_num in range(0, num_sessions, concurrent_users):
            batch_start = batch_num
            batch_end = min(batch_num + concurrent_users, num_sessions)
            batch_size = batch_end - batch_start
            
            logger.info(f"🔄 Running Batch {batch_num//concurrent_users + 1} ({batch_size} sessions)")
            
            # Create threads for concurrent sessions
            threads = []
            results = [None] * batch_size
            
            def run_session(session_id):
                try:
                    result = self.create_memory_pressure_session(session_id + 1, batch_num + session_id + 1)
                    results[session_id] = result
                    if result['success']:
                        response_times.append(result['avg_response_time'])
                except Exception as e:
                    logger.error(f"Session {session_id + 1}: Thread error: {e}")
                    results[session_id] = {
                        'user_id': session_id + 1,
                        'session_num': batch_num + session_id + 1,
                        'success': False,
                        'memory_impact': 0,
                        'avg_response_time': 0
                    }
            
            # Start all session threads
            for i in range(batch_size):
                thread = threading.Thread(target=run_session, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Process batch results
            for result in results:
                if result and result['success']:
                    successful_sessions += 1
                    total_memory_impact += result['memory_impact']
                else:
                    failed_sessions += 1
            
            batch_duration = time.time() - start_time
            logger.info(f"✅ Batch completed: {successful_sessions + failed_sessions}/{num_sessions} sessions")
            logger.info(f"   Success Rate: {((successful_sessions + failed_sessions) / num_sessions) * 100:.1f}%")
            logger.info(f"   Memory Impact: {total_memory_impact:.1f} units")
            
            # Wait between batches to allow memory cleanup
            if batch_end < num_sessions:
                logger.info("⏳ Waiting 5 seconds between batches...")
                time.sleep(5)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate statistics
        success_rate = (successful_sessions / num_sessions) * 100 if num_sessions > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        avg_memory_impact = total_memory_impact / successful_sessions if successful_sessions > 0 else 0
        
        # Generate report
        report = {
            'test_info': {
                'total_sessions': num_sessions,
                'concurrent_users': concurrent_users,
                'total_duration': total_duration,
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat()
            },
            'results': {
                'successful_sessions': successful_sessions,
                'failed_sessions': failed_sessions,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'total_memory_impact': total_memory_impact,
                'avg_memory_impact': avg_memory_impact
            }
        }
        
        # Save detailed report
        with open('memory_pressure_test_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info(f"\n📊 MEMORY PRESSURE TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"🎯 Total Sessions: {num_sessions}")
        logger.info(f"✅ Successful: {successful_sessions}")
        logger.info(f"❌ Failed: {failed_sessions}")
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        logger.info(f"⏱️  Total Duration: {total_duration:.2f}s")
        logger.info(f"📊 Avg Response Time: {avg_response_time:.2f}s")
        logger.info(f"💾 Total Memory Impact: {total_memory_impact:.1f} units")
        logger.info(f"📈 Avg Memory Impact: {avg_memory_impact:.1f} units")
        
        # Memory management assessment
        if success_rate > 95:
            logger.info("✅ EXCELLENT: High success rate maintained under pressure")
        elif success_rate > 90:
            logger.info("✅ GOOD: Good success rate under pressure")
        elif success_rate > 80:
            logger.info("⚠️  MODERATE: Some failures under pressure")
        else:
            logger.info("❌ CONCERNING: High failure rate under pressure")
        
        if avg_response_time < 10:
            logger.info("✅ EXCELLENT: Fast response times maintained")
        elif avg_response_time < 15:
            logger.info("✅ GOOD: Reasonable response times")
        elif avg_response_time < 20:
            logger.info("⚠️  MODERATE: Slower response times")
        else:
            logger.info("❌ CONCERNING: Very slow response times")
        
        logger.info(f"\n📄 Detailed results saved to: memory_pressure_test_results.json")

def main():
    """Main function to run the memory pressure test"""
    tester = MemoryPressureTester()
    
    try:
        # Run memory pressure test with 20 sessions and 5 concurrent users
        tester.run_memory_pressure_test(num_sessions=20, concurrent_users=5)
        
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main() 