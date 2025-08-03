# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - optimized for t3.medium (2 vCPUs, 4GB RAM)
# Use 3-4 workers for better concurrency
workers = 3  # Reduced from 4 to 3 for better memory management
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 2000  # Reduced from 5000 to 2000 for more frequent restarts
max_requests_jitter = 200  # Reduced jitter to prevent all workers restarting at once

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
worker_max_requests_jitter = 200
worker_max_requests = 2000

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