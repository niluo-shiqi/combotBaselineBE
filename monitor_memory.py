#!/usr/bin/env python3
"""
Memory Monitoring Script for Combot Backend
Monitors memory usage and alerts when thresholds are exceeded
"""

import psutil
import time
import subprocess
import os
from datetime import datetime

def get_memory_usage():
    """Get current memory usage"""
    memory = psutil.virtual_memory()
    return {
        'total': memory.total / (1024**3),  # GB
        'available': memory.available / (1024**3),  # GB
        'used': memory.used / (1024**3),  # GB
        'percent': memory.percent
    }

def get_process_memory():
    """Get memory usage of gunicorn processes"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if 'gunicorn' in proc.info['name'].lower():
                memory_mb = proc.info['memory_info'].rss / (1024**2)
                processes.append({
                    'pid': proc.info['pid'],
                    'memory_mb': memory_mb
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def check_database_connections():
    """Check database connection count"""
    try:
        result = subprocess.run([
            'python', 'manage.py', 'shell', '-c',
            'from django.db import connection; print(len(connection.queries))'
        ], capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except:
        return "Unknown"

def main():
    print("🔍 COMBOT BACKEND MEMORY MONITOR")
    print("=" * 50)
    
    while True:
        try:
            # Get system memory
            memory = get_memory_usage()
            
            # Get process memory
            processes = get_process_memory()
            
            # Get database connections
            db_connections = check_database_connections()
            
            # Print current status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ {timestamp}")
            print(f"💾 System Memory: {memory['used']:.1f}GB / {memory['total']:.1f}GB ({memory['percent']:.1f}%)")
            print(f"📊 Available Memory: {memory['available']:.1f}GB")
            
            if processes:
                total_process_memory = sum(p['memory_mb'] for p in processes)
                print(f"🔄 Gunicorn Processes: {len(processes)}")
                print(f"📈 Total Process Memory: {total_process_memory:.1f}MB")
                for proc in processes:
                    print(f"   PID {proc['pid']}: {proc['memory_mb']:.1f}MB")
            else:
                print("❌ No gunicorn processes found")
            
            print(f"🗄️  Database Queries: {db_connections}")
            
            # Alert thresholds
            if memory['percent'] > 80:
                print("⚠️  WARNING: High memory usage!")
            if memory['percent'] > 90:
                print("🚨 CRITICAL: Very high memory usage!")
                print("💡 Consider restarting the server")
            
            if processes and any(p['memory_mb'] > 500 for p in processes):
                print("⚠️  WARNING: Individual process using >500MB")
            
            print("-" * 50)
            
            # Wait 30 seconds before next check
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in monitoring: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main() 