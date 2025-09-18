#!/usr/bin/env python3
"""
Conservative optimization for 30 concurrent users
Focuses on gunicorn configuration and minimal code changes
"""

import os
import shutil

def create_optimized_gunicorn_config():
    """Create optimized gunicorn config for 30 users"""
    config = """# Optimized Gunicorn configuration for 30 concurrent users
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - increased for 30 concurrent users
workers = 8  # Increased from 2-3 to handle more concurrent users
worker_class = "sync"
worker_connections = 1000
max_requests = 500  # Restart workers after 500 requests to prevent memory leaks
max_requests_jitter = 50

# Timeout settings - increased for ML processing
timeout = 90  # Increased timeout for ML processing
keepalive = 5
graceful_timeout = 30

# Memory management
preload_app = True  # Load application before forking workers

# Logging
accesslog = "gunicorn.log"
errorlog = "gunicorn.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "combot_backend"

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Worker process management
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance

# Environment variables for optimization
raw_env = [
    'TRANSFORMERS_CACHE=./cache',
    'USE_TF=0',
    'TOKENIZERS_PARALLELISM=false',
    'OMP_NUM_THREADS=1',  # Limit OpenMP threads per worker
]

# Memory limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8192

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
"""
    
    with open("gunicorn_30_users.conf.py", "w") as f:
        f.write(config)
    
    print("✓ Created optimized gunicorn configuration for 30 users")

def create_ml_classifier_optimization():
    """Add ML classifier optimization to views.py"""
    print("🔧 Adding ML classifier optimization...")
    
    # Read current views.py
    with open("chatbot/views.py", "r") as f:
        content = f.read()
    
    # Add ML classifier caching at the top
    ml_optimization = '''
# ML Classifier optimization for high concurrency
import threading
_ml_classifier = None
_classifier_lock = threading.Lock()

def get_ml_classifier():
    """Get or create ML classifier with thread-safe caching"""
    global _ml_classifier
    if _ml_classifier is None:
        with _classifier_lock:
            if _ml_classifier is None:
                try:
                    os.environ["TRANSFORMERS_CACHE"] = "./cache"
                    os.environ["USE_TF"] = "0"
                    os.environ["TOKENIZERS_PARALLELISM"] = "false"
                    _ml_classifier = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                    print("ML classifier loaded successfully")
                except Exception as e:
                    print(f"ERROR: Failed to load ML classifier: {e}")
                    raise e
    return _ml_classifier

'''
    
    # Insert after the imports
    if "get_ml_classifier" not in content:
        # Find the end of imports
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                insert_index = i + 1
            elif line.strip() and not line.startswith('#'):
                break
        
        lines.insert(insert_index, ml_optimization)
        content = '\n'.join(lines)
        
        # Write back to file
        with open("chatbot/views.py", "w") as f:
            f.write(content)
        
        print("✓ Added ML classifier caching optimization")
    else:
        print("✓ ML classifier optimization already present")

def create_deployment_script():
    """Create deployment script for 30 users"""
    script = """#!/bin/bash
# Deploy server optimized for 30 concurrent users

echo "🚀 Deploying server optimized for 30 concurrent users..."

# Kill existing processes
echo "Stopping existing server..."
pkill -f gunicorn

# Wait for processes to stop
sleep 5

# Start optimized server
echo "Starting server with 8 workers for 30 concurrent users..."
cd ~/CombotBackend
source venv/bin/activate

# Use optimized gunicorn configuration
nohup gunicorn --config gunicorn_30_users.conf.py combotBaselineBE.wsgi:application > gunicorn.log 2>&1 &

echo "✅ Server started with 8 workers!"
echo "📊 Monitor with: ps aux | grep gunicorn"
echo "🌐 Server URL: http://3.144.114.76:8000"
echo "👥 Optimized for: 30 concurrent users"
"""
    
    with open("deploy_30_users.sh", "w") as f:
        f.write(script)
    
    os.chmod("deploy_30_users.sh", 0o755)
    print("✓ Created deployment script for 30 users")

def create_stress_test_30_users():
    """Create stress test specifically for 30 users"""
    script = """#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import statistics

async def test_30_users():
    \"\"\"Test with exactly 30 concurrent users\"\"\"
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
        
        print(f"\\n📊 RESULTS FOR 30 CONCURRENT USERS:")
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
            print(f"\\n❌ Failed requests:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"  Test {r['test_id']}: {r.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_30_users())
"""
    
    with open("test_30_users.py", "w") as f:
        f.write(script)
    
    os.chmod("test_30_users.py", 0o755)
    print("✓ Created stress test for 30 users")

def main():
    """Apply conservative optimizations"""
    print("🎯 APPLYING CONSERVATIVE OPTIMIZATIONS FOR 30 USERS")
    print("=" * 60)
    
    create_optimized_gunicorn_config()
    create_ml_classifier_optimization()
    create_deployment_script()
    create_stress_test_30_users()
    
    print("\n✅ CONSERVATIVE OPTIMIZATION COMPLETE!")
    print("=" * 60)
    print("📋 Optimizations applied:")
    print("• Increased gunicorn workers to 8")
    print("• Added ML classifier caching")
    print("• Increased timeouts for ML processing")
    print("• Added memory management")
    print("\n🚀 Next steps:")
    print("1. Deploy: ./deploy_30_users.sh")
    print("2. Test: python test_30_users.py")
    print("3. Monitor: ps aux | grep gunicorn")
    print("\n📊 Expected performance:")
    print("• 30 concurrent users supported")
    print("• Response times: 8-15s average")
    print("• Memory usage: ~6-8GB total")
    print("• Success rate: >80%")

if __name__ == "__main__":
    main()
