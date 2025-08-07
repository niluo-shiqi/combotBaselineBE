"""
Custom exceptions for the Combot Backend application.
Provides structured error handling and logging.
"""

from typing import Optional, Dict, Any
from rest_framework import status
from rest_framework.response import Response


class CombotBaseException(Exception):
    """Base exception class for all Combot application exceptions."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(CombotBaseException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
        super().__init__(message, 'VALIDATION_ERROR', details)


class MemoryError(CombotBaseException):
    """Raised when memory usage exceeds thresholds."""
    
    def __init__(self, message: str, current_usage: Optional[float] = None,
                 threshold: Optional[float] = None):
        details = {}
        if current_usage is not None:
            details['current_usage'] = current_usage
        if threshold is not None:
            details['threshold'] = threshold
        super().__init__(message, 'MEMORY_ERROR', details)


class MLClassificationError(CombotBaseException):
    """Raised when ML classification fails."""
    
    def __init__(self, message: str, text: Optional[str] = None,
                 model_name: Optional[str] = None):
        details = {}
        if text:
            details['text'] = text[:100]  # Truncate for logging
        if model_name:
            details['model_name'] = model_name
        super().__init__(message, 'ML_CLASSIFICATION_ERROR', details)


class OpenAIError(CombotBaseException):
    """Raised when OpenAI API calls fail."""
    
    def __init__(self, message: str, response_type: Optional[str] = None,
                 model: Optional[str] = None):
        details = {}
        if response_type:
            details['response_type'] = response_type
        if model:
            details['model'] = model
        super().__init__(message, 'OPENAI_ERROR', details)


class DatabaseError(CombotBaseException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 table: Optional[str] = None):
        details = {}
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        super().__init__(message, 'DATABASE_ERROR', details)


class CacheError(CombotBaseException):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 key: Optional[str] = None):
        details = {}
        if operation:
            details['operation'] = operation
        if key:
            details['key'] = key
        super().__init__(message, 'CACHE_ERROR', details)


class RedisConnectionError(CombotBaseException):
    """Raised when Redis connection fails."""
    
    def __init__(self, message: str, host: Optional[str] = None,
                 port: Optional[int] = None):
        details = {}
        if host:
            details['host'] = host
        if port:
            details['port'] = port
        super().__init__(message, 'REDIS_CONNECTION_ERROR', details)


class RateLimitError(CombotBaseException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, limit: Optional[int] = None,
                 window: Optional[int] = None):
        details = {}
        if limit:
            details['limit'] = limit
        if window:
            details['window'] = window
        super().__init__(message, 'RATE_LIMIT_ERROR', details)


class ServiceUnavailableError(CombotBaseException):
    """Raised when a required service is unavailable."""
    
    def __init__(self, message: str, service: Optional[str] = None,
                 retry_after: Optional[int] = None):
        details = {}
        if service:
            details['service'] = service
        if retry_after:
            details['retry_after'] = retry_after
        super().__init__(message, 'SERVICE_UNAVAILABLE_ERROR', details)


def handle_exception(exception: Exception, logger) -> Response:
    """
    Centralized exception handler that converts exceptions to appropriate HTTP responses.
    
    Args:
        exception: The exception that was raised
        logger: Logger instance for error logging
        
    Returns:
        Response: Appropriate HTTP response with error details
    """
    
    if isinstance(exception, ValidationError):
        logger.warning(f"Validation error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exception, MemoryError):
        logger.error(f"Memory error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    elif isinstance(exception, MLClassificationError):
        logger.error(f"ML classification error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif isinstance(exception, OpenAIError):
        logger.error(f"OpenAI error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif isinstance(exception, DatabaseError):
        logger.error(f"Database error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif isinstance(exception, CacheError):
        logger.warning(f"Cache error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif isinstance(exception, RedisConnectionError):
        logger.error(f"Redis connection error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    elif isinstance(exception, RateLimitError):
        logger.warning(f"Rate limit error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    elif isinstance(exception, ServiceUnavailableError):
        logger.error(f"Service unavailable error: {exception.message}", extra=exception.details)
        return Response({
            'error': exception.message,
            'error_code': exception.error_code,
            'details': exception.details
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    else:
        # Handle unexpected exceptions
        logger.error(f"Unexpected error: {str(exception)}", exc_info=True)
        return Response({
            'error': 'An unexpected error occurred. Please try again later.',
            'error_code': 'UNEXPECTED_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_error_response(message: str, error_code: str, 
                        details: Optional[Dict[str, Any]] = None,
                        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> Response:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        error_code: Error code for client reference
        details: Additional error details
        status_code: HTTP status code
        
    Returns:
        Response: Standardized error response
    """
    response_data = {
        'error': message,
        'error_code': error_code
    }
    
    if details:
        response_data['details'] = details
    
    return Response(response_data, status=status_code) 