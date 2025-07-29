#!/usr/bin/env python3
"""
Performance monitoring script for Combot Backend
Run this to monitor server performance and identify bottlenecks
"""

import psutil
import time
import subprocess
import json
from datetime import datetime

def get_system_stats():
    """Get current system statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_available_gb': memory.available / (1024**3),
        'memory_used_gb': memory.used / (1024**3),
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024**3)
    }

def get_process_stats():
    """Get Django/Gunicorn process statistics"""
    try:
        # Find Django/Gunicorn processes
        django_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if 'python' in proc.info['name'].lower() and proc.info['cpu_percent'] > 0:
                django_processes.append(proc.info)
        
        return django_processes
    except Exception as e:
        return f"Error getting process stats: {e}"

def get_network_connections():
    """Get active network connections"""
    try:
        connections = psutil.net_connections()
        port_8000_connections = [conn for conn in connections if conn.laddr.port == 8000]
        return len(port_8000_connections)
    except Exception as e:
        return f"Error getting network stats: {e}"

def monitor_performance(duration_minutes=5, interval_seconds=10):
    """Monitor performance for specified duration"""
    print(f"Starting performance monitoring for {duration_minutes} minutes...")
    print("=" * 60)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        system_stats = get_system_stats()
        process_stats = get_process_stats()
        network_connections = get_network_connections()
        
        print(f"\n[{system_stats['timestamp']}]")
        print(f"CPU: {system_stats['cpu_percent']}%")
        print(f"Memory: {system_stats['memory_percent']}% ({system_stats['memory_used_gb']:.1f}GB used)")
        print(f"Disk: {system_stats['disk_percent']}% ({system_stats['disk_free_gb']:.1f}GB free)")
        print(f"Active connections on port 8000: {network_connections}")
        
        if isinstance(process_stats, list):
            print(f"Django processes: {len(process_stats)}")
            for proc in process_stats[:3]:  # Show top 3 processes
                print(f"  PID {proc['pid']}: CPU {proc['cpu_percent']}%, Memory {proc['memory_percent']}%")
        
        time.sleep(interval_seconds)
    
    print("\n" + "=" * 60)
    print("Performance monitoring completed!")

if __name__ == "__main__":
    import sys
    
    duration = 5  # Default 5 minutes
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Usage: python monitor_performance.py [duration_minutes]")
            sys.exit(1)
    
    monitor_performance(duration) 