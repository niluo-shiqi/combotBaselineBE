#!/usr/bin/env python3
"""
Combot Backend Performance Dashboard
Real-time monitoring for t3.medium instance
"""

import psutil
import time
import subprocess
import os
from datetime import datetime

def get_system_stats():
    """Get comprehensive system statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used_gb': memory.used / (1024**3),
        'memory_available_gb': memory.available / (1024**3),
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024**3)
    }

def get_django_processes():
    """Get Django/Gunicorn process information"""
    django_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        if 'python' in proc.info['name'].lower() and proc.info['cpu_percent'] > 0:
            proc_info = proc.info.copy()
            proc_info['memory_mb'] = proc_info['memory_info'].rss / (1024**2)
            django_processes.append(proc_info)
    return django_processes

def get_network_stats():
    """Get network connection statistics"""
    connections = psutil.net_connections()
    port_8000_connections = [conn for conn in connections if conn.laddr.port == 8000]
    return len(port_8000_connections)

def test_api_response():
    """Test API response time"""
    try:
        import requests
        start_time = time.time()
        response = requests.get('http://localhost:8000/api/random/', timeout=5)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return response_time, response.status_code
    except Exception as e:
        return None, f"Error: {e}"

def print_dashboard():
    """Print the performance dashboard"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    # Header
    print("=" * 80)
    print("🚀 COMBOT BACKEND PERFORMANCE DASHBOARD")
    print("=" * 80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # System Stats
    system_stats = get_system_stats()
    print(f"💻 SYSTEM RESOURCES:")
    print(f"   CPU Usage:     {system_stats['cpu_percent']:5.1f}%")
    print(f"   Memory Usage:  {system_stats['memory_percent']:5.1f}% ({system_stats['memory_used_gb']:.1f}GB / 4GB)")
    print(f"   Memory Free:   {system_stats['memory_available_gb']:.1f}GB")
    print(f"   Disk Usage:    {system_stats['disk_percent']:5.1f}% ({system_stats['disk_free_gb']:.1f}GB free)")
    
    # Network Stats
    network_connections = get_network_stats()
    print(f"\n🌐 NETWORK:")
    print(f"   Active Connections (Port 8000): {network_connections}")
    
    # Django Processes
    django_processes = get_django_processes()
    print(f"\n🐍 DJANGO PROCESSES ({len(django_processes)} total):")
    for i, proc in enumerate(django_processes[:4], 1):
        print(f"   Process {i}: PID {proc['pid']:5d} | CPU {proc['cpu_percent']:5.1f}% | Memory {proc['memory_mb']:6.1f}MB")
    
    # Performance Metrics
    print(f"\n⚡ PERFORMANCE METRICS:")
    print(f"   t3.medium Capacity: 50-100 concurrent users")
    print(f"   Current Load:       {'🟢 Low' if system_stats['cpu_percent'] < 30 else '🟡 Medium' if system_stats['cpu_percent'] < 70 else '🔴 High'}")
    print(f"   Memory Status:      {'🟢 Good' if system_stats['memory_percent'] < 70 else '🟡 Warning' if system_stats['memory_percent'] < 90 else '🔴 Critical'}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if system_stats['cpu_percent'] < 20:
        print("   ✅ System is running efficiently")
        print("   ✅ Can handle more concurrent users")
    elif system_stats['cpu_percent'] < 50:
        print("   ⚠️  Moderate load - monitor closely")
    else:
        print("   🔴 High load - consider scaling up")
    
    print("=" * 80)
    print("Press Ctrl+C to stop monitoring")
    print("=" * 80)

def monitor_performance(interval_seconds=10):
    """Monitor performance continuously"""
    try:
        while True:
            print_dashboard()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped.")
        print("📊 Final Summary:")
        system_stats = get_system_stats()
        print(f"   Final CPU: {system_stats['cpu_percent']:.1f}%")
        print(f"   Final Memory: {system_stats['memory_percent']:.1f}%")

if __name__ == "__main__":
    print("Starting performance monitoring...")
    monitor_performance() 