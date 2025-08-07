"""
ML Service Module for Combot Backend
Provides optimized ML model management with caching, pooling, and async processing
"""

import hashlib
import json
import threading
import time
from typing import Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import psutil

from django.conf import settings
from django.core.cache import caches
from django_redis import get_redis_connection
from transformers import pipeline
import redis

from .utils import safe_debug_print, get_memory_usage


class MLModelPool:
    """
    Thread-safe ML model pool for sharing models across requests
    """
    
    def __init__(self, max_models: int = 2):
        self.max_models = max_models
        self.models = {}
        self.model_locks = {}
        self.pool_lock = threading.Lock()
        self.request_queue = []
        self.queue_lock = threading.Lock()
        
    def get_model(self, model_name: str = "jpsteinhafel/complaints_classifier") -> Optional[Any]:
        """Get a model from the pool, creating if necessary"""
        with self.pool_lock:
            if model_name not in self.models:
                if len(self.models) >= self.max_models:
                    # Remove least recently used model
                    lru_model = min(self.models.keys(), key=lambda k: self.models[k]['last_used'])
                    safe_debug_print(f"Removing LRU model: {lru_model}")
                    del self.models[lru_model]
                
                try:
                    safe_debug_print(f"Loading model: {model_name}")
                    model = pipeline("text-classification", model=model_name)
                    self.models[model_name] = {
                        'model': model,
                        'last_used': time.time(),
                        'lock': threading.Lock()
                    }
                    safe_debug_print(f"Model loaded successfully: {model_name}")
                except Exception as e:
                    safe_debug_print(f"Error loading model {model_name}: {e}")
                    return None
            
            # Update last used time
            self.models[model_name]['last_used'] = time.time()
            return self.models[model_name]['model']
    
    def cleanup_old_models(self, max_age: int = 3600):
        """Clean up models that haven't been used recently"""
        current_time = time.time()
        with self.pool_lock:
            models_to_remove = []
            for model_name, model_info in self.models.items():
                if current_time - model_info['last_used'] > max_age:
                    models_to_remove.append(model_name)
            
            for model_name in models_to_remove:
                safe_debug_print(f"Cleaning up old model: {model_name}")
                del self.models[model_name]


class MLResultCache:
    """
    Redis-based caching for ML classification results
    """
    
    def __init__(self):
        self.cache = caches['ml_results']
        self.redis_client = get_redis_connection("default")
    
    def _generate_cache_key(self, text: str) -> str:
        """Generate a cache key for the given text"""
        # Normalize text for consistent caching
        normalized_text = text.lower().strip()
        text_hash = hashlib.md5(normalized_text.encode()).hexdigest()
        return f"ml_classification:{text_hash}"
    
    def get_cached_result(self, text: str) -> Optional[Dict]:
        """Get cached ML classification result"""
        try:
            cache_key = self._generate_cache_key(text)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                safe_debug_print(f"Cache hit for text: {text[:50]}...")
                return cached_result
        except Exception as e:
            safe_debug_print(f"Cache get error: {e}")
        return None
    
    def set_cached_result(self, text: str, result: Dict, timeout: int = None):
        """Cache ML classification result"""
        try:
            cache_key = self._generate_cache_key(text)
            timeout = timeout or settings.ML_RESULT_CACHE_TIMEOUT
            self.cache.set(cache_key, result, timeout=timeout)
            safe_debug_print(f"Cached result for text: {text[:50]}...")
        except Exception as e:
            safe_debug_print(f"Cache set error: {e}")
    
    def invalidate_cache(self, pattern: str = "ml_classification:*"):
        """Invalidate cache entries matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                safe_debug_print(f"Invalidated {len(keys)} cache entries")
        except Exception as e:
            safe_debug_print(f"Cache invalidation error: {e}")


class RequestQueue:
    """
    Thread-safe request queue for limiting concurrent ML operations
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.active_requests = 0
        self.queue = []
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
    
    def acquire_slot(self, timeout: int = 30) -> bool:
        """Acquire a slot for ML processing"""
        with self.condition:
            start_time = time.time()
            while self.active_requests >= self.max_concurrent:
                remaining_timeout = timeout - (time.time() - start_time)
                if remaining_timeout <= 0:
                    safe_debug_print("Request queue timeout")
                    return False
                
                if not self.condition.wait(remaining_timeout):
                    safe_debug_print("Request queue timeout")
                    return False
            
            self.active_requests += 1
            safe_debug_print(f"Acquired ML slot. Active: {self.active_requests}")
            return True
    
    def release_slot(self):
        """Release a slot after ML processing"""
        with self.condition:
            self.active_requests = max(0, self.active_requests - 1)
            self.condition.notify()
            safe_debug_print(f"Released ML slot. Active: {self.active_requests}")


class MLService:
    """
    Main ML service that coordinates model pooling, caching, and async processing
    """
    
    def __init__(self):
        self.model_pool = MLModelPool(max_models=2)
        self.result_cache = MLResultCache()
        self.request_queue = RequestQueue(max_concurrent=settings.MAX_CONCURRENT_ML_OPERATIONS)
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for model cleanup"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    self.model_pool.cleanup_old_models()
                except Exception as e:
                    safe_debug_print(f"Cleanup worker error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def classify_text(self, text: str, use_cache: bool = True) -> Tuple[Optional[Dict], bool]:
        """
        Classify text using ML model with caching and queuing
        
        Returns:
            Tuple of (classification_result, was_cached)
        """
        if not text or not text.strip():
            return None, False
        
        # Check cache first
        if use_cache:
            cached_result = self.result_cache.get_cached_result(text)
            if cached_result:
                return cached_result, True
        
        # Acquire processing slot
        if not self.request_queue.acquire_slot():
            safe_debug_print("Could not acquire ML processing slot")
            return None, False
        
        try:
            # Get model from pool
            model = self.model_pool.get_model()
            if not model:
                safe_debug_print("Could not get ML model from pool")
                return None, False
            
            # Perform classification
            start_time = time.time()
            result = model(text, return_all_scores=True)
            processing_time = time.time() - start_time
            
            # Process results
            if result and len(result) > 0:
                all_scores = result[0]
                scores = {}
                for item in all_scores:
                    scores[item["label"]] = item["score"]
                
                classification_result = {
                    'scores': scores,
                    'primary_type': max(scores, key=scores.get),
                    'confidence': scores[max(scores, key=scores.get)],
                    'processing_time': processing_time,
                    'timestamp': time.time()
                }
                
                # Cache result
                if use_cache:
                    self.result_cache.set_cached_result(text, classification_result)
                
                safe_debug_print(f"ML classification completed in {processing_time:.2f}s")
                return classification_result, False
            else:
                safe_debug_print("ML classification returned empty result")
                return None, False
                
        except Exception as e:
            safe_debug_print(f"ML classification error: {e}")
            return None, False
        finally:
            self.request_queue.release_slot()
    
    def classify_text_async(self, text: str) -> Any:
        """Submit classification task to async executor"""
        return self.executor.submit(self.classify_text, text)
    
    def get_pool_status(self) -> Dict:
        """Get status of model pool and request queue"""
        return {
            'active_models': len(self.model_pool.models),
            'max_models': self.model_pool.max_models,
            'active_requests': self.request_queue.active_requests,
            'max_concurrent': self.request_queue.max_concurrent,
            'memory_usage': get_memory_usage()
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
        self.model_pool.cleanup_old_models(max_age=0)  # Remove all models


# Global ML service instance
_ml_service = None
_ml_service_lock = threading.Lock()


def get_ml_service() -> MLService:
    """Get or create the global ML service instance"""
    global _ml_service
    if _ml_service is None:
        with _ml_service_lock:
            if _ml_service is None:
                _ml_service = MLService()
    return _ml_service


def cleanup_ml_service():
    """Clean up the global ML service"""
    global _ml_service
    if _ml_service:
        _ml_service.cleanup()
        _ml_service = None 