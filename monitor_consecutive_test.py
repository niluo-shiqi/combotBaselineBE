#!/usr/bin/env python3
"""
Real-time Monitor for Consecutive Memory Test
Monitors the progress and provides live updates
"""

import time
import json
import os
import requests
import psutil
from datetime import datetime
import subprocess

def get_server_memory():
    """Get current server memory usage"""
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
                        'usage_percent': usage_percent
                    }
    except Exception as e:
        return None

def check_server_status():
    """Check if server is responding"""
    try:
        response = requests.get("http://3.144.114.76:8000/api/chatbot/initial/", timeout=5)
        return response.status_code == 200
    except:
        return False

def monitor_test_progress():
    """Monitor the consecutive test progress"""
    print("🔍 CONSECUTIVE MEMORY TEST MONITOR")
    print("=" * 50)
    print("⏰ Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # Track memory over time
    memory_history = []
    start_time = time.time()
    
    while True:
        try:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Get server memory
            memory = get_server_memory()
            if memory:
                memory_history.append({
                    'time': elapsed,
                    'memory_mb': memory['used_mb'],
                    'memory_percent': memory['usage_percent']
                })
                
                # Keep only last 20 readings
                if len(memory_history) > 20:
                    memory_history.pop(0)
            
            # Check server status
            server_responding = check_server_status()
            
            # Clear screen and show status
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🔍 CONSECUTIVE MEMORY TEST MONITOR")
            print("=" * 50)
            print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Elapsed: {elapsed:.0f}s")
            print()
            
            # Server status
            status_icon = "✅" if server_responding else "❌"
            print(f"{status_icon} Server Status: {'Online' if server_responding else 'Offline'}")
            
            # Memory status
            if memory:
                print(f"💾 Memory: {memory['used_mb']}/{memory['total_mb']} MB ({memory['usage_percent']:.1f}%)")
                
                # Memory trend
                if len(memory_history) >= 2:
                    recent_avg = sum(m['memory_mb'] for m in memory_history[-5:]) / 5
                    older_avg = sum(m['memory_mb'] for m in memory_history[-10:-5]) / 5
                    
                    if recent_avg > older_avg + 50:
                        trend = "📈 Increasing"
                    elif recent_avg < older_avg - 50:
                        trend = "📉 Decreasing"
                    else:
                        trend = "➡️  Stable"
                    
                    print(f"📊 Trend: {trend}")
                
                # Memory assessment
                if memory['usage_percent'] < 60:
                    assessment = "🟢 Excellent"
                elif memory['usage_percent'] < 75:
                    assessment = "🟡 Good"
                elif memory['usage_percent'] < 85:
                    assessment = "🟠 Moderate"
                else:
                    assessment = "🔴 Critical"
                
                print(f"📈 Assessment: {assessment}")
            
            print()
            print("📋 Memory History (last 20 readings):")
            if memory_history:
                for i, reading in enumerate(memory_history[-10:], 1):
                    time_str = f"{reading['time']:.0f}s"
                    memory_str = f"{reading['memory_mb']} MB ({reading['memory_percent']:.1f}%)"
                    print(f"   {i:2d}. {time_str:>6s} | {memory_str}")
            
            print()
            print("💡 Press Ctrl+C to stop monitoring")
            
            # Wait 10 seconds before next check
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in monitoring: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_test_progress() 