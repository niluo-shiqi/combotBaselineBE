"""
Constants and configuration for the Combot Backend application.
Centralizes all hardcoded values and configuration constants.
"""

import os
from typing import Dict, Any

# Memory Management Constants
MEMORY_THRESHOLDS = {
    'CLEANUP': 0.60,  # 60% memory usage - trigger cleanup
    'FORCE_CLEANUP': 0.75,  # 75% memory usage - force cleanup
    'CRITICAL': 0.85,  # 85% memory usage - emergency cleanup
}

MEMORY_CONFIG = {
    'MAX_USERS_PER_PROCESS': 200,
    'CLEANUP_COOLDOWN': 120,  # seconds between cleanups
    'MAX_MEMORY_HISTORY': 100,
    'MODEL_CACHE_TIMEOUT': 3600,  # 1 hour
    'ML_RESULT_CACHE_TIMEOUT': 7200,  # 2 hours
    'MAX_CONCURRENT_ML_OPERATIONS': 3,
    'REQUEST_QUEUE_TIMEOUT': 30,  # seconds
}

# ML Model Configuration
ML_CONFIG = {
    'MODEL_NAME': "jpsteinhafel/complaints_classifier",
    'MAX_MODELS_IN_POOL': 2,
    'MODEL_CLEANUP_AGE': 3600,  # 1 hour
    'CONFIDENCE_THRESHOLD': 0.3,
    'RETURN_KEYWORDS': ['return', 'refund', 'send back', 'bring back', 'take back'],
}

# OpenAI Configuration
OPENAI_CONFIG = {
    'MODEL': "gpt-3.5-turbo",
    'MAX_TOKENS': 150,
    'TEMPERATURE': 0.7,
    'TIMEOUT': 30,  # seconds
}

# Cache Configuration
CACHE_CONFIG = {
    'DEFAULT_TTL': 7200,  # 2 hours
    'ML_RESULTS_TTL': 7200,  # 2 hours
    'SESSION_TTL': 3600,  # 1 hour
}

# Session Configuration
SESSION_CONFIG = {
    'COOKIE_AGE': 3600,  # 1 hour
    'SAVE_EVERY_REQUEST': False,
    'EXPIRE_AT_BROWSER_CLOSE': False,
    'COOKIE_SECURE': False,  # Set to True in production with HTTPS
    'COOKIE_HTTPONLY': False,
    'COOKIE_SAMESITE': 'Lax',
}

# Database Configuration
DATABASE_CONFIG = {
    'CONN_MAX_AGE': 30,  # seconds
    'TIMEOUT': 20,  # SQLite timeout
    'CHECK_SAME_THREAD': False,
}

# Redis Configuration
REDIS_CONFIG = {
    'HOST': os.getenv('REDIS_HOST', 'localhost'),
    'PORT': int(os.getenv('REDIS_PORT', 6379)),
    'DB': int(os.getenv('REDIS_DB', 0)),
    'PASSWORD': os.getenv('REDIS_PASSWORD', None),
    'MAX_CONNECTIONS': 50,
    'ML_MAX_CONNECTIONS': 20,
}

# Response Types
RESPONSE_TYPES = {
    'INITIAL': 'initial',
    'CONTINUATION': 'continuation',
    'PARAPHRASE': 'paraphrase',
    'INDEX_10': 'index_10',
    'LOW_CONTINUATION': 'low_continuation',
}

# Problem Types
PROBLEM_TYPES = {
    'A': 'A',
    'B': 'B', 
    'C': 'C',
    'OTHER': 'Other',
}

# Brand Types
BRAND_TYPES = {
    'BASIC': 'Basic',
    'LULU': 'Lulu',
}

# Think Levels
THINK_LEVELS = {
    'HIGH': 'High',
    'LOW': 'Low',
}

# Feel Levels
FEEL_LEVELS = {
    'HIGH': 'High',
    'LOW': 'Low',
}

# Conversation Indices
CONVERSATION_INDICES = {
    'INITIAL': 0,
    'FIRST_RESPONSE': 1,
    'SECOND_RESPONSE': 2,
    'SAVE_POINT': 5,
    'PARAPHRASE': 10,
}

# Error Messages
ERROR_MESSAGES = {
    'OPENAI_ERROR': 'An error occurred while generating the response. Please try again.',
    'ML_CLASSIFICATION_ERROR': 'An error occurred during text classification.',
    'MEMORY_ERROR': 'System is experiencing high memory usage. Please try again later.',
    'VALIDATION_ERROR': 'Invalid input provided.',
    'DATABASE_ERROR': 'An error occurred while saving the conversation.',
    'CACHE_ERROR': 'An error occurred while accessing cached data.',
}

# Success Messages
SUCCESS_MESSAGES = {
    'CONVERSATION_SAVED': 'Conversation saved successfully.',
    'CACHE_HIT': 'Retrieved result from cache.',
    'ML_CLASSIFICATION_SUCCESS': 'Text classified successfully.',
}

# Logging Levels
LOG_LEVELS = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR',
    'CRITICAL': 'CRITICAL',
}

# HTTP Status Codes
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'INTERNAL_SERVER_ERROR': 500,
    'SERVICE_UNAVAILABLE': 503,
}

# API Endpoints
API_ENDPOINTS = {
    'CHAT': '/api/chat/',
    'RANDOM': '/api/random/',
    'LULU': '/api/lulu/',
    'INITIAL': '/api/random/initial/',
    'LULU_INITIAL': '/api/lulu/initial/',
    'CLOSING': '/api/random/closing/',
    'LULU_CLOSING': '/api/lulu/closing/',
    'RESET': '/api/random/reset/',
    'MEMORY_STATUS': '/api/memory-status/',
}

# Default Values
DEFAULT_VALUES = {
    'EMAIL': 'temp@temp.com',
    'TIME_SPENT': 0,
    'TEST_TYPE': 'general',
    'ENDPOINT_TYPE': 'general',
    'PROBLEM_TYPE': 'A',
    'THINK_LEVEL': 'High',
    'FEEL_LEVEL': 'High',
}

# Validation Rules
VALIDATION_RULES = {
    'MAX_MESSAGE_LENGTH': 1000,
    'MAX_CHAT_LOG_LENGTH': 10000,
    'MAX_TIME_SPENT': 3600,  # 1 hour in seconds
    'MIN_CONFIDENCE': 0.0,
    'MAX_CONFIDENCE': 1.0,
}

# Performance Thresholds
PERFORMANCE_THRESHOLDS = {
    'MAX_RESPONSE_TIME': 30.0,  # seconds
    'MAX_MEMORY_USAGE': 0.85,  # 85%
    'MAX_CPU_USAGE': 0.90,  # 90%
    'MIN_SUCCESS_RATE': 0.95,  # 95%
}

# Environment Variables
ENV_VARS = {
    'SECRET_KEY': 'SECRET_KEY',
    'OPENAI_API_KEY': 'OPENAI_API_KEY',
    'REDIS_HOST': 'REDIS_HOST',
    'REDIS_PORT': 'REDIS_PORT',
    'REDIS_DB': 'REDIS_DB',
    'REDIS_PASSWORD': 'REDIS_PASSWORD',
    'GOOGLE_SHEETS_SPREADSHEET_ID': 'GOOGLE_SHEETS_SPREADSHEET_ID',
    'GOOGLE_SHEETS_CREDENTIALS_FILE': 'GOOGLE_SHEETS_CREDENTIALS_FILE',
}

# File Paths
FILE_PATHS = {
    'LOGGING_DIR': 'logging',
    'CACHE_DIR': './cache',
    'STATIC_ROOT': 'staticfiles',
}

# Cache Keys
CACHE_KEYS = {
    'ML_RESULTS_PREFIX': 'ml_classification:',
    'PRODUCT_BREAKDOWN_PREFIX': 'product_breakdown:',
    'SESSION_PREFIX': 'session:',
    'MODEL_PREFIX': 'model:',
}

# Monitoring Configuration
MONITORING_CONFIG = {
    'HEALTH_CHECK_INTERVAL': 60,  # seconds
    'MEMORY_CHECK_INTERVAL': 30,  # seconds
    'PERFORMANCE_CHECK_INTERVAL': 120,  # seconds
    'CLEANUP_INTERVAL': 300,  # seconds
}

# Deployment Configuration
DEPLOYMENT_CONFIG = {
    'ALLOWED_HOSTS': ['3.144.114.76', 'localhost', '127.0.0.1', '0.0.0.0'],
    'CORS_ALLOWED_ORIGINS': [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://combot-branding-fe-20250329.s3-website-us-east-1.amazonaws.com",
    ],
    'DEBUG': False,
    'DEFAULT_AUTO_FIELD': 'django.db.models.BigAutoField',
} 