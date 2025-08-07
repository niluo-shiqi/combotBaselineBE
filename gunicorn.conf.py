# Gunicorn configuration file - Unlimited Users Optimized
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - Optimized for t3.large with better stability
workers = 4  # Increased from 3 to 4 for better concurrency
worker_class = "sync"
worker_connections = 1000  # Increased from 500
timeout = 60  # Increased from 30 for better stability
keepalive = 5  # Increased from 2

# Balanced worker recycling - not too frequent, not too infrequent
max_requests = 500  # Increased from 100 - less frequent recycling
max_requests_jitter = 50  # Increased jitter for better distribution

# Memory management - use system temp directory instead of /dev/shm
worker_tmp_dir = None  # Use system default temp directory

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "combot-backend"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if using HTTPS)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Preload app for better performance
preload_app = True

# Performance optimizations
worker_abort_on_app_exit = True
worker_exit_on_app_exit = True

# Memory management - prevent memory leaks
worker_max_requests_jitter = 50
worker_max_requests = 500

# Memory optimization settings
max_requests_jitter = 50
max_requests = 500

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
    worker.log.info("Worker aborted (pid: %s)", worker.pid) 