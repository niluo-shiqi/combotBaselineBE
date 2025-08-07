"""
Utility functions for Combot Backend
"""

import psutil
import threading
import time
from typing import Dict, Any
from django.conf import settings


def safe_debug_print(message: str):
    """Safely print debug messages without causing BrokenPipeError"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
    except (BrokenPipeError, OSError):
        pass


def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics"""
    try:
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'used_gb': memory.used / (1024**3),
            'available_gb': memory.available / (1024**3),
            'percent': memory.percent,
            'free_gb': memory.free / (1024**3)
        }
    except Exception as e:
        safe_debug_print(f"Error getting memory usage: {e}")
        return {}


def check_memory_threshold(threshold: int = 85) -> bool:
    """Check if memory usage is below threshold"""
    try:
        memory = psutil.virtual_memory()
        return memory.percent < threshold
    except Exception as e:
        safe_debug_print(f"Error checking memory threshold: {e}")
        return True


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a consistent cache key from arguments"""
    import hashlib
    import json
    
    # Sort kwargs for consistent key generation
    sorted_kwargs = sorted(kwargs.items())
    key_data = (args, sorted_kwargs)
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def rate_limit_check(key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Simple rate limiting check using Redis"""
    try:
        from django_redis import get_redis_connection
        redis_client = get_redis_connection("default")
        
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Remove old entries
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        request_count = redis_client.zcard(key)
        
        if request_count >= max_requests:
            return False
        
        # Add current request
        redis_client.zadd(key, {str(current_time): current_time})
        redis_client.expire(key, window_seconds)
        
        return True
    except Exception as e:
        safe_debug_print(f"Rate limit check error: {e}")
        return True  # Allow if Redis is unavailable


def get_performance_metrics() -> Dict[str, Any]:
    """Get comprehensive performance metrics"""
    try:
        memory_stats = get_memory_usage()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            'memory': memory_stats,
            'cpu_percent': cpu_percent,
            'timestamp': time.time(),
            'settings': {
                'max_concurrent_ml': settings.MAX_CONCURRENT_ML_OPERATIONS,
                'ml_cache_timeout': settings.ML_RESULT_CACHE_TIMEOUT,
                'request_queue_timeout': settings.REQUEST_QUEUE_TIMEOUT
            }
        }
    except Exception as e:
        safe_debug_print(f"Error getting performance metrics: {e}")
        return {}


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, log_interval: int = 300):  # 5 minutes
        self.log_interval = log_interval
        self.last_log_time = 0
        self.request_count = 0
        self.error_count = 0
        self.lock = threading.Lock()
    
    def log_request(self, success: bool = True):
        """Log a request for monitoring"""
        with self.lock:
            self.request_count += 1
            if not success:
                self.error_count += 1
            
            current_time = time.time()
            if current_time - self.last_log_time >= self.log_interval:
                self._log_metrics()
                self.last_log_time = current_time
    
    def _log_metrics(self):
        """Log current performance metrics"""
        metrics = get_performance_metrics()
        success_rate = ((self.request_count - self.error_count) / self.request_count * 100) if self.request_count > 0 else 0
        
        safe_debug_print(f"Performance Metrics:")
        safe_debug_print(f"  Requests: {self.request_count}")
        safe_debug_print(f"  Errors: {self.error_count}")
        safe_debug_print(f"  Success Rate: {success_rate:.1f}%")
        safe_debug_print(f"  Memory Usage: {metrics.get('memory', {}).get('percent', 0):.1f}%")
        safe_debug_print(f"  CPU Usage: {metrics.get('cpu_percent', 0):.1f}%")
        
        # Reset counters
        self.request_count = 0
        self.error_count = 0


# Global performance monitor
performance_monitor = PerformanceMonitor() 