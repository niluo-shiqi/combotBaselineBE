#!/usr/bin/env python3
"""
Load Testing Script for Combot Backend
Simulates 20 concurrent users hitting the API endpoints
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime
import statistics

class LoadTester:
    def __init__(self, base_url, num_users=10, duration_seconds=60):
        self.base_url = base_url
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.results = []
        self.session = None
        
    async def init_session(self):
        """Initialize aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            
    async def make_request(self, user_id, endpoint, payload=None):
        """Make a single API request"""
        start_time = time.time()
        success = False
        error = None
        response_time = 0
        
        try:
            if payload:
                async with self.session.post(f"{self.base_url}{endpoint}", json=payload) as response:
                    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    success = response.status == 200
                    if not success:
                        error = f"HTTP {response.status}"
            else:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    response_time = (time.time() - start_time) * 1000
                    success = response.status == 200
                    if not success:
                        error = f"HTTP {response.status}"
                        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error = str(e)
            
        return {
            'user_id': user_id,
            'endpoint': endpoint,
            'success': success,
            'response_time': response_time,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
    async def simulate_user(self, user_id):
        """Simulate a single user making requests"""
        user_results = []
        
        # User starts with initial message
        result = await self.make_request(user_id, "/api/chatbot/initial/")
        user_results.append(result)
        
        # Simulate some delay between requests
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # User sends a message
        messages = [
            "I bought a phone last week and it stopped working after 2 days",
            "The delivery was supposed to come yesterday but it's still not here",
            "The customer service was really rude to me on the phone",
            "My order was wrong and they won't let me return it",
            "The product quality is terrible, it broke immediately"
        ]
        
        payload = {
            "message": random.choice(messages),
            "chat_log": json.dumps([
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help you today?"}
            ])
        }
        
        result = await self.make_request(user_id, "/api/chatbot/", payload)
        user_results.append(result)
        
        # Simulate more interactions
        for i in range(3):
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            follow_up_messages = [
                "That's not what I expected",
                "Can you help me with something else?",
                "I'm still not satisfied",
                "What are my options?",
                "This is taking too long"
            ]
            
            payload = {
                "message": random.choice(follow_up_messages),
                "chat_log": json.dumps([
                    {"role": "user", "content": "I have a problem"},
                    {"role": "assistant", "content": "I'm here to help. What's the issue?"},
                    {"role": "user", "content": payload["message"]}
                ])
            }
            
            result = await self.make_request(user_id, "/api/chatbot/", payload)
            user_results.append(result)
            
        return user_results
        
    async def run_load_test(self):
        """Run the load test with multiple concurrent users"""
        print(f"🚀 Starting load test with {self.num_users} concurrent users")
        print(f"⏱️  Duration: {self.duration_seconds} seconds")
        print(f"🌐 Target: {self.base_url}")
        print("=" * 60)
        
        await self.init_session()
        
        start_time = time.time()
        
        # Create tasks for all users
        tasks = []
        for user_id in range(self.num_users):
            task = asyncio.create_task(self.simulate_user(user_id))
            tasks.append(task)
            
        # Wait for all users to complete their sessions
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for user_results in all_results:
            if isinstance(user_results, list):
                self.results.extend(user_results)
                
        await self.close_session()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return total_time
        
    def analyze_results(self, total_time):
        """Analyze the load test results"""
        if not self.results:
            print("❌ No results to analyze")
            return
            
        successful_requests = [r for r in self.results if r['success']]
        failed_requests = [r for r in self.results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_requests]
        
        print("\n📊 LOAD TEST RESULTS")
        print("=" * 60)
        print(f"⏱️  Total Test Time: {total_time:.1f} seconds")
        print(f"📈 Total Requests: {len(self.results)}")
        print(f"✅ Successful Requests: {len(successful_requests)}")
        print(f"❌ Failed Requests: {len(failed_requests)}")
        print(f"📊 Success Rate: {len(successful_requests)/len(self.results)*100:.1f}%")
        
        if response_times:
            print(f"\n⏱️  RESPONSE TIME ANALYSIS:")
            print(f"   Average: {statistics.mean(response_times):.1f}ms")
            print(f"   Median: {statistics.median(response_times):.1f}ms")
            print(f"   Min: {min(response_times):.1f}ms")
            print(f"   Max: {max(response_times):.1f}ms")
            print(f"   Requests per second: {len(successful_requests)/total_time:.1f}")
            
        if failed_requests:
            print(f"\n❌ FAILED REQUESTS:")
            error_counts = {}
            for req in failed_requests:
                error = req.get('error', 'Unknown')
                error_counts[error] = error_counts.get(error, 0) + 1
                
            for error, count in error_counts.items():
                print(f"   {error}: {count} times")
                
        # Performance assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT:")
        if len(successful_requests)/len(self.results) > 0.95:
            print("   ✅ Excellent - High success rate")
        elif len(successful_requests)/len(self.results) > 0.90:
            print("   ⚠️  Good - Some failures")
        else:
            print("   🔴 Poor - Many failures")
            
        if response_times and statistics.mean(response_times) < 1000:
            print("   ✅ Fast response times")
        elif response_times and statistics.mean(response_times) < 3000:
            print("   ⚠️  Moderate response times")
        else:
            print("   🔴 Slow response times")
            
        print(f"\n💡 RECOMMENDATIONS:")
        if len(successful_requests)/len(self.results) < 0.95:
            print("   - Investigate failed requests")
            print("   - Check server logs for errors")
        if response_times and statistics.mean(response_times) > 2000:
            print("   - Consider performance optimizations")
            print("   - Monitor server resources during load")
        else:
            print("   - System handles load well")
            print("   - Ready for production use")

async def main():
    """Main function to run the load test"""
    # Configuration
    BASE_URL = "http://18.222.168.169:8000"  # Your EC2 instance
    NUM_USERS = 10  # Testing with 10 users
    DURATION = 30  # Reduced from 60 to 30 seconds
    
    print("🧪 COMBOT BACKEND LOAD TESTER")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Users: {NUM_USERS}")
    print(f"Duration: {DURATION} seconds")
    print("=" * 60)
    
    # Create and run load tester
    load_tester = LoadTester(BASE_URL, NUM_USERS, DURATION)
    
    try:
        total_time = await load_tester.run_load_test()
        load_tester.analyze_results(total_time)
        
    except KeyboardInterrupt:
        print("\n🛑 Load test interrupted by user")
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 