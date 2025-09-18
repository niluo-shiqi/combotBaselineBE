#!/usr/bin/env python3
"""
Combot Stress Testing Script
Tests server capacity and response times under various loads
"""

import asyncio
import aiohttp
import time
import json
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
import argparse

class StressTester:
    def __init__(self, base_url="http://3.144.114.76:8000"):
        self.base_url = base_url
        self.results = []
        
    async def single_request(self, session, test_id, scenario_type="Basic"):
        """Make a single API request and measure response time"""
        start_time = time.time()
        
        # Test data for different scenarios
        test_scenarios = {
            "Basic": {
                "message": "I need to return some shoes",
                "index": 0,
                "timer": 0,
                "chatLog": "[]",
                "classType": "",
                "messageTypeLog": "[]",
                "scenario": {"brand": "Basic", "problem_type": "Other", "think_level": "High", "feel_level": "High"}
            },
            "Lulu": {
                "message": "When is my package getting here? Its late",
                "index": 0,
                "timer": 0,
                "chatLog": "[]",
                "classType": "",
                "messageTypeLog": "[]",
                "scenario": {"brand": "Lulu", "problem_type": "Other", "think_level": "High", "feel_level": "High"}
            },
            "Return": {
                "message": "I need to return some shoes",
                "index": 0,
                "timer": 0,
                "chatLog": "[]",
                "classType": "",
                "messageTypeLog": "[]",
                "scenario": {"brand": "Lulu", "problem_type": "Other", "think_level": "High", "feel_level": "High"}
            }
        }
        
        data = test_scenarios[scenario_type]
        
        try:
            async with session.post(
                f"{self.base_url}/api/random/",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()
                end_time = time.time()
                
                result = {
                    "test_id": test_id,
                    "scenario": scenario_type,
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "timestamp": start_time,
                    "response_size": len(response_text)
                }
                
                if response.status == 200:
                    try:
                        response_data = json.loads(response_text)
                        result["has_weights"] = "product_type_breakdown" in response_data.get("scenario", {})
                        result["class_type"] = response_data.get("classType", "")
                    except:
                        result["has_weights"] = False
                        result["class_type"] = ""
                
                return result
                
        except asyncio.TimeoutError:
            end_time = time.time()
            return {
                "test_id": test_id,
                "scenario": scenario_type,
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": "timeout",
                "timestamp": start_time
            }
        except Exception as e:
            end_time = time.time()
            return {
                "test_id": test_id,
                "scenario": scenario_type,
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "timestamp": start_time
            }

    async def run_concurrent_test(self, concurrent_users, duration_seconds, scenario_type="Basic"):
        """Run stress test with specified number of concurrent users"""
        print(f"Starting stress test: {concurrent_users} concurrent users for {duration_seconds}s ({scenario_type})")
        
        connector = aiohttp.TCPConnector(limit=concurrent_users * 2, limit_per_host=concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            start_time = time.time()
            tasks = []
            request_count = 0
            
            # Create initial batch of requests
            for i in range(concurrent_users):
                task = asyncio.create_task(self.single_request(session, f"{i}_{request_count}", scenario_type))
                tasks.append(task)
                request_count += 1
            
            # Keep adding new requests as old ones complete
            while time.time() - start_time < duration_seconds:
                # Wait for at least one task to complete
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                # Process completed tasks
                for task in done:
                    result = await task
                    self.results.append(result)
                    
                    # Create new task to maintain concurrency
                    if time.time() - start_time < duration_seconds:
                        new_task = asyncio.create_task(
                            self.single_request(session, f"{len(tasks) % concurrent_users}_{request_count}", scenario_type)
                        )
                        tasks.append(new_task)
                        request_count += 1
                
                # Remove completed tasks from pending list
                tasks = [task for task in tasks if not task.done()]
            
            # Wait for remaining tasks to complete
            if tasks:
                remaining_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in remaining_results:
                    if isinstance(result, dict):
                        self.results.append(result)
        
        return self.analyze_results(concurrent_users, duration_seconds)

    def analyze_results(self, concurrent_users, duration_seconds):
        """Analyze test results and return performance metrics"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Filter results from this test run
        test_results = [r for r in self.results if r.get("test_id", "").startswith(f"{concurrent_users}_") or 
                       (isinstance(r.get("test_id"), str) and r["test_id"].split("_")[0].isdigit() and 
                        int(r["test_id"].split("_")[0]) < concurrent_users)]
        
        if not test_results:
            test_results = self.results[-concurrent_users*10:]  # Fallback to recent results
        
        total_requests = len(test_results)
        successful_requests = len([r for r in test_results if r.get("success", False)])
        failed_requests = total_requests - successful_requests
        
        if successful_requests == 0:
            return {
                "concurrent_users": concurrent_users,
                "duration": duration_seconds,
                "total_requests": total_requests,
                "successful_requests": 0,
                "failed_requests": failed_requests,
                "success_rate": 0.0,
                "error": "No successful requests"
            }
        
        response_times = [r["response_time"] for r in test_results if r.get("success", False)]
        
        analysis = {
            "concurrent_users": concurrent_users,
            "duration": duration_seconds,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests * 100,
            "requests_per_second": total_requests / duration_seconds,
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
            "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "has_weights_rate": len([r for r in test_results if r.get("has_weights", False)]) / successful_requests * 100 if successful_requests > 0 else 0
        }
        
        return analysis

    def print_results(self, results):
        """Print formatted test results"""
        print("\n" + "="*60)
        print(f"STRESS TEST RESULTS - {results['concurrent_users']} Concurrent Users")
        print("="*60)
        print(f"Duration: {results['duration']}s")
        print(f"Total Requests: {results['total_requests']}")
        print(f"Successful: {results['successful_requests']}")
        print(f"Failed: {results['failed_requests']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Requests/sec: {results['requests_per_second']:.2f}")
        print(f"Avg Response Time: {results['avg_response_time']:.3f}s")
        print(f"Median Response Time: {results['median_response_time']:.3f}s")
        print(f"95th Percentile: {results['p95_response_time']:.3f}s")
        print(f"99th Percentile: {results['p99_response_time']:.3f}s")
        print(f"Min Response Time: {results['min_response_time']:.3f}s")
        print(f"Max Response Time: {results['max_response_time']:.3f}s")
        print(f"Weights Present: {results['has_weights_rate']:.1f}%")
        print("="*60)

async def main():
    parser = argparse.ArgumentParser(description="Combot Stress Testing")
    parser.add_argument("--users", type=int, default=1, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--scenario", choices=["Basic", "Lulu", "Return"], default="Basic", help="Test scenario")
    parser.add_argument("--url", default="http://3.144.114.76:8000", help="Server URL")
    parser.add_argument("--max-users", type=int, default=50, help="Maximum users for capacity test")
    parser.add_argument("--capacity-test", action="store_true", help="Run capacity test to find optimal users")
    
    args = parser.parse_args()
    
    tester = StressTester(args.url)
    
    if args.capacity_test:
        print("Running capacity test to find optimal concurrent users...")
        print("This will test from 1 to {} users in increments of 5".format(args.max_users))
        
        optimal_users = 1
        best_throughput = 0
        
        for users in range(1, args.max_users + 1, 5):
            print(f"\nTesting {users} concurrent users...")
            results = await tester.run_concurrent_test(users, 30, args.scenario)
            
            if "error" not in results:
                tester.print_results(results)
                
                # Consider optimal if success rate > 95% and avg response time < 5s
                if (results["success_rate"] > 95 and 
                    results["avg_response_time"] < 5.0 and 
                    results["requests_per_second"] > best_throughput):
                    optimal_users = users
                    best_throughput = results["requests_per_second"]
            else:
                print(f"Test failed: {results['error']}")
                break
            
            # Wait between tests to let server recover
            await asyncio.sleep(10)
        
        print(f"\n🎯 OPTIMAL CAPACITY: {optimal_users} concurrent users")
        print(f"Best throughput: {best_throughput:.2f} requests/second")
        
    else:
        # Single test
        results = await tester.run_concurrent_test(args.users, args.duration, args.scenario)
        tester.print_results(results)

if __name__ == "__main__":
    asyncio.run(main())
