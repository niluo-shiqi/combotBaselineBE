#!/usr/bin/env python3
"""
Enhanced Memory Monitoring Script for Combot Backend
Monitors memory usage, Redis cache, and alerts when thresholds are exceeded
Now includes advanced memory management integration
"""

import psutil
import time
import subprocess
import os
import json
from datetime import datetime
import redis

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

def check_redis_status():
    """Check Redis cache status and memory usage"""
    try:
        # Try to connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=1)
        info = r.info()
        
        # Get cache statistics
        ml_cache_keys = len(r.keys("ml_results:*"))
        product_cache_keys = len(r.keys("product_breakdown:*"))
        
        return {
            'connected': True,
            'memory_used_mb': info.get('used_memory_human', 'Unknown'),
            'memory_peak_mb': info.get('used_memory_peak_human', 'Unknown'),
            'ml_cache_keys': ml_cache_keys,
            'product_cache_keys': product_cache_keys,
            'total_keys': info.get('db0', {}).get('keys', 0)
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }

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

def check_ml_model_status():
    """Check if ML model is loaded and memory usage"""
    try:
        result = subprocess.run([
            'python', 'manage.py', 'shell', '-c',
            'from chatbot.views import memory_manager; print(memory_manager.ml_model is not None)'
        ], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() == 'True'
    except:
        return False

def get_system_stats():
    """Get comprehensive system statistics"""
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_usage = {
        'total': disk.total / (1024**3),  # GB
        'used': disk.used / (1024**3),  # GB
        'free': disk.free / (1024**3),  # GB
        'percent': (disk.used / disk.total) * 100
    }
    
    # Network I/O
    net_io = psutil.net_io_counters()
    network = {
        'bytes_sent': net_io.bytes_sent / (1024**2),  # MB
        'bytes_recv': net_io.bytes_recv / (1024**2),  # MB
    }
    
    return {
        'cpu_percent': cpu_percent,
        'disk': disk_usage,
        'network': network
    }

def main():
    print("🔍 ENHANCED COMBOT BACKEND MEMORY MONITOR")
    print("=" * 60)
    
    while True:
        try:
            # Get system memory
            memory = get_memory_usage()
            
            # Get process memory
            processes = get_process_memory()
            
            # Get Redis status
            redis_status = check_redis_status()
            
            # Get database connections
            db_connections = check_database_connections()
            
            # Check ML model status
            ml_model_loaded = check_ml_model_status()
            
            # Get system stats
            system_stats = get_system_stats()
            
            # Print current status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ {timestamp}")
            print(f"💾 System Memory: {memory['used']:.1f}GB / {memory['total']:.1f}GB ({memory['percent']:.1f}%)")
            print(f"📊 Available Memory: {memory['available']:.1f}GB")
            print(f"🖥️  CPU Usage: {system_stats['cpu_percent']:.1f}%")
            print(f"💿 Disk Usage: {system_stats['disk']['used']:.1f}GB / {system_stats['disk']['total']:.1f}GB ({system_stats['disk']['percent']:.1f}%)")
            
            if processes:
                total_process_memory = sum(p['memory_mb'] for p in processes)
                print(f"🔄 Gunicorn Processes: {len(processes)}")
                print(f"📈 Total Process Memory: {total_process_memory:.1f}MB")
                for proc in processes:
                    print(f"   PID {proc['pid']}: {proc['memory_mb']:.1f}MB")
            else:
                print("❌ No gunicorn processes found")
            
            # Redis status
            if redis_status['connected']:
                print(f"🔴 Redis: Connected")
                print(f"   Memory: {redis_status['memory_used_mb']}")
                print(f"   Peak Memory: {redis_status['memory_peak_mb']}")
                print(f"   ML Cache Keys: {redis_status['ml_cache_keys']}")
                print(f"   Product Cache Keys: {redis_status['product_cache_keys']}")
                print(f"   Total Keys: {redis_status['total_keys']}")
            else:
                print(f"❌ Redis: Disconnected - {redis_status.get('error', 'Unknown error')}")
            
            print(f"🤖 ML Model: {'✅ Loaded' if ml_model_loaded else '❌ Not Loaded'}")
            print(f"🗄️  Database Queries: {db_connections}")
            print(f"🌐 Network I/O: ↑{system_stats['network']['bytes_sent']:.1f}MB ↓{system_stats['network']['bytes_recv']:.1f}MB")
            
            # Alert thresholds
            if memory['percent'] > 80:
                print("⚠️  WARNING: High memory usage!")
            if memory['percent'] > 90:
                print("🚨 CRITICAL: Very high memory usage!")
                print("💡 Consider restarting the server")
            
            if processes and any(p['memory_mb'] > 500 for p in processes):
                print("⚠️  WARNING: Individual process using >500MB")
            
            if system_stats['cpu_percent'] > 80:
                print("⚠️  WARNING: High CPU usage!")
            
            if system_stats['disk']['percent'] > 85:
                print("⚠️  WARNING: High disk usage!")
            
            print("-" * 60)
            
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