#!/usr/bin/env python3
"""
Comprehensive Test Suite for Combot Backend
Covers all bugs, edge cases, and functionality
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime

class ComprehensiveTester:
    def __init__(self, base_url="http://18.222.168.169:8000"):
        self.base_url = base_url
        self.results = []
        
    async def test_single_request(self, test_name, endpoint, method="GET", payload=None, expected_status=200):
        """Test a single API request"""
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                start_time = time.time()
                
                if method == "GET":
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        response_time = (time.time() - start_time) * 1000
                        success = response.status == expected_status
                        response_text = await response.text()
                        
                elif method == "POST":
                    async with session.post(f"{self.base_url}{endpoint}", json=payload) as response:
                        response_time = (time.time() - start_time) * 1000
                        success = response.status == expected_status
                        response_text = await response.text()
                
                result = {
                    'test_name': test_name,
                    'endpoint': endpoint,
                    'method': method,
                    'success': success,
                    'response_time': response_time,
                    'status': response.status,
                    'response_text': response_text[:200] if response_text else None
                }
                
                status_icon = "✅" if success else "❌"
                print(f"{status_icon} {test_name} - {response.status} ({response_time:.1f}ms)")
                
                return result
                
            except Exception as e:
                result = {
                    'test_name': test_name,
                    'endpoint': endpoint,
                    'method': method,
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                }
                print(f"❌ {test_name} - Error: {str(e)}")
                return result

    async def run_basic_functionality_tests(self):
        """Test basic functionality"""
        print("\n🧪 BASIC FUNCTIONALITY TESTS")
        print("=" * 50)
        
        tests = [
            ("Initial Message - Basic", "/api/random/initial/", "GET"),
            ("Initial Message - Lulu", "/api/lulu/initial/", "GET"),
            ("Reset Session", "/api/random/reset/", "GET"),
        ]
        
        results = []
        for test_name, endpoint, method in tests:
            result = await self.test_single_request(test_name, endpoint, method)
            results.append(result)
        
        return results

    async def run_chat_interaction_tests(self):
        """Test chat interactions with different scenarios"""
        print("\n🧪 CHAT INTERACTION TESTS")
        print("=" * 50)
        
        # Test different problem types
        problem_types = [
            ("Product Quality Issue", "My yoga pants are falling apart after one wash"),
            ("Delivery Issue", "My order was supposed to arrive yesterday but it's still not here"),
            ("Customer Service Issue", "The employee was very rude to me on the phone"),
            ("Return Request", "I want to return my item"),
            ("Refund Request", "I need a refund for my purchase"),
        ]
        
        results = []
        for problem_name, message in problem_types:
            payload = {
                "message": message,
                "index": 0
            }
            test_name = f"Chat - {problem_name}"
            result = await self.test_single_request(test_name, "/api/random/", "POST", payload)
            results.append(result)
            
            # Test continuation
            payload = {
                "message": "More details about the issue",
                "index": 1,
                "chatLog": json.dumps([
                    {"sender": "user", "text": message},
                    {"sender": "combot", "text": "I understand your concern"}
                ])
            }
            test_name = f"Chat Continuation - {problem_name}"
            result = await self.test_single_request(test_name, "/api/random/", "POST", payload)
            results.append(result)
        
        return results

    async def run_edge_case_tests(self):
        """Test edge cases and error conditions"""
        print("\n🧪 EDGE CASE TESTS")
        print("=" * 50)
        
        edge_cases = [
            ("Empty Message", {"message": "", "index": 0}),
            ("Very Long Message", {"message": "A" * 1000, "index": 0}),
            ("Special Characters", {"message": "!@#$%^&*()_+-=[]{}|;':\",./<>?", "index": 0}),
            ("Unicode Characters", {"message": "测试中文消息 🚀", "index": 0}),
            ("Missing Message", {"index": 0}),
            ("Missing Index", {"message": "test message"}),
            ("Invalid Index", {"message": "test", "index": -1}),
            ("High Index", {"message": "test", "index": 999}),
            ("Invalid JSON", "invalid json string"),
        ]
        
        results = []
        for case_name, payload in edge_cases:
            if isinstance(payload, dict):
                result = await self.test_single_request(f"Edge Case - {case_name}", "/api/random/", "POST", payload)
            else:
                # Test with invalid JSON
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(f"{self.base_url}/api/random/", data=payload) as response:
                            success = response.status in [400, 422]  # Expect bad request
                            print(f"{'✅' if success else '❌'} Edge Case - {case_name} - {response.status}")
                            result = {
                                'test_name': f"Edge Case - {case_name}",
                                'success': success,
                                'status': response.status,
                                'response_time': 0
                            }
                    except Exception as e:
                        print(f"❌ Edge Case - {case_name} - Error: {str(e)}")
                        result = {
                            'test_name': f"Edge Case - {case_name}",
                            'success': False,
                            'error': str(e),
                            'response_time': 0
                        }
            results.append(result)
        
        return results

    async def run_conversation_flow_tests(self):
        """Test complete conversation flows"""
        print("\n🧪 CONVERSATION FLOW TESTS")
        print("=" * 50)
        
        flows = [
            ("Short Flow (3 messages)", [
                {"message": "My product is defective", "index": 0},
                {"message": "It broke after one day", "index": 1},
                {"message": "I want a refund", "index": 2},
            ]),
            ("Long Flow (5 messages)", [
                {"message": "Delivery is late", "index": 0},
                {"message": "It was supposed to arrive yesterday", "index": 1},
                {"message": "I need it urgently", "index": 2},
                {"message": "Can you expedite it?", "index": 3},
                {"message": "test@email.com", "index": 4},
            ]),
        ]
        
        results = []
        for flow_name, messages in flows:
            print(f"\n📝 Testing: {flow_name}")
            flow_results = []
            
            for i, payload in enumerate(messages):
                # Add chat log for continuation messages
                if i > 0:
                    chat_log = []
                    for j in range(i):
                        chat_log.append({"sender": "user", "text": messages[j]["message"]})
                        chat_log.append({"sender": "combot", "text": f"Response {j+1}"})
                    payload["chatLog"] = json.dumps(chat_log)
                
                test_name = f"{flow_name} - Message {i+1}"
                result = await self.test_single_request(test_name, "/api/random/", "POST", payload)
                flow_results.append(result)
                
                # Small delay between messages
                await asyncio.sleep(0.5)
            
            results.extend(flow_results)
        
        return results

    async def run_load_tests(self):
        """Test system under load"""
        print("\n🧪 LOAD TESTS")
        print("=" * 50)
        
        load_scenarios = [
            ("Light Load - 3 users", 3),
            ("Medium Load - 5 users", 5),
            ("Heavy Load - 8 users", 8),
        ]
        
        results = []
        for scenario_name, num_users in load_scenarios:
            print(f"\n📊 Testing: {scenario_name}")
            
            # Create concurrent tasks
            tasks = []
            for i in range(num_users):
                payload = {
                    "message": f"Test message from user {i+1}",
                    "index": 0
                }
                task = self.test_single_request(f"{scenario_name} - User {i+1}", "/api/random/", "POST", payload)
                tasks.append(task)
            
            # Run concurrently
            start_time = time.time()
            scenario_results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Process results
            successful = [r for r in scenario_results if isinstance(r, dict) and r.get('success')]
            failed = [r for r in scenario_results if isinstance(r, dict) and not r.get('success')]
            
            print(f"   ✅ Successful: {len(successful)}/{num_users}")
            print(f"   ❌ Failed: {len(failed)}/{num_users}")
            print(f"   ⏱️  Time: {total_time:.1f}s")
            
            results.extend([r for r in scenario_results if isinstance(r, dict)])
        
        return results

    async def run_error_handling_tests(self):
        """Test error handling and recovery"""
        print("\n🧪 ERROR HANDLING TESTS")
        print("=" * 50)
        
        error_tests = [
            ("Invalid Endpoint", "/api/nonexistent/", "GET"),
            ("Invalid Method", "/api/random/", "PUT"),
            ("Malformed JSON", "/api/random/", "POST", "invalid json"),
            ("Large Payload", "/api/random/", "POST", {"message": "A" * 10000, "index": 0}),
        ]
        
        results = []
        for test_name, endpoint, method, *args in error_tests:
            payload = args[0] if args else None
            try:
                result = await self.test_single_request(test_name, endpoint, method, payload, expected_status=400)
                results.append(result)
            except Exception as e:
                result = {
                    'test_name': test_name,
                    'endpoint': endpoint,
                    'method': method,
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                }
                print(f"❌ {test_name} - Error: {str(e)}")
                results.append(result)
        
        return results

    async def run_all_tests(self):
        """Run all test suites"""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        all_results = []
        
        # Run all test suites
        test_suites = [
            ("Basic Functionality", self.run_basic_functionality_tests()),
            ("Chat Interactions", self.run_chat_interaction_tests()),
            ("Edge Cases", self.run_edge_case_tests()),
            ("Conversation Flows", self.run_conversation_flow_tests()),
            ("Load Tests", self.run_load_tests()),
            ("Error Handling", self.run_error_handling_tests()),
        ]
        
        for suite_name, suite_coro in test_suites:
            try:
                suite_results = await suite_coro
                all_results.extend(suite_results)
            except Exception as e:
                print(f"❌ {suite_name} suite failed: {e}")
        
        # Analyze results
        self.analyze_results(all_results)

    def analyze_results(self, results):
        """Analyze and display test results"""
        print("\n📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(results)
        successful_tests = [r for r in results if r.get('success', False)]
        failed_tests = [r for r in results if not r.get('success', False)]
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Successful: {len(successful_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📊 Success Rate: {(len(successful_tests)/total_tests*100):.1f}%")
        
        if successful_tests:
            response_times = [r.get('response_time', 0) for r in successful_tests if r.get('response_time')]
            if response_times:
                print(f"\n⏱️  RESPONSE TIMES (Successful Tests):")
                print(f"   Average: {sum(response_times)/len(response_times):.1f}ms")
                print(f"   Min: {min(response_times):.1f}ms")
                print(f"   Max: {max(response_times):.1f}ms")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   {test.get('test_name', 'Unknown')}: {test.get('error', 'Unknown error')}")
        
        print(f"\n🎯 OVERALL ASSESSMENT:")
        success_rate = len(successful_tests)/total_tests*100
        if success_rate >= 95:
            print("   ✅ EXCELLENT - System is very robust")
        elif success_rate >= 85:
            print("   ✅ GOOD - System handles most cases well")
        elif success_rate >= 70:
            print("   ⚠️  FAIR - Some issues need attention")
        else:
            print("   🔴 POOR - Significant issues found")

async def main():
    """Main function to run comprehensive tests"""
    tester = ComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 