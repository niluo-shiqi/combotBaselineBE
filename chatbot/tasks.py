"""
Celery tasks for async ML processing
"""

import time
from celery import shared_task
from django.conf import settings
from django.core.cache import caches

from .ml_service import get_ml_service
from .utils import safe_debug_print, performance_monitor


@shared_task(bind=True, name='ml.classify_text')
def classify_text_async(self, text: str, use_cache: bool = True):
    """
    Async task for ML text classification
    
    Args:
        text: Text to classify
        use_cache: Whether to use cached results
    
    Returns:
        Classification result or None
    """
    try:
        safe_debug_print(f"Starting async ML classification for text: {text[:50]}...")
        
        # Get ML service
        ml_service = get_ml_service()
        
        # Perform classification
        result, was_cached = ml_service.classify_text(text, use_cache=use_cache)
        
        if result:
            safe_debug_print(f"Async ML classification completed successfully")
            performance_monitor.log_request(success=True)
            return result
        else:
            safe_debug_print(f"Async ML classification failed")
            performance_monitor.log_request(success=False)
            return None
            
    except Exception as e:
        safe_debug_print(f"Async ML classification error: {e}")
        performance_monitor.log_request(success=False)
        self.retry(countdown=60, max_retries=3)  # Retry after 1 minute, max 3 times


@shared_task(bind=True, name='ml.batch_classify')
def batch_classify_async(self, texts: list, use_cache: bool = True):
    """
    Async task for batch ML text classification
    
    Args:
        texts: List of texts to classify
        use_cache: Whether to use cached results
    
    Returns:
        List of classification results
    """
    try:
        safe_debug_print(f"Starting batch ML classification for {len(texts)} texts")
        
        # Get ML service
        ml_service = get_ml_service()
        
        results = []
        for text in texts:
            result, was_cached = ml_service.classify_text(text, use_cache=use_cache)
            results.append({
                'text': text,
                'result': result,
                'was_cached': was_cached
            })
        
        safe_debug_print(f"Batch ML classification completed for {len(texts)} texts")
        performance_monitor.log_request(success=True)
        return results
        
    except Exception as e:
        safe_debug_print(f"Batch ML classification error: {e}")
        performance_monitor.log_request(success=False)
        self.retry(countdown=60, max_retries=3)


@shared_task(bind=True, name='cache.cleanup')
def cleanup_cache_async(self):
    """Async task to clean up old cache entries"""
    try:
        safe_debug_print("Starting cache cleanup")
        
        # Get Redis connection
        from django_redis import get_redis_connection
        redis_client = get_redis_connection("default")
        
        # Clean up old ML result cache entries (older than 2 hours)
        current_time = int(time.time())
        cutoff_time = current_time - (2 * 60 * 60)  # 2 hours ago
        
        # This is a simplified cleanup - in production you might want more sophisticated logic
        keys_to_delete = []
        for key in redis_client.scan_iter(match="ml_results:*"):
            try:
                # Check if key is old (this is a simplified approach)
                # In production, you'd store timestamps with the data
                pass
            except Exception:
                keys_to_delete.append(key)
        
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            safe_debug_print(f"Cleaned up {len(keys_to_delete)} cache entries")
        else:
            safe_debug_print("No cache entries to clean up")
            
    except Exception as e:
        safe_debug_print(f"Cache cleanup error: {e}")


@shared_task(bind=True, name='monitoring.health_check')
def health_check_async(self):
    """Async task to perform health checks"""
    try:
        from .utils import get_performance_metrics
        
        metrics = get_performance_metrics()
        ml_service = get_ml_service()
        pool_status = ml_service.get_pool_status()
        
        # Check if system is healthy
        memory_usage = metrics.get('memory', {}).get('percent', 0)
        cpu_usage = metrics.get('cpu_percent', 0)
        
        is_healthy = (
            memory_usage < 85 and
            cpu_usage < 90 and
            pool_status.get('active_requests', 0) < pool_status.get('max_concurrent', 3)
        )
        
        safe_debug_print(f"Health check - Memory: {memory_usage:.1f}%, CPU: {cpu_usage:.1f}%, Healthy: {is_healthy}")
        
        return {
            'healthy': is_healthy,
            'metrics': metrics,
            'pool_status': pool_status
        }
        
    except Exception as e:
        safe_debug_print(f"Health check error: {e}")
        return {'healthy': False, 'error': str(e)}


@shared_task(bind=True, name='ml.preload_models')
def preload_models_async(self):
    """Async task to preload ML models"""
    try:
        safe_debug_print("Starting ML model preloading")
        
        ml_service = get_ml_service()
        
        # Preload the main model
        model = ml_service.model_pool.get_model()
        
        if model:
            safe_debug_print("ML model preloaded successfully")
            return {'status': 'success', 'model_loaded': True}
        else:
            safe_debug_print("Failed to preload ML model")
            return {'status': 'error', 'model_loaded': False}
            
    except Exception as e:
        safe_debug_print(f"ML model preloading error: {e}")
        return {'status': 'error', 'error': str(e)} 