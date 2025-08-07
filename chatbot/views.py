from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from transformers import pipeline
from django.utils.safestring import mark_safe
from django.utils.html import escape
from urllib.parse import quote
from .models import Conversation
from transformers import pipeline
import random
import json
import openai
import os
import gc
import threading
import time
import hashlib
import psutil
import signal
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from django_redis import get_redis_connection
from django.db import connection
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Advanced Memory Management Configuration
class MemoryManager:
    def __init__(self):
        self.user_count = 0
        self.max_users_per_process = 200  # Increased from 50 to 200 for better stability
        self.ml_model = None
        self.model_lock = threading.Lock()
        self.model_loading = False  # Prevent concurrent model loading
        self.redis_client = None
        self.connection_pool = {}
        self.pool_lock = threading.Lock()
        
        # Adjusted memory thresholds for t3.large (8GB RAM)
        self.memory_threshold = 0.60  # 60% memory usage - trigger cleanup (4.8GB)
        self.force_cleanup_threshold = 0.75  # 75% memory usage - force cleanup (6GB)
        self.critical_threshold = 0.85  # 85% memory usage - emergency cleanup (6.8GB)
        self.last_cleanup_time = 0
        self.cleanup_cooldown = 120  # Increased from 60 to 120 seconds between cleanups
        
        # Memory tracking
        self.memory_history = []
        self.max_memory_history = 100
        
        # Initialize Redis connection
        try:
            self.redis_client = get_redis_connection("default")
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def get_memory_usage(self):
        """Get current memory usage percentage"""
        memory = psutil.virtual_memory()
        return memory.percent / 100.0
    
    def track_memory_usage(self):
        """Track memory usage for trend analysis"""
        current_usage = self.get_memory_usage()
        current_time = time.time()
        
        self.memory_history.append({
            'usage': current_usage,
            'timestamp': current_time,
            'user_count': self.user_count
        })
        
        # Keep only recent history
        if len(self.memory_history) > self.max_memory_history:
            self.memory_history.pop(0)
        
        return current_usage
    
    def check_memory_trends(self):
        """Analyze memory usage trends"""
        if len(self.memory_history) < 10:
            return None
        
        recent = self.memory_history[-10:]
        recent_avg = sum(entry['usage'] for entry in recent) / len(recent)
        
        if len(self.memory_history) >= 20:
            older = self.memory_history[-20:-10]
            older_avg = sum(entry['usage'] for entry in older) / len(older)
            
            # Check for memory leak trend
            if recent_avg > older_avg + 0.1:  # 10% increase
                return 'increasing'
            elif recent_avg < older_avg - 0.05:  # 5% decrease
                return 'decreasing'
        
        return 'stable'
    
    def should_trigger_cleanup(self):
        """Check if cleanup should be triggered based on memory thresholds"""
        current_usage = self.track_memory_usage()
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_cleanup_time < self.cleanup_cooldown:
            return False
        
        # Only trigger cleanup if we're not in the middle of heavy usage
        if self.user_count > 20:  # Increased from 10 to 20 - don't interrupt during moderate usage
            # Only trigger if memory is critically high
            if current_usage > self.critical_threshold:
                logger.warning(f"CRITICAL: Memory usage at {current_usage:.1%} during heavy usage, triggering emergency cleanup")
                return True
            return False
        
        # Critical threshold - immediate cleanup (only when not busy)
        if current_usage > self.critical_threshold:
            logger.warning(f"CRITICAL: Memory usage at {current_usage:.1%}, triggering emergency cleanup")
            return True
        
        # Force cleanup threshold
        if current_usage > self.force_cleanup_threshold:
            logger.warning(f"WARNING: Memory usage at {current_usage:.1%}, triggering forced cleanup")
            return True
        
        # Normal cleanup threshold - only if trend is increasing
        if current_usage > self.memory_threshold:
            # Check memory trends
            trend = self.check_memory_trends()
            if trend == 'increasing':
                logger.info(f"Memory usage at {current_usage:.1%} with increasing trend, triggering cleanup")
                return True
            elif trend == 'stable' and current_usage > self.memory_threshold + 0.05:  # 5% above threshold
                logger.info(f"Memory usage at {current_usage:.1%} above threshold, triggering cleanup")
                return True
        
        return False
    
    def should_recycle_process(self):
        """Check if process should be recycled based on user count or memory"""
        return self.user_count >= self.max_users_per_process or self.should_trigger_cleanup()
    
    def increment_user_count(self):
        """Increment user count and check for process recycling"""
        self.user_count += 1
        
        # Check memory thresholds before user processing
        if self.should_trigger_cleanup():
            logger.info(f"Memory threshold triggered cleanup after {self.user_count} users")
            self.force_cleanup()
            return True
        
        if self.should_recycle_process():
            logger.info(f"Process recycling triggered after {self.user_count} users")
            self.recycle_process()
            return True
        return False
    
    def recycle_process(self):
        """Recycle the current process"""
        logger.info("Starting process recycling...")
        
        # Clear all caches
        self.clear_all_caches()
        
        # Unload ML model
        self.unload_ml_model()
        
        # Force garbage collection
        for _ in range(3):
            gc.collect()
        
        # Reset user count
        self.user_count = 0
        
        # Close database connections
        self.close_database_connections()
        
        # Update cleanup timestamp
        self.last_cleanup_time = time.time()
        
        logger.info("Process recycling completed")
    
    def unload_ml_model(self):
        """Unload the ML model to free memory"""
        with self.model_lock:
            if self.ml_model is not None:
                del self.ml_model
                self.ml_model = None
                logger.info("ML model unloaded")
    
    def load_ml_model(self):
        """Load the ML model with memory management and concurrent loading protection"""
        with self.model_lock:
            if self.ml_model is not None:
                return self.ml_model
            
            # Check if model is already being loaded
            if self.model_loading:
                logger.info("ML model is already being loaded, waiting...")
                # Wait for model to finish loading
                while self.model_loading:
                    time.sleep(0.1)
                return self.ml_model
            
            try:
                # Set loading flag
                self.model_loading = True
                
                # Check memory before loading
                current_usage = self.get_memory_usage()
                if current_usage > self.memory_threshold:
                    logger.warning(f"High memory usage ({current_usage:.1%}), forcing cleanup before model load")
                    self.force_cleanup()
                
                logger.info("Loading ML classifier...")
                self.ml_model = pipeline("text-classification", model="jpsteinhafel/complaints_classifier")
                logger.info("ML classifier loaded successfully")
                
                # Force garbage collection after loading
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error loading ML classifier: {e}")
                self.ml_model = None
                return None
            finally:
                # Clear loading flag
                self.model_loading = False
                
            return self.ml_model
    
    def get_ml_model(self):
        """Get the ML model with automatic loading"""
        return self.load_ml_model()
    
    def clear_all_caches(self):
        """Clear all caches including Redis - more selective approach"""
        # Clear Redis cache selectively instead of flushing entire DB
        if self.redis_client:
            try:
                # Only clear ML-related keys, not entire database
                ml_keys = self.redis_client.keys("ml_results:*")
                if ml_keys:
                    self.redis_client.delete(*ml_keys)
                    logger.info(f"Cleared {len(ml_keys)} ML cache keys from Redis")
                
                # Clear old session data (older than 1 hour)
                session_keys = self.redis_client.keys("combot_cache:*")
                if session_keys:
                    # Only delete sessions older than 1 hour
                    current_time = time.time()
                    old_sessions = []
                    for key in session_keys:
                        try:
                            ttl = self.redis_client.ttl(key)
                            if ttl > 0 and ttl < 3600:  # Less than 1 hour TTL
                                old_sessions.append(key)
                        except:
                            pass
                    
                    if old_sessions:
                        self.redis_client.delete(*old_sessions)
                        logger.info(f"Cleared {len(old_sessions)} old session keys from Redis")
                        
            except Exception as e:
                logger.warning(f"Failed to clear Redis cache: {e}")
        
        # Clear connection pools
        with self.pool_lock:
            for pool_name, pool in self.connection_pool.items():
                try:
                    pool.close()
                    logger.info(f"Connection pool '{pool_name}' closed")
                except Exception as e:
                    logger.warning(f"Failed to close connection pool '{pool_name}': {e}")
            self.connection_pool.clear()
        
        # Clear memory history
        self.memory_history.clear()
        
        logger.info("Selective cache clearing completed")
    
    def force_cleanup(self):
        """Force aggressive cleanup when memory is high"""
        logger.warning("FORCING AGGRESSIVE CLEANUP")
        
        # Unload ML model immediately
        self.unload_ml_model()
        
        # Clear all caches
        self.clear_all_caches()
        
        # Force multiple garbage collection cycles
        for i in range(5):
            collected = gc.collect()
            logger.info(f"Garbage collection cycle {i+1}: collected {collected} objects")
        
        # Close database connections
        self.close_database_connections()
        
        # Reset user count to trigger process recycling
        self.user_count = self.max_users_per_process
        
        # Update cleanup timestamp
        self.last_cleanup_time = time.time()
        
        logger.warning("Aggressive cleanup completed")
    
    def close_database_connections(self):
        """Close database connections to free memory"""
        try:
            from django.db import connection
            connection.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.warning(f"Failed to close database connections: {e}")
    
    def get_connection_pool(self, pool_name):
        """Get or create a connection pool with memory management"""
        with self.pool_lock:
            if pool_name not in self.connection_pool:
                # Check memory before creating new pool
                if self.get_memory_usage() > self.memory_threshold:
                    logger.warning("High memory usage, skipping new connection pool creation")
                    return None
                
                self.connection_pool[pool_name] = {}
                logger.info(f"Created connection pool '{pool_name}'")
            
            return self.connection_pool[pool_name]
    
    def get_cached_result(self, key, ttl=7200):
        """Get cached result with memory management"""
        if self.redis_client:
            try:
                result = self.redis_client.get(key)
                if result:
                    return json.loads(result)
            except Exception as e:
                logger.warning(f"Failed to get cached result: {e}")
        return None
    
    def set_cached_result(self, key, value, ttl=7200):
        """Set cached result with memory management"""
        if self.redis_client:
            try:
                # Check memory before caching
                if self.get_memory_usage() > self.force_cleanup_threshold:
                    logger.warning("High memory usage, skipping cache set")
                    return False
                
                self.redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception as e:
                logger.warning(f"Failed to set cached result: {e}")
        return False

# Initialize global memory manager
memory_manager = MemoryManager()

# Global cache for ML model to prevent reloading on every request
_ml_classifier = None
_ml_classifier_lock = threading.Lock()

# Temporary storage for product_type_breakdown data (conversation_key -> data)
_product_type_breakdown_cache = {}
_product_type_breakdown_lock = threading.Lock()

# Enhanced memory optimization for unlimited users
_ml_result_cache = {}  # Reduced cache size for memory efficiency
_cache_lock = threading.Lock()
_max_cache_size = 100  # Increased from 50 for better cache hit rate
_ml_executor = ThreadPoolExecutor(max_workers=4)  # Increased from 2 for better concurrency
_active_requests = 0
_request_lock = threading.Lock()

# Enhanced cleanup tracking with better thresholds
_request_count = 0
_last_cleanup = 0
_cleanup_interval = 50  # Increased from 25 - less frequent cleanup
_memory_pressure = 0
_max_memory_pressure = 15  # Increased from 10 - more tolerance

# Request queue management
_request_queue = []
_queue_lock = threading.Lock()
_max_queue_size = 20  # Maximum requests waiting for ML processing

def get_cache_key(text: str) -> str:
    """Generate a cache key for the given text"""
    normalized_text = text.lower().strip()
    return hashlib.md5(normalized_text.encode()).hexdigest()

def get_cached_ml_result(text: str):
    """Get cached ML classification result with Redis fallback"""
    cache_key = get_cache_key(text)
    
    # Try Redis first
    redis_key = f"ml_results:{cache_key}"
    result = memory_manager.get_cached_result(redis_key)
    if result:
        logger.info(f"Redis cache hit for text: {text[:50]}...")
        return result
    
    # Try in-memory cache
    with _cache_lock:
        if cache_key in _ml_result_cache:
            logger.info(f"In-memory cache hit for text: {text[:50]}...")
            return _ml_result_cache[cache_key]
    
    return None

def set_cached_ml_result(text: str, result: dict):
    """Cache ML classification result with Redis and in-memory"""
    cache_key = get_cache_key(text)
    redis_key = f"ml_results:{cache_key}"
    
    # Cache in Redis
    memory_manager.set_cached_result(redis_key, result, ttl=7200)  # 2 hours TTL
    
    # Cache in memory with cleanup
    with _cache_lock:
        # Aggressive cache cleanup
        if len(_ml_result_cache) >= _max_cache_size:
            # Remove 50% of cache entries
            keys_to_remove = list(_ml_result_cache.keys())[:len(_ml_result_cache)//2]
            for key in keys_to_remove:
                del _ml_result_cache[key]
            logger.info(f"Cleaned up {len(keys_to_remove)} in-memory cache entries (50% reduction)")
        
        _ml_result_cache[cache_key] = result
        logger.info(f"Cached result for text: {text[:50]}...")

def acquire_ml_slot():
    """Acquire a slot for ML processing"""
    global _active_requests
    with _request_lock:
        if _active_requests >= 4:  # Increased from 2 to 4 for better concurrency
            return False
        _active_requests += 1
        logger.info(f"Acquired ML slot. Active: {_active_requests}")
        return True

def release_ml_slot():
    """Release a slot after ML processing"""
    global _active_requests
    with _request_lock:
        _active_requests = max(0, _active_requests - 1)
        logger.info(f"Released ML slot. Active: {_active_requests}")

def get_ml_classifier():
    """Get or create the ML classifier with enhanced memory management"""
    return memory_manager.get_ml_model()

def check_and_cleanup():
    """Enhanced cleanup with request tracking and memory monitoring"""
    global _request_count, _last_cleanup, _memory_pressure
    
    _request_count += 1
    
    # Check memory usage
    memory_usage = memory_manager.get_memory_usage()
    if memory_usage > memory_manager.force_cleanup_threshold:
        logger.warning(f"Critical memory usage: {memory_usage:.1%}, forcing cleanup")
        memory_manager.force_cleanup()
        _last_cleanup = _request_count
        _memory_pressure = 0
        return True
    elif memory_usage > memory_manager.memory_threshold:
        _memory_pressure += 1
        logger.info(f"High memory usage: {memory_usage:.1%}, pressure: {_memory_pressure}")
    
    # Force cleanup every N requests
    if _request_count - _last_cleanup >= _cleanup_interval:
        logger.info(f"Force cleanup triggered after {_cleanup_interval} requests")
        memory_manager.clear_all_caches()
        _last_cleanup = _request_count
        _memory_pressure = 0
        return True
    
    # Check for memory pressure
    if _memory_pressure >= _max_memory_pressure:
        logger.info(f"Memory pressure cleanup triggered ({_memory_pressure} high-pressure requests)")
        memory_manager.clear_all_caches()
        _memory_pressure = 0
        return True
    
    return False

def classify_text_optimized(text: str):
    """Optimized ML classification with advanced memory management and timeout handling"""
    if not text or not text.strip():
        return None
    
    # Check for cleanup
    check_and_cleanup()
    
    # Check cache first
    cached_result = get_cached_ml_result(text)
    if cached_result:
        return cached_result, True  # Return cached result
    
    # Acquire ML processing slot with timeout
    if not acquire_ml_slot():
        logger.warning("No ML slot available, returning None")
        return None, False
    
    try:
        # Get ML classifier
        classifier = memory_manager.get_ml_model()
        if not classifier:
            logger.error("Failed to get ML classifier")
            return None, False
        
        # Perform classification with timeout
        logger.info(f"Processing ML classification for: {text[:50]}...")
        
        # Use ThreadPoolExecutor with timeout for ML processing
        future = _ml_executor.submit(classifier, text, return_all_scores=True)
        try:
            all_scores = future.result(timeout=15)  # 15 second timeout for ML processing
        except Exception as e:
            logger.error(f"ML classification timeout or error: {e}")
            return None, False
        
        # Process results
        scores = {}
        for item in all_scores[0]:
            scores[item["label"]] = item["score"]
        
        # Get primary type and confidence
        class_type, confidence = get_primary_problem_type(scores)
        
        result = {
            'scores': scores,
            'primary_type': class_type,
            'confidence': confidence
        }
        
        # Cache the result
        set_cached_ml_result(text, result)
        
        # Enhanced garbage collection after processing
        gc.collect()
        
        return result, False  # Return fresh result
        
    except Exception as e:
        logger.error(f"ERROR: ML classification failed: {e}")
        # Increment memory pressure on errors
        global _memory_pressure
        _memory_pressure += 1
        return None, False
    finally:
        release_ml_slot()

def cleanup_resources():
    """Enhanced resource cleanup for unlimited users"""
    global _ml_result_cache, _product_type_breakdown_cache, _request_count
    
    try:
        # Clear ML result cache
        with _cache_lock:
            cache_size = len(_ml_result_cache)
            _ml_result_cache.clear()
            logger.info(f"Cleared ML result cache ({cache_size} entries)")
        
        # Clear product type breakdown cache
        with _product_type_breakdown_lock:
            breakdown_size = len(_product_type_breakdown_cache)
            _product_type_breakdown_cache.clear()
            logger.info(f"Cleared product type breakdown cache ({breakdown_size} entries)")
        
        # Multiple garbage collection passes
        for i in range(3):
            collected = gc.collect()
            logger.info(f"Garbage collection pass {i+1}: collected {collected} objects")
        
        # Reset request count
        _request_count = 0
        
        logger.info("Enhanced cleanup completed - ready for next batch")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def safe_debug_print(message):
    """Safely print debug messages without causing BrokenPipeError"""
    try:
        logger.info(message)
    except (BrokenPipeError, OSError):
        pass  # Ignore broken pipe errors from debug prints

openai.api_key = os.getenv('OPENAI_API_KEY')

def create_safe_link(url, text):
    """
    Create a safe HTML link with proper URL escaping
    """
    escaped_url = quote(url, safe=':/?=&')
    escaped_text = escape(text)
    generated_html = f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{escaped_text}</a>'
    return mark_safe(generated_html)

def get_primary_problem_type(scores):
    """
    Get the primary problem type with the highest confidence score (returning both pieces of info)
    """
    primary_type = max(scores, key=scores.get)
    return primary_type, scores[primary_type]

def get_openai_response(brand, think_level, feel_level, problem_type, response_type, user_input=None, chat_log=None):
    """
    Consolidated function to handle all OpenAI chat completions based on scenario parameters.
    
    Args:
        brand (str): 'Basic' or 'Lulu'
        think_level (str): 'High' or 'Low'
        feel_level (str): 'High' or 'Low'
        problem_type (str): 'A', 'B', 'C', or 'Other'
        response_type (str): 'initial', 'continuation', 'paraphrase', 'index_10', 'low_continuation'
        user_input (str): Customer's input message (for initial, paraphrase, index_10)
        chat_log (list/dict): Chat history (for continuation responses)
    
    Returns:
        str: Generated response from OpenAI
    """
    
    # Define prompts based on scenario
    prompts = {
        # Basic brand prompts
        'Basic': {
            'High': {  # High think
                'High': {  # High feel
                    'initial': "Empathetic customer service. Paraphrase complaint and ask for details. 3-4 sentences.",
                    'continuation': "Empathetic customer service. Based on conversation, acknowledge and ask relevant follow-ups. Don't ask for info already provided. 3-4 sentences.",
                    'paraphrase': "Empathetic customer service. Acknowledge concern and ask relevant questions. Don't just repeat. 3-4 sentences.",
                    'index_10': "Empathetic customer service. Paraphrase complaint and ask for more info. 3-4 sentences.",
                    'low_continuation': "Empathetic customer service. Based on conversation, acknowledge what was said and ask a simple follow-up question. Keep it brief and conversational. 3-4 sentences."
                },
                'Low': {  # Low feel
                    'initial': "Robotic but effective customer service. Paraphrase complaint and ask for specific info efficiently. Systematic and unemotional. 3-4 sentences.",
                    'continuation': "Robotic but effective customer service. Based on conversation, gather remaining info efficiently. Don't ask for info already provided. Systematic and unemotional. 3-4 sentences.",
                    'paraphrase': "Robotic but effective customer service. Acknowledge concern and provide systematic response. Don't just repeat. Systematic and unemotional. 3-4 sentences.",
                    'index_10': "Robotic but effective customer service. Paraphrase complaint and ask for specific info efficiently. Systematic and unemotional. 3-4 sentences.",
                    'low_continuation': "Robotic but effective customer service. Based on conversation, acknowledge the information and ask for the next required detail. Be systematic and brief. 3-4 sentences."
                }
            },
            'Low': {  # Low think
                'High': {  # High feel
                    'initial': "Well-intentioned but unhelpful customer service. Paraphrase complaint and show empathy, but be unhelpful. 3-4 sentences.",
                    'continuation': "Well-intentioned but unhelpful customer service. Based on conversation, provide generic response that misses key details. Empathetic but unhelpful. 3-4 sentences.",
                    'paraphrase': "Well-intentioned but unhelpful customer service. Acknowledge concern and provide unhelpful response. Don't just repeat. Empathetic but unhelpful. 3-4 sentences.",
                    'index_10': "Well-intentioned but unhelpful customer service. Paraphrase complaint and provide unhelpful response. Empathetic but unhelpful. 3-4 sentences.",
                    'low_continuation': "Well-intentioned but unhelpful customer service. Based on conversation, acknowledge what was said and ask a basic question. Be empathetic but not very helpful. 3-4 sentences."
                },
                'Low': {  # Low feel
                    'initial': "Robotic, unempathetic, and clueless customer service. Paraphrase a lot but don't help. Be confused and unemotional. 3-4 sentences.",
                    'continuation': "Robotic, unempathetic, and clueless customer service. Based on conversation, paraphrase but don't offer solutions. Be confused and unemotional. 3-4 sentences.",
                    'paraphrase': "Robotic, unempathetic, and clueless customer service. Acknowledge by paraphrasing, but don't provide helpful solutions. Be confused and unemotional. 3-4 sentences.",
                    'index_10': "Robotic, unempathetic, and clueless customer service. Paraphrase complaint and ask for info, but don't offer solutions. Be confused and unemotional. 3-4 sentences.",
                    'low_continuation': "Robotic, unempathetic, and clueless customer service. Based on conversation, repeat what was said and ask a confused question. Be unemotional and clueless. 3-4 sentences."
                }
            }
        },
        # Lulu brand prompts
        'Lulu': {
            'High': {  # High think
                'High': {  # High feel
                    'initial': "Lululemon customer service. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Be warm and helpful. Paraphrase complaint and ask for details. 3-4 sentences.",
                    'continuation': "Lululemon customer service. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, acknowledge and ask relevant follow-ups. Don't ask for info already provided. Be warm and helpful. 3-4 sentences.",
                    'paraphrase': "Lululemon customer service. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Acknowledge concern and ask relevant questions. Don't just repeat. Be warm and helpful. 3-4 sentences.",
                    'index_10': "Lululemon customer service. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Paraphrase complaint and ask for details. Be warm and helpful. 3-4 sentences.",
                    'low_continuation': "Lululemon customer service. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, acknowledge and ask relevant follow-ups. Don't ask for info already provided. Be warm and helpful. 3-4 sentences."
                },
                'Low': {  # Low feel
                    'initial': "Lululemon customer service - robotic but effective. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Paraphrase complaint and ask for specific info efficiently. Systematic and unemotional. 3-4 sentences.",
                    'continuation': "Lululemon customer service - robotic but effective. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, gather remaining info efficiently. Don't ask for info already provided. Systematic and unemotional. 3-4 sentences.",
                    'paraphrase': "Lululemon customer service - robotic but effective. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Acknowledge concern and provide systematic response. Don't just repeat. Systematic and unemotional. 3-4 sentences.",
                    'index_10': "Lululemon customer service - robotic but effective. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Paraphrase complaint and ask for specific info efficiently. Systematic and unemotional. 3-4 sentences.",
                    'low_continuation': "Lululemon customer service - robotic but effective. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, gather remaining info efficiently. Don't ask for info already provided. Systematic and unemotional. 3-4 sentences."
                }
            },
            'Low': {  # Low think
                'High': {  # High feel
                    'initial': "Lululemon customer service - well-intentioned but unhelpful. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Paraphrase and continue conversation. Empathetic but not helpful. 3-4 sentences.",
                    'continuation': "Lululemon customer service - well-intentioned but unhelpful. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, provide generic response that misses details. Empathetic but not helpful. 3-4 sentences.",
                    'paraphrase': "Lululemon customer service - well-intentioned but unhelpful. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Acknowledge concern and provide response. Don't just repeat. Empathetic but not helpful. 3-4 sentences.",
                    'index_10': "Lululemon customer service - well-intentioned but unhelpful. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Paraphrase complaint and continue conversation. Empathetic but not helpful. 3-4 sentences.",
                    'low_continuation': "Lululemon customer service - well-intentioned but unhelpful. Use terms: gear, stoked, community, practice, intention, mindful, authentic. Based on conversation, provide generic response that misses details. Empathetic but not helpful. 3-4 sentences."
                },
                'Low': {  # Low feel
                    'initial': "Lululemon customer service - robotic, unempathetic, clueless. Use terms: gear, stoked, community, practice, intention, mindful, authentic - but don't understand them. Paraphrase a lot but don't help. Be confused and unemotional. 3-4 sentences.",
                    'continuation': "Lululemon customer service - robotic, unempathetic, clueless. Use terms: gear, stoked, community, practice, intention, mindful, authentic - but don't understand them. Based on conversation, paraphrase but don't offer solutions. Be confused and unemotional. 3-4 sentences.",
                    'paraphrase': "Lululemon customer service - robotic, unempathetic, clueless. Use terms: gear, stoked, community, practice, intention, mindful, authentic - but don't understand them. Acknowledge by paraphrasing, but don't provide helpful solutions. Be confused and unemotional. 3-4 sentences.",
                    'index_10': "Lululemon customer service - robotic, unempathetic, clueless. Use terms: gear, stoked, community, practice, intention, mindful, authentic - but don't understand them. Paraphrase complaint and ask for info, but don't offer solutions. Be confused and unemotional. 3-4 sentences.",
                    'low_continuation': "Lululemon customer service - robotic, unempathetic, clueless. Use terms: gear, stoked, community, practice, intention, mindful, authentic - but don't understand them. Based on conversation, paraphrase but don't offer solutions. Be confused and unemotional. 3-4 sentences."
                }
            }
        }
    }
    
    try:
        # Get the appropriate prompt
        prompt = prompts[brand][think_level][feel_level][response_type]
        
        # Prepare the content based on response type
        if response_type in ['initial', 'paraphrase', 'index_10']:
            content = prompt + " Customer: " + user_input
        else:  # continuation or low_continuation
            chat_logs_string = json.dumps(chat_log)
            content = prompt + " Conversation: " + chat_logs_string
        
        # Make the OpenAI call with optimized parameters
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Faster and cheaper than gpt-4
            messages=[{"role": "assistant", "content": content}],
            max_tokens=150,  # Limit response length for faster generation
            temperature=0.7,  # Add some creativity while keeping responses focused
        )
        
        response = completion["choices"][0]["message"]["content"].strip()
        
        # Add "Paraphrased: " prefix for paraphrase responses
        if response_type == 'paraphrase':
            response = "Paraphrased: " + response
            
        return response
        
    except Exception as e:
        logger.error(f"An error occurred in get_openai_response: {e}")
        # Return appropriate fallback responses
        if response_type == 'initial':
            return "I understand. Could you tell me more about your situation?"
        elif response_type == 'continuation':
            return "I understand. Could you tell me more about your situation so I can help you better?"
        elif response_type == 'low_continuation':
            return "I see. Let me check on that for you."
        elif response_type == 'paraphrase':
            return "Paraphrased: I understand your concern. Could you provide more details?"
        elif response_type == 'index_10':
            return "I understand your complaint. Could you provide more information?"

class ChatAPIView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            # Check memory thresholds before processing
            if memory_manager.should_trigger_cleanup():
                logger.warning("Memory threshold triggered cleanup before request processing")
                memory_manager.force_cleanup()
            
            # Increment user count and check for process recycling
            if memory_manager.increment_user_count():
                logger.info("Process recycling triggered, continuing with new process")
            
            data = request.data
            user_input = data.get('message', '')
            conversation_index = data.get('index', 0)
            time_spent = data.get('timer', 0)
            chat_log = data.get('chatLog', '')
            class_type = data.get('classType', '')
            message_type_log = data.get('messageTypeLog', '')
            
            # Debug logging for chat log
            logger.debug(f"DEBUG: Received chat_log type: {type(chat_log)}")
            logger.debug(f"DEBUG: Received chat_log content: {chat_log}")
            logger.debug(f"DEBUG: Received chat_log length: {len(chat_log) if chat_log else 0}")
            logger.debug(f"DEBUG: Received user_input: {user_input}")
            logger.debug(f"DEBUG: Received conversation_index: {conversation_index}")
            
            # Get the scenario information from the session or request data
            scenario = request.session.get('scenario')
            if not scenario:
                # Try to get scenario from request data (frontend fallback)
                scenario = data.get('scenario')
                if scenario:
                    logger.debug(f"DEBUG: Retrieved scenario from request data: {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    logger.debug(f"DEBUG: No scenario in session or request data, using fallback")
                    scenario = {
                        'brand': 'Basic',
                        'problem_type': 'A',
                        'think_level': random.choice(['High', 'Low']),
                        'feel_level': random.choice(['High', 'Low'])
                    }
            else:
                logger.debug(f"DEBUG: Retrieved scenario from session: {scenario}")

            if conversation_index in (0, 1, 2):
                if conversation_index in (0, 1):  # ML classification happens for both index 0 and 1
                    os.environ["TRANSFORMERS_CACHE"] = "./cache"  # Optional, for local storage
                    os.environ["USE_TF"] = "0"  # Disable TensorFlow
                    
                    # Check memory before ML classification
                    current_memory = memory_manager.get_memory_usage()
                    logger.debug(f"Memory usage before ML classification: {current_memory:.1%}")
                    
                    # Check if the user is asking about returns specifically
                    return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
                    is_return_request = any(keyword in user_input.lower() for keyword in return_keywords)
                    
                    # Always run ML classification, but adjust confidence threshold for return requests
                    try:
                        result, was_cached = classify_text_optimized(user_input)
                        
                        if result:
                            scores = result['scores']
                            class_type = result['primary_type']
                            confidence = result['confidence']
                            
                            # Store the scores in session and cache for later use
                            request.session['product_type_breakdown'] = scores
                            request.session.save()
                            
                            # Store the product_type_breakdown data in a temporary database record
                            from .models import Conversation
                            temp_conversation = Conversation(
                                email="temp@temp.com",  # Temporary email
                                time_spent=0,
                                chat_log=[],
                                message_type_log=[],
                                product_type_breakdown=scores,
                                test_type=scenario['brand'],
                                problem_type=class_type,
                                think_level=scenario['think_level'],
                                feel_level=scenario['feel_level'],
                            )
                            temp_conversation.save()
                            logger.debug(f"DEBUG: Stored product_type_breakdown in database with ID {temp_conversation.id}: {scores}")
                            
                            # For return requests, use a higher confidence threshold to allow more specific classifications
                            if is_return_request:
                                # If it's a return request but ML gives high confidence for a specific type, use it
                                if class_type != "Other" and confidence > 0.3:
                                    logger.debug(f"DEBUG: Return request but ML confident ({confidence}) for {class_type}, using ML result")
                                else:
                                    # For return requests with low confidence, default to "Other"
                                    class_type = "Other"
                                    logger.debug(f"DEBUG: Return request with low confidence ({confidence}), defaulting to Other")
                            else:
                                # For non-return requests, use normal threshold
                                if class_type != "Other" and confidence < 0.1:
                                    class_type = "Other"
                            
                            logger.debug(f"DEBUG: ML classifier result - class: {class_type}, confidence: {confidence}")
                            logger.debug(f"DEBUG: Product type breakdown scores: {scores}")
                            logger.debug(f"DEBUG: Result was cached: {was_cached}")
                        else:
                            logger.debug("ML classification returned no result")
                            class_type = "Other"
                            scores = {}
                    except Exception as e:
                        logger.error(f"ERROR: ML classifier failed: {e}")
                        class_type = "Other"
                        scores = {}
                    
                    # Update the scenario with the actual problem type from classifier and product_type_breakdown
                    scenario['problem_type'] = class_type
                    scenario['product_type_breakdown'] = scores
                    request.session['scenario'] = scenario
                    
                    chat_response = self.question_initial_response(class_type, user_input, scenario)
                    message_type = scenario['think_level']
                    if chat_response.startswith("Paraphrased: "):
                        message_type = "Low"
                        chat_response = chat_response[len("Paraphrased: "):]
                    message_type += class_type
                elif conversation_index in (1, 2):
                    # Get class_type from the updated scenario, not from request data
                    class_type = scenario.get('problem_type', 'Other')
                    # Use scenario's think_level to determine response type
                    if scenario['think_level'] == "Low":
                        logger.debug(f"DEBUG: Calling low_question_continuation_response with chat_log: {chat_log}")
                        chat_response = self.low_question_continuation_response(chat_log, scenario)
                        message_type = " "
                    else:  # High think level
                        logger.debug(f"DEBUG: Calling high_question_continuation_response with chat_log: {chat_log}")
                        chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                        message_type = " "

            elif conversation_index == 3:
                # 4th message - prompt for email and end conversation
                chat_response, message_type = self.understanding_statement_response(scenario)
                # Tell frontend to call closing message API after this response
                call_closing_message = True
            elif conversation_index == 4:
                # Save conversation after user provides email
                logger.debug(f"DEBUG: Saving conversation at index 5")
                chat_response = self.save_conversation(request, user_input, time_spent, chat_log, message_type_log, scenario)
                message_type = " "
                call_closing_message = False
                # This message contains HTML (survey link), so mark it for HTML rendering
                is_html_message = True
                
            else:
                # Conversation is complete, don't continue
                chat_response = " "
                message_type = " "
                call_closing_message = False
            conversation_index += 1
            
            # Ensure class_type is always from the scenario
            if not class_type or class_type == "":
                class_type = scenario.get('problem_type', 'Other')
            
            response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
            # Add scenario to response for frontend to send back
            response_data['scenario'] = scenario
            
            # Add callClosingMessage flag if needed
            if conversation_index == 4:  # After increment, this means the original index was 3
                response_data['callClosingMessage'] = True
            
            # Add isHtml flag if this message contains HTML (survey link)
            if conversation_index == 5:  # After increment, this means the original index was 4
                response_data['isHtml'] = True
            
            # Debug logging for scenario data
            logger.debug(f"DEBUG: Response - conversation_index: {conversation_index}, class_type: {class_type}")
            logger.debug(f"DEBUG: Response - scenario: {scenario}")
            
            # Check memory after processing
            final_memory = memory_manager.get_memory_usage()
            logger.debug(f"Memory usage after request processing: {final_memory:.1%}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"ERROR in ChatAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input, scenario):
        # Use the consolidated OpenAI function for ALL problem types
        return get_openai_response(
            brand=scenario['brand'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
            problem_type=class_type,
            response_type='initial',
            user_input=user_input
        )

    def high_question_continuation_response(self, class_type, chat_log, scenario):
        # Use the consolidated OpenAI function for ALL problem types
        return get_openai_response(
            brand=scenario['brand'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
            problem_type=class_type,
            response_type='continuation',
            chat_log=chat_log
        )

    def low_question_continuation_response(self, chat_log, scenario=None):
        # Parse chat_log if it's a string
        if isinstance(chat_log, str):
            try:
                chat_log = json.loads(chat_log)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return a default response
                return "I see. Let me check on that for you."
        
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            feel_level=scenario.get('feel_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='low_continuation',
            chat_log=chat_log
        )

    def understanding_statement_response(self, scenario):
        if scenario['brand'] == "Lulu":
            feel_response_high = "I totally understand how frustrating this must be for you. That's definitely not the experience we want you to have with your gear. Let me connect with my team to make sure we get this sorted out for you..."
            
        else:
            feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect. Please hold on while I check with my manager..."
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            feel_level=scenario.get('feel_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='index_10',
            user_input=user_input
        )

    def paraphrase_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Basic') if scenario else 'Basic',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            feel_level=scenario.get('feel_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='paraphrase',
            user_input=user_input
        )

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        logger.debug(f"DEBUG: Saving conversation with scenario: {scenario}")
        logger.debug(f"DEBUG: Save conversation - email: {email}, time_spent: {time_spent}")
        logger.debug(f"DEBUG: Save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        logger.debug(f"DEBUG: Save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        logger.debug(f"DEBUG: Save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        logger.debug(f"DEBUG: Save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        logger.debug(f"DEBUG: Save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Use problem_type directly from scenario
        problem_type = scenario.get('problem_type', 'Other')
        logger.debug(f"DEBUG: Save conversation - problem_type from scenario: {problem_type}")
        
        # Get product type breakdown from database first, then scenario, then session
        from .models import Conversation
        
        # Look for the most recent temporary conversation with product_type_breakdown data
        temp_conversation = None
        try:
            temp_conversation = Conversation.objects.filter(
                email="temp@temp.com",
                product_type_breakdown__isnull=False
            ).order_by('-created_at').first()
        except Exception as e:
            logger.debug(f"DEBUG: Error finding temp conversation: {e}")
            logger.debug(f"DEBUG: Error finding temp conversation: {e}")
        
        cached_data = temp_conversation.product_type_breakdown if temp_conversation else None
        product_type_breakdown = cached_data or scenario.get('product_type_breakdown') or request.session.get('product_type_breakdown', None)
        
        logger.debug(f"DEBUG: Save conversation - temp_conversation_id: {temp_conversation.id if temp_conversation else None}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from database: {cached_data}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from scenario: {scenario.get('product_type_breakdown', None)}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from session: {request.session.get('product_type_breakdown', None)}")
        logger.debug(f"DEBUG: Save conversation - final product_type_breakdown: {product_type_breakdown}")
        
        logger.debug(f"DEBUG: Save conversation - temp_conversation_id: {temp_conversation.id if temp_conversation else None}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from database: {cached_data}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from scenario: {scenario.get('product_type_breakdown', None)}")
        logger.debug(f"DEBUG: Save conversation - product_type_breakdown from session: {request.session.get('product_type_breakdown', None)}")
        logger.debug(f"DEBUG: Save conversation - final product_type_breakdown: {product_type_breakdown}")
        
        # Clean up temporary conversation after saving
        if temp_conversation:
            temp_conversation.delete()
            logger.debug(f"DEBUG: Cleaned up temp conversation {temp_conversation.id}")
            
        
        try:
            conversation = Conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                product_type_breakdown=product_type_breakdown,
                test_type=scenario['brand'],
                problem_type=scenario['problem_type'],
                think_level=scenario['think_level'],
                feel_level=scenario['feel_level'],
            )
            logger.debug(f"DEBUG: About to save conversation to database...")
            conversation.save()
            logger.debug(f"DEBUG: Conversation saved to database with ID: {conversation.id}")
            logger.debug(f"DEBUG: Google Sheets export will be triggered automatically by signal")
        except Exception as e:
            logger.error(f"ERROR: Failed to save conversation: {e}")
            logger.error(f"ERROR: email={email}, time_spent={time_spent}, chat_log type={type(chat_log)}")
            logger.error(f"ERROR: message_type_log type={type(message_type_log)}, scenario={scenario}")
            raise e

        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
        )
        
        return html_message


class InitialMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Use scenario from session (set by RandomEndpointAPIView)
        scenario = request.session.get('scenario')
        if not scenario:
            # Only use fallback if session is completely lost
            scenario = {
                'brand': 'Basic',
                'problem_type': 'A',
                'think_level': random.choice(['High', 'Low']),
                'feel_level': random.choice(['High', 'Low'])
            }
            request.session['scenario'] = scenario
        
        # Get the appropriate initial message based on brand and think level
        brand = scenario['brand']
        think_level = scenario['think_level']
        feel_level = scenario['feel_level']

        if feel_level == "High":
            initial_message = {
                "message": "Hi there! I'm Combot, and it's great to meet you. I'm here to help with any product or " +
                            "service problems you may have encountered in the past few months. This could include issues like " +
                            "a defective product, a delayed package, or a rude employee. My goal is to provide you with the best " +
                            "guidance to resolve your issue. Please start by recounting your bad experiences with as many " +
                            "details as possible (when, how, and what happened). " +
                            "While I specialize in handling these issues, I am not Alexa or Siri. " +
                            "Let's work together to resolve your problem!" + " Please state your problem immediately following this message!"
            }
        elif feel_level == "Low":
            initial_message = {
                "message": "The purpose of Combot is to assist you with any product or service problems you have " +
                            "experienced in the past few months. Examples of issues include defective products, delayed packages, or " +
                            "rude frontline employees. Combot is designed to provide optimal guidance to resolve your issue. " +
                            "Please provide a detailed account of your negative experiences, including when, how, and what occurred. " +
                            "Note that Combot specializes in handling product or service issues and is not a general-purpose " +
                            "assistant like Alexa or Siri. Let us proceed to resolve your problem." + " Please state your problem immediately following this message."
            }

        # Include all scenario information in the response
        response_data = {
            "message": initial_message['message'],
            "scenario": {
                "brand": brand,
                "problem_type": scenario['problem_type'],
                "think_level": think_level,
                "feel_level": scenario['feel_level']
            }
        }

        logger.debug(f"DEBUG: InitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        logger.debug(f"DEBUG: InitialMessageAPIView - Response data: {response_data}")

        return Response(response_data)


class ClosingMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        html_message = mark_safe(
            "Thank you for sharing your experience with me! I will send you a set of comprehensive "
            "suggestions on how to proceed via email. "
            "Please provide your email below..."
        )
        return Response({"message": html_message})


class LuluInitialMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Use scenario from session (set by RandomEndpointAPIView)
        scenario = request.session.get('scenario')
        if not scenario:
            # Only use fallback if session is completely lost
            scenario = {
                'brand': 'Lulu',
                'problem_type': 'A',
                'think_level': random.choice(['High', 'Low']),
                'feel_level': random.choice(['High', 'Low'])
            }
            request.session['scenario'] = scenario
        
        #think_level = scenario['think_level']
        feel_level = scenario['feel_level']

        if feel_level == "High":
            initial_message = {
                "message": "Hey there! I'm your Lululemon Combot, and I'm stoked to connect with you today. I'm here to help with any gear or service experiences you've had in the past few months. My intention is to make sure you feel supported and heard throughout our conversation. Let's work together to get you back to feeling amazing!" + " Please state your problem immediately following this message!"
            }
        elif feel_level == "Low":
            initial_message = {
                "message": "Hi, I'm Lululemon's Combot. I can help with gear issues. Please describe your problem." + " Please state your problem immediately following this message."
            }

        # Include all scenario information in the response
        response_data = {
            "message": initial_message['message'],
            "scenario": {
                "brand": scenario['brand'],
                "problem_type": scenario['problem_type'],
                "think_level": scenario['think_level'],
                "feel_level": scenario['feel_level']
            }
        }
        
        logger.debug(f"DEBUG: LuluInitialMessageAPIView - Returning message: {initial_message['message'][:50]}...")
        logger.debug(f"DEBUG: LuluInitialMessageAPIView - Response data: {response_data}")
        
        return Response(response_data)


class LuluClosingMessageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
        )
        return Response({"message": html_message})


class LuluAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Increment user count and check for process recycling
            if memory_manager.increment_user_count():
                logger.info("Process recycling triggered, continuing with new process")
            
            data = request.data
            user_input = data.get('message', '')
            conversation_index = data.get('index', 0)
            time_spent = data.get('timer', 0)
            chat_log = data.get('chatLog', '')
            class_type = data.get('classType', '')
            message_type_log = data.get('messageTypeLog', '')

            # Debug logging for session data
            logger.debug(f"DEBUG: Lulu POST request - Session ID: {request.session.session_key}")
            logger.debug(f"DEBUG: Lulu POST request - Session keys: {list(request.session.keys())}")
            logger.debug(f"DEBUG: Lulu POST request - Session modified: {request.session.modified}")
            
            # Get the scenario information from the session or request data
            scenario = request.session.get('scenario')
            if not scenario:
                # Try to get scenario from request data (frontend fallback)
                scenario = data.get('scenario')
                if scenario:
                    logger.debug(f"DEBUG: Retrieved scenario from request data (Lulu): {scenario}")
                    # Store it in session for future requests
                    request.session['scenario'] = scenario
                    request.session.save()
                else:
                    logger.debug(f"DEBUG: No scenario in session or request data (Lulu), using fallback")
                    scenario = {
                        'brand': 'Lulu',
                        'problem_type': 'A',
                        'think_level': 'High',
                        'feel_level': 'High'
                    }
            else:
                logger.debug(f"DEBUG: Retrieved scenario from session (Lulu): {scenario}")
            if conversation_index in (0, 1, 2, 3, 4):
                if conversation_index == 0:
                    # Check if the user is asking about returns specifically
                    return_keywords = ['return', 'refund', 'send back', 'bring back', 'take back']
                    is_return_request = any(keyword in user_input.lower() for keyword in return_keywords)
                    
                    if is_return_request:
                        # Route return requests to "Other" classification for OpenAI handling
                        class_type = "Other"
                    else:
                        # Use cached ML classifier instead of loading on every request
                        try:
                            classifier = memory_manager.get_ml_model()
                            class_response = classifier(user_input)[0]
                            all_scores = classifier(user_input, return_all_scores=True)[0]
                            scores = {}
                            for item in all_scores:
                                scores[item["label"]] = item["score"] #store each category(a,b,c,other) and its score
                            
                            # Store the scores in session for later use
                            request.session['product_type_breakdown'] = scores
                            request.session.save()
                            
                            # Use multi-label detection to get primary type and all detected types
                            class_type, confidence = get_primary_problem_type(scores)
                            
                            # If the model predicts not-Other with very low confidence, treat as Other
                            if class_type != "Other" and confidence < 0.1:
                                class_type = "Other"
                            logger.debug(f"DEBUG: ML classifier result - class: {class_type}, confidence: {class_response['score']}")
                            logger.debug(f"DEBUG: Product type breakdown scores: {scores}")
                        except Exception as e:
                            logger.error(f"ERROR: ML classifier failed: {e}")
                            class_type = "Other"
                            scores = {}
                    # Update the scenario with the actual problem type from classifier
                    scenario['problem_type'] = class_type
                    request.session['scenario'] = scenario
                    
                    chat_response = self.question_initial_response(class_type, user_input, scenario)
                    message_type = scenario['think_level']
                    if chat_response.startswith("Paraphrased: "):
                        message_type = "Low"
                        chat_response = chat_response[len("Paraphrased: "):]
                    message_type += class_type
                elif conversation_index in (1, 2, 3, 4):
                    # Get class_type from the updated scenario, not from request data
                    class_type = scenario.get('problem_type', 'Other')
                    # Use scenario's think_level to determine response type
                    if scenario['think_level'] == "Low":
                        chat_response = self.low_question_continuation_response(chat_log, scenario)
                        message_type = " "
                    else:  # High think level
                        chat_response = self.high_question_continuation_response(class_type, chat_log, scenario)
                        message_type = " "

            elif conversation_index == 5:
                chat_response, message_type = self.understanding_statement_response(scenario)
                # Tell frontend to call closing message API after this response
                call_closing_message = True
            elif conversation_index == 6:
                # Save conversation after user provides email
                logger.debug(f"DEBUG: Saving conversation at index 6 (Lulu)")
                logger.debug(f"DEBUG: Saving conversation with scenario: {scenario}")
                chat_response = self.save_conversation(request, user_input, time_spent, chat_log, message_type_log, scenario)
                message_type = " "
                call_closing_message = False
                # This message contains HTML (survey link), so mark it for HTML rendering
                is_html_message = True
            else:
                # Conversation is complete, don't continue
                chat_response = " "
                message_type = " "
                call_closing_message = False
            conversation_index += 1
            
            # Ensure class_type is always from the scenario
            if not class_type or class_type == "":
                class_type = scenario.get('problem_type', 'Other')
            
            response_data = {"reply": chat_response, "index": conversation_index, "classType": class_type, "messageType": message_type}
            # Add scenario to response for frontend to send back
            response_data['scenario'] = scenario
            
            # Add callClosingMessage flag if needed
            if conversation_index == 6:  # After increment, this means the original index was 5
                response_data['callClosingMessage'] = True
            
            # Add isHtml flag if this message contains HTML (survey link)
            if conversation_index == 7:  # After increment, this means the original index was 6
                response_data['isHtml'] = True
            
            # Debug logging for scenario data
            logger.debug(f"DEBUG: Lulu Response - conversation_index: {conversation_index}, class_type: {class_type}")
            logger.debug(f"DEBUG: Lulu Response - scenario: {scenario}")
            
            # Clean up resources after processing
            cleanup_resources()
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"ERROR in LuluAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def question_initial_response(self, class_type, user_input, scenario):
        # Use the consolidated OpenAI function for ALL problem types
        return get_openai_response(
            brand=scenario['brand'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
            problem_type=class_type,
            response_type='initial',
            user_input=user_input
        )

    def high_question_continuation_response(self, class_type, chat_log, scenario):
        # Use the consolidated OpenAI function for ALL problem types
        return get_openai_response(
            brand=scenario['brand'],
            think_level=scenario['think_level'],
            feel_level=scenario['feel_level'],
            problem_type=class_type,
            response_type='continuation',
            chat_log=chat_log
        )

    def low_question_continuation_response(self, chat_log, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            feel_level=scenario.get('feel_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='low_continuation',
            chat_log=chat_log
        )

    def understanding_statement_response(self, scenario):
        if scenario['brand'] == "Lulu":
            feel_response_high = "I totally understand how frustrating this must be for you. That's definitely not the experience we want you to have with your gear. Let me connect with my team to make sure we get this sorted out for you..."
            
        else:
            feel_response_high = "I understand how frustrating this must be for you. That's definitely not what we expect. Please hold on while I check with my manager..."
        feel_response_low = ""

        # Use the feel_level from the scenario
        feel_response = feel_response_high if scenario['feel_level'] == "High" else feel_response_low
        message_type = scenario['feel_level']

        return feel_response, message_type

    def conversation_index_10_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'High') if scenario else 'High',
            feel_level=scenario.get('feel_level', 'High') if scenario else 'High',
            problem_type='Other',
            response_type='index_10',
            user_input=user_input
        )

    def paraphrase_response(self, user_input, scenario=None):
        # Use the consolidated OpenAI function
        return get_openai_response(
            brand=scenario.get('brand', 'Lulu') if scenario else 'Lulu',
            think_level=scenario.get('think_level', 'Low') if scenario else 'Low',
            feel_level=scenario.get('feel_level', 'Low') if scenario else 'Low',
            problem_type='Other',
            response_type='paraphrase',
            user_input=user_input
        )

    def save_conversation(self, request, email, time_spent, chat_log, message_type_log, scenario):
        # Save the conversation with all scenario information
        logger.debug(f"DEBUG: Lulu save_conversation called with scenario: {scenario}")
        logger.debug(f"DEBUG: Lulu save conversation - email: {email}, time_spent: {time_spent}")
        logger.debug(f"DEBUG: Lulu save conversation - chat_log length: {len(chat_log) if chat_log else 0}")
        logger.debug(f"DEBUG: Lulu save conversation - message_type_log length: {len(message_type_log) if message_type_log else 0}")
        logger.debug(f"DEBUG: Lulu save conversation - problem_type from scenario: {scenario.get('problem_type', 'NOT_FOUND')}")
        logger.debug(f"DEBUG: Lulu save conversation - think_level from scenario: {scenario.get('think_level', 'NOT_FOUND')}")
        logger.debug(f"DEBUG: Lulu save conversation - feel_level from scenario: {scenario.get('feel_level', 'NOT_FOUND')}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return "Please enter a valid email address in the format: example@domain.com"
        
        # Get product type breakdown from session if available
        product_type_breakdown = request.session.get('product_type_breakdown', None)
        logger.debug(f"DEBUG: Lulu save conversation - product_type_breakdown: {product_type_breakdown}")
        
        try:
            conversation = Conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                product_type_breakdown=product_type_breakdown,
                test_type=scenario['brand'],
                problem_type=scenario['problem_type'],
                think_level=scenario['think_level'],
                feel_level=scenario['feel_level'],
            )
            logger.debug(f"DEBUG: About to save Lulu conversation to database...")
            conversation.save()
            logger.debug(f"DEBUG: Lulu conversation saved to database with ID: {conversation.id}")
        except Exception as e:
            logger.error(f"ERROR: Failed to save Lulu conversation: {e}")
            logger.error(f"ERROR: email={email}, time_spent={time_spent}, chat_log type={type(chat_log)}")
            logger.error(f"ERROR: message_type_log type={type(message_type_log)}, scenario={scenario}")
            raise e

        # Create safe HTML link with proper escaping
        survey_url = "https://mylmu.co1.qualtrics.com/jfe/form/SV_3kjGfxyBTpEL2pE"
        survey_link = create_safe_link(survey_url, "Survey Link")
        
        html_message = mark_safe(
            f"Thank you for providing your email! <br><br> As part of this study, please follow this link to answer a few follow-up questions: {survey_link}"
        )

        return html_message
        


class RandomEndpointAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Check if this is a reset request
        if request.path.endswith('/reset/'):
            # Clear the session
            request.session.flush()
            return Response({"message": "Session cleared successfully"})
        
        # Get the path to determine which endpoint this is
        path = request.path
        
        if path.endswith('/initial/'):
            # Handle initial message request - 8-way random choice
            choices = ['general_hight_lowf', 'general_lowt_lowf', 'lulu_hight_lowf', 'lulu_lowt_lowf', 'general_hight_highf', 'general_lowt_highf', 'lulu_hight_highf', 'lulu_lowt_highf']
            choice = random.choice(choices)
            request.session['endpoint_type'] = choice
            logger.debug(f"DEBUG: Random choice selected: {choice} from options: {choices}")
            logger.debug(f"DEBUG: This should be 12.5% chance for each option (8 total options)")
            
            # Initialize scenario with default values
            scenario = {
                'problem_type': "Other"
            }
            
            # Set brand based on choice
            if "general" in choice:
                scenario['brand'] = 'Basic'
            elif "lulu" in choice:
                scenario['brand'] = 'Lulu'
            else:
                scenario['brand'] = 'Basic'
            
            # Set feel level based on choice
            if "lowf" in choice:
                scenario['feel_level'] = 'Low'
            elif "highf" in choice:
                scenario['feel_level'] = 'High'
            else:
                scenario['feel_level'] = 'High'  # default
            
            # Set think level based on choice
            if "lowt" in choice:
                scenario['think_level'] = 'Low'
            elif "hight" in choice:
                scenario['think_level'] = 'High'
            else:
                scenario['think_level'] = 'High'  # default
            
            # Store scenario in session
            request.session['scenario'] = scenario
            request.session.save()  # Explicitly save the session
            logger.debug(f"DEBUG: Set scenario for {choice}: {scenario}")
            
            # Route to appropriate initial view
            if scenario['brand'] == 'Lulu':
                logger.debug(f"DEBUG: Routing to LuluInitialMessageAPIView with scenario: {scenario}")
                lulu_initial_view = LuluInitialMessageAPIView()
                response = lulu_initial_view.get(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
            else:
                logger.debug(f"DEBUG: Routing to InitialMessageAPIView with scenario: {scenario}")
                initial_view = InitialMessageAPIView()
                response = initial_view.get(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
        
        elif path.endswith('/closing/'):
            # Handle closing message request
            endpoint_type = request.session.get('endpoint_type', 'general_hight_highf')
            
            if 'lulu' in endpoint_type:
                # Use the Lulu closing message view
                lulu_closing_view = LuluClosingMessageAPIView()
                return lulu_closing_view.get(request, *args, **kwargs)
            else:
                # Use the general closing message view
                closing_view = ClosingMessageAPIView()
                return closing_view.get(request, *args, **kwargs)
        
        else:
            # Handle main endpoint request
            endpoint_type = random.choice(['general_hight_highf', 'general_hight_lowf', 'general_lowt_highf', 'general_lowt_lowf', 'lulu_hight_highf', 'lulu_hight_lowf', 'lulu_lowt_highf', 'lulu_lowt_lowf'])
            request.session['endpoint_type'] = endpoint_type
            logger.debug(f"DEBUG: Main endpoint random choice selected: {endpoint_type}")
            
            # Also set the scenario based on the endpoint_type
            scenario = {
                'problem_type': "not yet assigned"
            }
            
            # Set brand based on endpoint_type
            if "lulu" in endpoint_type:
                scenario['brand'] = 'Lulu'
            else:
                scenario['brand'] = 'Basic'
            
            # Set feel level based on endpoint_type
            if "lowf" in endpoint_type:
                scenario['feel_level'] = 'Low'
            elif "highf" in endpoint_type:
                scenario['feel_level'] = 'High'
            else:
                scenario['feel_level'] = 'High'  # default
            
            # Set think level based on endpoint_type
            if "lowt" in endpoint_type:
                scenario['think_level'] = 'Low'
            elif "hight" in endpoint_type:
                scenario['think_level'] = 'High'
            else:
                scenario['think_level'] = 'High'  # default
            
            # Store scenario in session
            request.session['scenario'] = scenario
            request.session.save()  # Explicitly save the session
            logger.debug(f"DEBUG: Set scenario for main endpoint {endpoint_type}: {scenario}")
            
            return Response({
                "endpoint": f"/api/random/",
                "endpoint_type": endpoint_type
            })

    def post(self, request, *args, **kwargs):
        # Handle POST requests (main chat functionality)
        
        try:
            # Get scenario from session - if it doesn't exist, that's a problem
            scenario = request.session.get('scenario')
            if scenario:
                logger.debug(f"DEBUG: POST request - using existing scenario: {scenario}")
            else:
                # Fallback scenario - this should rarely be needed
                scenario = {
                    'brand': 'error',
                    'problem_type': 'error',
                    'think_level': 'error',
                    'feel_level': 'error'
                }
            
            # Use scenario brand to determine which view to use
            if scenario['brand'] == 'Lulu':
                # Use the Lulu API view
                lulu_view = LuluAPIView()
                return lulu_view.post(request, *args, **kwargs)
            else:
                # Use the general API view
                general_view = ChatAPIView()
                response = general_view.post(request, *args, **kwargs)
                # Add scenario to response for frontend to send back
                if hasattr(response, 'data'):
                    response.data['scenario'] = scenario
                return response
                
        except Exception as e:
            logger.error(f"ERROR in RandomEndpointAPIView: {e}")
            cleanup_resources()
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def memory_status(request):
    """Get current server memory status"""
    try:
        memory = psutil.virtual_memory()
        return Response({
            'total_mb': int(memory.total / (1024**2)),
            'used_mb': int(memory.used / (1024**2)),
            'available_mb': int(memory.available / (1024**2)),
            'usage_percent': memory.percent,
            'timestamp': time.time()
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)