#!/usr/bin/env python3
import psutil
import time
import requests
import json

def monitor_server():
    while True:
        try:
            # Check server response
            response = requests.get("http://3.144.114.76:8000/api/random/", timeout=5)
            server_status = "UP" if response.status_code == 200 else "DOWN"
        except:
            server_status = "DOWN"
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get process info
        gunicorn_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if 'gunicorn' in proc.info['name'].lower():
                gunicorn_processes.append(proc.info)
        
        print(f"\rServer: {server_status} | CPU: {cpu_percent:.1f}% | Memory: {memory_percent:.1f}% | Workers: {len(gunicorn_processes)}", end="")
        
        # Alert if resources are high
        if cpu_percent > 80 or memory_percent > 85:
            print(f"\n⚠️ HIGH RESOURCE USAGE: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%")
        
        time.sleep(5)

if __name__ == "__main__":
    print("🔍 Starting server monitoring for 30 concurrent users...")
    print("Press Ctrl+C to stop")
    monitor_server()
