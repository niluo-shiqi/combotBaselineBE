#!/usr/bin/env python3
"""
Smart Auto Restart Monitor for Combot Backend
Only restarts when safe and necessary - avoids interrupting active users
"""

import psutil
import time
import subprocess
import os
import signal
import sys
from datetime import datetime, timedelta
import json
import requests

class SmartAutoRestartMonitor:
    def __init__(self, memory_threshold=80, process_memory_threshold=500):
        self.memory_threshold = memory_threshold  # System memory % threshold
        self.process_memory_threshold = process_memory_threshold  # MB per process
        self.restart_count = 0
        self.last_restart_time = None
        self.last_activity_time = None
        self.monitoring = True
        self.base_url = "http://localhost:8000"  # Your server URL
        
    def get_memory_usage(self):
        """Get current system memory usage"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total / (1024**3),  # GB
            'available': memory.available / (1024**3),  # GB
            'used': memory.used / (1024**3),  # GB
            'percent': memory.percent
        }
    
    def get_gunicorn_processes(self):
        """Get gunicorn process information"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'create_time']):
            try:
                if 'gunicorn' in proc.info['name'].lower():
                    memory_mb = proc.info['memory_info'].rss / (1024**2)
                    processes.append({
                        'pid': proc.info['pid'],
                        'memory_mb': memory_mb,
                        'create_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    
    def check_server_activity(self):
        """Check if server is currently handling requests"""
        try:
            # Try to make a simple request to check if server is active
            response = requests.get(f"{self.base_url}/api/chatbot/initial/", timeout=5)
            if response.status_code == 200:
                self.last_activity_time = datetime.now()
                return True
        except:
            pass
        return False
    
    def is_safe_to_restart(self):
        """Determine if it's safe to restart (no active users)"""
        # Check if there's been recent activity
        if self.last_activity_time:
            time_since_activity = datetime.now() - self.last_activity_time
            # Only restart if no activity for at least 5 minutes
            if time_since_activity < timedelta(minutes=5):
                return False
        
        # Check if server is currently responding to requests
        if self.check_server_activity():
            return False
        
        # Check if it's been too soon since last restart
        if self.last_restart_time:
            time_since_restart = datetime.now() - self.last_restart_time
            # Don't restart more than once every 10 minutes
            if time_since_restart < timedelta(minutes=10):
                return False
        
        return True
    
    def should_restart(self, memory_usage, processes):
        """Determine if server should be restarted (with safety checks)"""
        # Check if it's safe to restart
        if not self.is_safe_to_restart():
            return False
        
        # Check system memory (only if very high)
        if memory_usage['percent'] > self.memory_threshold:
            print(f"⚠️  System memory usage: {memory_usage['percent']:.1f}% > {self.memory_threshold}%")
            return True
        
        # Check individual process memory (only if very high)
        if processes:
            for proc in processes:
                if proc['memory_mb'] > self.process_memory_threshold:
                    print(f"⚠️  Process {proc['pid']} memory: {proc['memory_mb']:.1f}MB > {self.process_memory_threshold}MB")
                    return True
        
        return False
    
    def restart_server(self):
        """Restart the server safely"""
        print(f"\n🔄 SMART RESTART (Attempt #{self.restart_count + 1})")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ Safe to restart - no active users detected")
        
        # Kill existing processes
        try:
            subprocess.run(['pkill', '-f', 'gunicorn'], timeout=10)
            time.sleep(3)
        except subprocess.TimeoutExpired:
            print("⚠️  Force killing processes...")
            subprocess.run(['pkill', '-9', '-f', 'gunicorn'])
            time.sleep(2)
        
        # Clear cache
        try:
            subprocess.run([
                'python', 'manage.py', 'shell', '-c',
                'from django.core.cache import cache; cache.clear()'
            ], timeout=10)
        except:
            print("⚠️  Could not clear Django cache")
        
        # Start server
        try:
            subprocess.Popen([
                'nohup', 'gunicorn', 'combotBaselineBE.wsgi:application',
                '--config', 'gunicorn.conf.py'
            ], stdout=open('server.log', 'a'), stderr=subprocess.STDOUT)
            
            # Wait for server to start
            time.sleep(10)
            
            # Check if server started successfully
            processes = self.get_gunicorn_processes()
            if processes:
                print(f"✅ Server restarted successfully with {len(processes)} workers")
                self.restart_count += 1
                self.last_restart_time = datetime.now()
                return True
            else:
                print("❌ Server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error restarting server: {e}")
            return False
    
    def log_status(self, memory_usage, processes):
        """Log current status"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if safe to restart
        safe_to_restart = self.is_safe_to_restart()
        
        status = {
            'timestamp': timestamp,
            'memory_percent': memory_usage['percent'],
            'memory_used_gb': memory_usage['used'],
            'memory_available_gb': memory_usage['available'],
            'gunicorn_processes': len(processes),
            'total_process_memory_mb': sum(p['memory_mb'] for p in processes) if processes else 0,
            'restart_count': self.restart_count,
            'last_restart': self.last_restart_time.isoformat() if self.last_restart_time else None,
            'safe_to_restart': safe_to_restart,
            'last_activity': self.last_activity_time.isoformat() if self.last_activity_time else None
        }
        
        # Save to JSON log
        with open('smart_monitor_log.json', 'a') as f:
            f.write(json.dumps(status) + '\n')
        
        # Print status
        print(f"\n⏰ {timestamp}")
        print(f"💾 Memory: {memory_usage['used']:.1f}GB / {memory_usage['total']:.1f}GB ({memory_usage['percent']:.1f}%)")
        print(f"🔄 Gunicorn Processes: {len(processes)}")
        if processes:
            total_memory = sum(p['memory_mb'] for p in processes)
            print(f"📈 Total Process Memory: {total_memory:.1f}MB")
        print(f"🔄 Restart Count: {self.restart_count}")
        print(f"🛡️  Safe to Restart: {'✅ Yes' if safe_to_restart else '❌ No (active users)'}")
    
    def run(self, check_interval=60):
        """Main monitoring loop"""
        print("🚀 SMART AUTO RESTART MONITOR STARTED")
        print(f"📊 Memory Threshold: {self.memory_threshold}%")
        print(f"📊 Process Memory Threshold: {self.process_memory_threshold}MB")
        print(f"⏱️  Check Interval: {check_interval} seconds")
        print(f"🛡️  Safety: Won't restart during active user sessions")
        print("=" * 60)
        
        while self.monitoring:
            try:
                # Get current status
                memory_usage = self.get_memory_usage()
                processes = self.get_gunicorn_processes()
                
                # Log status
                self.log_status(memory_usage, processes)
                
                # Check if restart is needed AND safe
                if self.should_restart(memory_usage, processes):
                    if self.restart_server():
                        print("✅ Smart restart completed successfully")
                    else:
                        print("❌ Smart restart failed - manual intervention may be needed")
                else:
                    # Check if restart was needed but not safe
                    if memory_usage['percent'] > self.memory_threshold or (processes and any(p['memory_mb'] > self.process_memory_threshold for p in processes)):
                        print("⚠️  Restart needed but not safe - waiting for user activity to stop")
                
                # Wait for next check
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Smart monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in smart monitoring loop: {e}")
                time.sleep(check_interval)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart auto restart monitor for Combot Backend')
    parser.add_argument('--memory-threshold', type=int, default=80, 
                       help='System memory threshold percentage (default: 80)')
    parser.add_argument('--process-memory-threshold', type=int, default=500,
                       help='Process memory threshold in MB (default: 500)')
    parser.add_argument('--check-interval', type=int, default=60,
                       help='Check interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    monitor = SmartAutoRestartMonitor(
        memory_threshold=args.memory_threshold,
        process_memory_threshold=args.process_memory_threshold
    )
    
    monitor.run(check_interval=args.check_interval)

if __name__ == "__main__":
    main() 