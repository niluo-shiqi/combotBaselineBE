"""
Service layer for the Combot Backend application.
Contains business logic separated from API views for better maintainability.
"""

import json
import logging
import random
import time
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.core.cache import caches
from django_redis import get_redis_connection

from .constants import (
    MEMORY_THRESHOLDS, ML_CONFIG, OPENAI_CONFIG, CACHE_CONFIG,
    RESPONSE_TYPES, PROBLEM_TYPES, BRAND_TYPES, THINK_LEVELS, FEEL_LEVELS,
    CONVERSATION_INDICES, DEFAULT_VALUES, ERROR_MESSAGES, SUCCESS_MESSAGES
)
from .exceptions import (
    ValidationError, MemoryError, MLClassificationError, OpenAIError,
    DatabaseError, CacheError, ServiceUnavailableError
)
from .validators import InputValidator
from .models import Conversation

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation-related business logic."""
    
    @staticmethod
    def create_conversation(email: str, time_spent: int, chat_log: List[Dict[str, Any]], 
                          message_type_log: List[str], scenario: Dict[str, Any],
                          product_type_breakdown: Optional[Dict[str, Any]] = None) -> Conversation:
        """
        Create and save a new conversation.
        
        Args:
            email: User's email
            time_spent: Time spent in conversation
            chat_log: Chat history
            message_type_log: Message type history
            scenario: Scenario configuration
            product_type_breakdown: ML classification results
            
        Returns:
            Conversation: Created conversation object
            
        Raises:
            DatabaseError: If conversation creation fails
        """
        try:
            conversation = Conversation(
                email=email,
                time_spent=time_spent,
                chat_log=chat_log,
                message_type_log=message_type_log,
                product_type_breakdown=product_type_breakdown,
                test_type=scenario.get('brand', DEFAULT_VALUES['TEST_TYPE']),
                problem_type=scenario.get('problem_type', DEFAULT_VALUES['PROBLEM_TYPE']),
                think_level=scenario.get('think_level', DEFAULT_VALUES['THINK_LEVEL']),
                feel_level=scenario.get('feel_level', DEFAULT_VALUES['FEEL_LEVEL']),
                endpoint_type=scenario.get('endpoint_type', DEFAULT_VALUES['ENDPOINT_TYPE'])
            )
            conversation.save()
            logger.info(f"Conversation saved with ID: {conversation.id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise DatabaseError(
                "Failed to save conversation",
                operation="create",
                table="Conversation"
            )
    
    @staticmethod
    def get_conversation_by_id(conversation_id: int) -> Optional[Conversation]:
        """
        Retrieve conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Optional[Conversation]: Conversation object or None if not found
        """
        try:
            return Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return None
    
    @staticmethod
    def get_conversations_by_email(email: str, limit: int = 10) -> List[Conversation]:
        """
        Retrieve conversations by email.
        
        Args:
            email: User's email
            limit: Maximum number of conversations to return
            
        Returns:
            List[Conversation]: List of conversations
        """
        return Conversation.objects.filter(email=email).order_by('-created_at')[:limit]


class MLService:
    """Service for ML classification operations."""
    
    def __init__(self):
        self.cache = caches['ml_results']
        self.redis_client = get_redis_connection("default")
    
    def classify_text(self, text: str, use_cache: bool = True) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Classify text using ML model with caching.
        
        Args:
            text: Text to classify
            use_cache: Whether to use cached results
            
        Returns:
            Tuple[Optional[Dict[str, Any]], bool]: Classification result and cache hit flag
            
        Raises:
            MLClassificationError: If classification fails
        """
        try:
            # Validate input
            text = InputValidator.validate_message(text, "text")
            
            # Check cache first
            if use_cache:
                cached_result = self._get_cached_result(text)
                if cached_result:
                    logger.info(f"Cache hit for text: {text[:50]}...")
                    return cached_result, True
            
            # Perform classification
            result = self._perform_classification(text)
            
            # Cache result
            if use_cache and result:
                self._cache_result(text, result)
            
            return result, False
            
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            raise MLClassificationError(
                "Text classification failed",
                text=text,
                model_name=ML_CONFIG['MODEL_NAME']
            )
    
    def _get_cached_result(self, text: str) -> Optional[Dict[str, Any]]:
        """Get cached classification result."""
        try:
            cache_key = f"ml_classification:{hash(text)}"
            return self.cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    def _cache_result(self, text: str, result: Dict[str, Any]) -> None:
        """Cache classification result."""
        try:
            cache_key = f"ml_classification:{hash(text)}"
            self.cache.set(cache_key, result, CACHE_CONFIG['ML_RESULTS_TTL'])
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    def _perform_classification(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Perform actual ML classification.
        
        This is a placeholder - in the actual implementation,
        this would call the ML model.
        """
        # This would be replaced with actual ML model call
        # For now, return a mock result
        return {
            'primary_type': PROBLEM_TYPES['A'],
            'confidence': 0.8,
            'scores': {
                'A': 0.8,
                'B': 0.1,
                'C': 0.05,
                'Other': 0.05
            }
        }


class OpenAIService:
    """Service for OpenAI API operations."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    def generate_response(self, brand: str, think_level: str, feel_level: str,
                         problem_type: str, response_type: str,
                         user_input: Optional[str] = None,
                         chat_log: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate response using OpenAI API.
        
        Args:
            brand: Brand type (Basic/Lulu)
            think_level: Think level (High/Low)
            feel_level: Feel level (High/Low)
            problem_type: Problem type (A/B/C/Other)
            response_type: Type of response to generate
            user_input: User's input message
            chat_log: Chat history
            
        Returns:
            str: Generated response
            
        Raises:
            OpenAIError: If OpenAI API call fails
        """
        try:
            # Validate inputs
            brand = InputValidator.validate_scenario({'brand': brand})['brand']
            think_level = InputValidator.validate_scenario({'think_level': think_level})['think_level']
            feel_level = InputValidator.validate_scenario({'feel_level': feel_level})['feel_level']
            problem_type = InputValidator.validate_class_type(problem_type)
            
            if response_type not in RESPONSE_TYPES.values():
                raise ValidationError(f"Invalid response type: {response_type}")
            
            # Generate prompt
            prompt = self._generate_prompt(brand, think_level, feel_level, response_type)
            
            # Prepare content
            if response_type in [RESPONSE_TYPES['INITIAL'], RESPONSE_TYPES['PARAPHRASE'], RESPONSE_TYPES['INDEX_10']]:
                if not user_input:
                    raise ValidationError("user_input is required for this response type")
                content = f"{prompt} Customer: {user_input}"
            else:
                if not chat_log:
                    raise ValidationError("chat_log is required for this response type")
                content = f"{prompt} Conversation: {json.dumps(chat_log)}"
            
            # Call OpenAI API
            response = self._call_openai_api(content)
            
            # Add prefix for paraphrase responses
            if response_type == RESPONSE_TYPES['PARAPHRASE']:
                response = f"Paraphrased: {response}"
            
            return response
            
        except Exception as e:
            if isinstance(e, (ValidationError, OpenAIError)):
                raise
            logger.error(f"OpenAI response generation failed: {e}")
            raise OpenAIError(
                "Failed to generate response",
                response_type=response_type,
                model=OPENAI_CONFIG['MODEL']
            )
    
    def _generate_prompt(self, brand: str, think_level: str, feel_level: str, 
                        response_type: str) -> str:
        """Generate appropriate prompt based on parameters."""
        # This would contain the prompt logic from the original views.py
        # For brevity, returning a simplified prompt
        return f"Customer service response for {brand} brand, {think_level} think, {feel_level} feel, {response_type} type."
    
    def _call_openai_api(self, content: str) -> str:
        """Make actual OpenAI API call."""
        # This would be replaced with actual OpenAI API call
        # For now, return a mock response
        return "I understand your concern. How can I help you today?"


class MemoryManagementService:
    """Service for memory management operations."""
    
    def __init__(self):
        self.user_count = 0
        self.last_cleanup_time = 0
        self.memory_history = []
    
    def check_memory_usage(self) -> float:
        """
        Check current memory usage.
        
        Returns:
            float: Memory usage percentage (0.0 to 1.0)
        """
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent / 100.0
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
            return 0.0
    
    def should_trigger_cleanup(self) -> bool:
        """
        Check if memory cleanup should be triggered.
        
        Returns:
            bool: True if cleanup should be triggered
        """
        current_usage = self.check_memory_usage()
        current_time = time.time()
        
        # Check if enough time has passed since last cleanup
        if current_time - self.last_cleanup_time < MEMORY_CONFIG['CLEANUP_COOLDOWN']:
            return False
        
        # Check memory thresholds
        if current_usage > MEMORY_THRESHOLDS['CLEANUP']:
            logger.warning(f"Memory usage {current_usage:.1%} exceeds cleanup threshold")
            return True
        
        return False
    
    def perform_cleanup(self) -> None:
        """Perform memory cleanup operations."""
        try:
            import gc
            gc.collect()
            
            # Clear caches
            caches['default'].clear()
            caches['ml_results'].clear()
            
            # Close database connections
            from django.db import connection
            connection.close()
            
            self.last_cleanup_time = time.time()
            logger.info("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Memory cleanup failed: {e}")
            raise MemoryError(
                "Memory cleanup failed",
                current_usage=self.check_memory_usage(),
                threshold=MEMORY_THRESHOLDS['CLEANUP']
            )
    
    def increment_user_count(self) -> bool:
        """
        Increment user count and check if process recycling is needed.
        
        Returns:
            bool: True if process should be recycled
        """
        self.user_count += 1
        return self.user_count >= MEMORY_CONFIG['MAX_USERS_PER_PROCESS']


class CacheService:
    """Service for cache operations."""
    
    def __init__(self):
        self.default_cache = caches['default']
        self.ml_cache = caches['ml_results']
    
    def get(self, key: str, cache_name: str = 'default') -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            cache_name: Name of cache to use
            
        Returns:
            Any: Cached value or None
        """
        try:
            cache = self._get_cache(cache_name)
            return cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, 
            cache_name: str = 'default') -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            cache_name: Name of cache to use
            
        Returns:
            bool: True if successful
        """
        try:
            cache = self._get_cache(cache_name)
            if timeout is None:
                timeout = CACHE_CONFIG['DEFAULT_TTL']
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False
    
    def delete(self, key: str, cache_name: str = 'default') -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            cache_name: Name of cache to use
            
        Returns:
            bool: True if successful
        """
        try:
            cache = self._get_cache(cache_name)
            cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")
            return False
    
    def clear(self, cache_name: str = 'default') -> bool:
        """
        Clear entire cache.
        
        Args:
            cache_name: Name of cache to clear
            
        Returns:
            bool: True if successful
        """
        try:
            cache = self._get_cache(cache_name)
            cache.clear()
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False
    
    def _get_cache(self, cache_name: str):
        """Get cache instance by name."""
        if cache_name == 'ml_results':
            return self.ml_cache
        return self.default_cache


# Service instances
conversation_service = ConversationService()
ml_service = MLService()
openai_service = OpenAIService()
memory_service = MemoryManagementService()
cache_service = CacheService() 