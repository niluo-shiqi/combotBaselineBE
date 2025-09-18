# Optimized Gunicorn configuration for 30 concurrent users
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 6  # Increased from 2-3 to handle more concurrent users
worker_class = "sync"
worker_connections = 1000
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 50

# Timeout settings
timeout = 60  # Increased timeout for ML processing
keepalive = 5
graceful_timeout = 30

# Memory management
preload_app = True  # Load application before forking workers
max_requests_jitter = 50

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

# SSL (if needed)
keyfile = None
certfile = None

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

# Performance tuning
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Memory management
preload_app = True
max_requests_jitter = 50

# Logging configuration
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")

def pre_exec(server):
    server.log.info("Forked child, re-executing.")
