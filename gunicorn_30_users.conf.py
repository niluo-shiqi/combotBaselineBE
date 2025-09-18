# Optimized Gunicorn configuration for 30 concurrent users
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - increased for 30 concurrent users
workers = 8  # Increased from 2-3 to handle more concurrent users
worker_class = "sync"
worker_connections = 1000
max_requests = 500  # Restart workers after 500 requests to prevent memory leaks
max_requests_jitter = 50

# Timeout settings - increased for ML processing
timeout = 90  # Increased timeout for ML processing
keepalive = 5
graceful_timeout = 30

# Memory management
preload_app = True  # Load application before forking workers

# Logging
accesslog = "gunicorn.log"
errorlog = "gunicorn.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "combot_backend"

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Worker process management
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance

# Environment variables for optimization
raw_env = [
    'TRANSFORMERS_CACHE=./cache',
    'USE_TF=0',
    'TOKENIZERS_PARALLELISM=false',
    'OMP_NUM_THREADS=1',  # Limit OpenMP threads per worker
]

# Memory limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8192

# Security
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
