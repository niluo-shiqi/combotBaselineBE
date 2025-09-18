#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import statistics

async def test_30_users():
    """Test with exactly 30 concurrent users"""
    print("🧪 Testing with 30 concurrent users...")
    
    async def single_request(session, test_id):
        start_time = time.time()
        try:
            async with session.post(
                "http://3.144.114.76:8000/api/random/",
                json={
                    "message": "I need to return some shoes",
                    "index": 0,
                    "timer": 0,
                    "chatLog": "[]",
                    "classType": "",
                    "messageTypeLog": "[]",
                    "scenario": {"brand": "Basic", "problem_type": "Other", "think_level": "High", "feel_level": "High"}
                },
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response_text = await response.text()
                end_time = time.time()
                return {
                    "test_id": test_id,
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200
                }
        except Exception as e:
            end_time = time.time()
            return {
                "test_id": test_id,
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e)
            }
    
    # Test with 30 concurrent users
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print("Starting 30 concurrent requests...")
        start_time = time.time()
        
        tasks = []
        for i in range(30):
            task = asyncio.create_task(single_request(session, i))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyze results
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        if successful:
            response_times = [r["response_time"] for r in successful]
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
        else:
            avg_time = max_time = min_time = 0
        
        print(f"\n📊 RESULTS FOR 30 CONCURRENT USERS:")
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
        print(f"Total time: {end_time - start_time:.2f}s")
        print(f"Average response time: {avg_time:.2f}s")
        print(f"Min response time: {min_time:.2f}s")
        print(f"Max response time: {max_time:.2f}s")
        
        if len(successful) >= 25:  # 83% success rate
            print("✅ SUCCESS: Server can handle 30 concurrent users!")
        else:
            print("❌ FAILED: Server cannot handle 30 concurrent users reliably")
        
        # Show failed requests
        if failed:
            print(f"\n❌ Failed requests:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"  Test {r['test_id']}: {r.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_30_users())
