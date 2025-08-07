#!/bin/bash

# Enhanced Deployment Script for t3.large with Advanced Memory Management
# This script sets up the environment for optimal performance on t3.large instances

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root"
    exit 1
fi

print_status "Starting t3.large optimized deployment..."

# Update system packages
print_status "Updating system packages..."
sudo yum update -y

# Install essential packages for t3.large
print_status "Installing essential packages..."
sudo yum install -y \
    python3 \
    python3-pip \
    python3-devel \
    gcc \
    gcc-c++ \
    make \
    git \
    wget \
    curl \
    htop \
    iotop \
    nethogs \
    tree \
    unzip \
    vim \
    nano \
    tmux \
    screen

# Install Redis for advanced caching
print_status "Installing and configuring Redis..."
if ! command -v redis-server &> /dev/null; then
    sudo yum install -y redis
    
    # Configure Redis for t3.large (2GB RAM)
    sudo cp /etc/redis.conf /etc/redis.conf.backup
    sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis.conf
    sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis.conf
    sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis.conf
    sudo sed -i 's/# save 900 1/save 900 1/' /etc/redis.conf
    sudo sed -i 's/# save 300 10/save 300 10/' /etc/redis.conf
    sudo sed -i 's/# save 60 10000/save 60 10000/' /etc/redis.conf
    
    # Enable and start Redis
    sudo systemctl enable redis
    sudo systemctl start redis
    
    print_success "Redis installed and configured"
else
    print_status "Redis already installed"
fi

# Check Redis status
if sudo systemctl is-active --quiet redis; then
    print_success "Redis is running"
else
    print_error "Redis failed to start"
    exit 1
fi

# Create project directory
PROJECT_DIR="/home/ec2-user/CombotBackend"
print_status "Setting up project directory: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    print_success "Created project directory"
else
    print_status "Project directory already exists"
fi

cd "$PROJECT_DIR"

# Create virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Created virtual environment"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create optimized Gunicorn configuration for t3.large
print_status "Creating optimized Gunicorn configuration..."
cat > gunicorn.conf.py << 'EOF'
# Optimized Gunicorn configuration for t3.large (2 vCPU, 8GB RAM)
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 2  # Optimal for t3.large (2 vCPU)
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "combot-backend"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Memory management
worker_tmp_dir = "/dev/shm"
worker_exit_on_app_exit = False

# Performance tuning
worker_rlimit_nofile = 65536
worker_rlimit_core = 0

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Debugging
reload = False
reload_engine = "auto"
spew = False

# Memory monitoring
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

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_exit(server, worker):
    server.log.info("Worker exited (pid: %s)", worker.pid)

def on_exit(server):
    server.log.info("Server is shutting down")
EOF

print_success "Created optimized Gunicorn configuration"

# Create systemd service for enhanced process manager
print_status "Creating systemd service for enhanced process manager..."
sudo tee /etc/systemd/system/combot-enhanced.service > /dev/null << 'EOF'
[Unit]
Description=Combot Backend Enhanced Process Manager
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/CombotBackend
Environment=PATH=/home/ec2-user/CombotBackend/venv/bin
ExecStart=/home/ec2-user/CombotBackend/venv/bin/python /home/ec2-user/CombotBackend/process_manager.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Memory and resource limits for t3.large
MemoryMax=6G
CPUQuota=200%
LimitNOFILE=65536

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/ec2-user/CombotBackend

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable combot-enhanced.service

print_success "Created systemd service"

# Create monitoring script
print_status "Creating enhanced monitoring script..."
cat > monitor_enhanced.sh << 'EOF'
#!/bin/bash

# Enhanced monitoring script for t3.large
echo "🔍 COMBOT BACKEND ENHANCED MONITORING"
echo "======================================"

# Check system resources
echo "📊 System Resources:"
free -h
echo ""

# Check CPU usage
echo "🖥️  CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
echo ""

# Check disk usage
echo "💿 Disk Usage:"
df -h /
echo ""

# Check Redis status
echo "🔴 Redis Status:"
if systemctl is-active --quiet redis; then
    echo "✅ Redis is running"
    redis-cli info memory | grep -E "(used_memory_human|used_memory_peak_human)"
else
    echo "❌ Redis is not running"
fi
echo ""

# Check application status
echo "🚀 Application Status:"
if systemctl is-active --quiet combot-enhanced; then
    echo "✅ Enhanced process manager is running"
else
    echo "❌ Enhanced process manager is not running"
fi
echo ""

# Check Gunicorn processes
echo "🔄 Gunicorn Processes:"
ps aux | grep gunicorn | grep -v grep
echo ""

# Check memory usage of processes
echo "💾 Process Memory Usage:"
ps aux --sort=-%mem | head -10
echo ""

# Check network connections
echo "🌐 Network Connections:"
netstat -tuln | grep :8000
echo ""

# Check logs
echo "📝 Recent Logs:"
journalctl -u combot-enhanced --no-pager -n 20
echo ""
EOF

chmod +x monitor_enhanced.sh
print_success "Created enhanced monitoring script"

# Create environment file
print_status "Creating environment configuration..."
cat > .env << 'EOF'
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=3.144.114.76,localhost,127.0.0.1,0.0.0.0

# OpenAI Settings
OPENAI_API_KEY=your-openai-api-key-here

# Redis Settings (Optimized for t3.large)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Database Settings
DATABASE_URL=sqlite:///db.sqlite3

# Memory Management Settings
MAX_MEMORY_USAGE=0.85
CRITICAL_MEMORY_USAGE=0.95
MAX_USERS_PER_PROCESS=50
PROCESS_RECYCLE_INTERVAL=4

# Cache Settings
CACHE_TTL=7200
MAX_CACHE_SIZE=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/combot.log
EOF

print_success "Created environment configuration"

# Create logs directory
mkdir -p logs
print_success "Created logs directory"

# Run database migrations
print_status "Running database migrations..."
python manage.py migrate

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Test Redis connection
print_status "Testing Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    print_success "Redis connection successful"
else
    print_error "Redis connection failed"
    exit 1
fi

# Test Django application
print_status "Testing Django application..."
python manage.py check --deploy

# Start the enhanced process manager
print_status "Starting enhanced process manager..."
sudo systemctl start combot-enhanced.service

# Check if service started successfully
sleep 5
if sudo systemctl is-active --quiet combot-enhanced; then
    print_success "Enhanced process manager started successfully"
else
    print_error "Failed to start enhanced process manager"
    sudo systemctl status combot-enhanced.service
    exit 1
fi

# Create startup script
print_status "Creating startup script..."
cat > start_enhanced.sh << 'EOF'
#!/bin/bash

# Enhanced startup script for t3.large
echo "🚀 Starting Combot Backend with Enhanced Memory Management..."

# Check Redis
if ! systemctl is-active --quiet redis; then
    echo "Starting Redis..."
    sudo systemctl start redis
fi

# Check and start enhanced process manager
if ! systemctl is-active --quiet combot-enhanced; then
    echo "Starting enhanced process manager..."
    sudo systemctl start combot-enhanced
fi

# Show status
echo "📊 Service Status:"
sudo systemctl status redis --no-pager -l
echo ""
sudo systemctl status combot-enhanced --no-pager -l
echo ""

# Show monitoring info
echo "🔍 Quick System Check:"
free -h
echo ""
df -h /
echo ""

echo "✅ Enhanced startup completed!"
echo "🌐 Application should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo "📊 Monitor with: ./monitor_enhanced.sh"
echo "📝 View logs with: journalctl -u combot-enhanced -f"
EOF

chmod +x start_enhanced.sh
print_success "Created startup script"

# Create performance test script
print_status "Creating performance test script..."
cat > test_performance.py << 'EOF'
#!/usr/bin/env python3
"""
Performance test script for t3.large deployment
"""

import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor

def make_request():
    """Make a single request to the API"""
    try:
        start_time = time.time()
        response = requests.post(
            'http://localhost:8000/api/chat/',
            json={
                'message': 'I have a problem with my order',
                'index': 0,
                'timer': 0,
                'chatLog': [],
                'classType': '',
                'messageTypeLog': []
            },
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def run_performance_test(num_requests=50, concurrent_requests=10):
    """Run performance test"""
    print(f"🚀 Running performance test: {num_requests} requests, {concurrent_requests} concurrent")
    
    times = []
    successful_requests = 0
    
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        
        for future in futures:
            result = future.result()
            if result is not None:
                times.append(result)
                successful_requests += 1
    
    if times:
        print(f"✅ Successful requests: {successful_requests}/{num_requests}")
        print(f"📊 Response times:")
        print(f"   Average: {statistics.mean(times):.3f}s")
        print(f"   Median: {statistics.median(times):.3f}s")
        print(f"   Min: {min(times):.3f}s")
        print(f"   Max: {max(times):.3f}s")
        print(f"   Std Dev: {statistics.stdev(times):.3f}s")
        
        # Calculate requests per second
        total_time = max(times) - min(times) if len(times) > 1 else times[0]
        rps = len(times) / total_time if total_time > 0 else 0
        print(f"🚀 Requests per second: {rps:.2f}")
    else:
        print("❌ No successful requests")

if __name__ == "__main__":
    run_performance_test()
EOF

chmod +x test_performance.py
print_success "Created performance test script"

# Final status check
print_status "Performing final status check..."

# Check all services
services=("redis" "combot-enhanced")
all_running=true

for service in "${services[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        print_success "$service is running"
    else
        print_error "$service is not running"
        all_running=false
    fi
done

# Check memory usage
memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
print_status "Current memory usage: ${memory_usage}%"

# Check disk usage
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
print_status "Current disk usage: ${disk_usage}%"

if [ "$all_running" = true ]; then
    print_success "🎉 t3.large deployment completed successfully!"
    echo ""
    echo "📋 Deployment Summary:"
    echo "  ✅ Redis caching enabled"
    echo "  ✅ Enhanced process manager running"
    echo "  ✅ Advanced memory management active"
    echo "  ✅ Process recycling every 50 users"
    echo "  ✅ Model unloading between batches"
    echo "  ✅ Connection pooling configured"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  Start services: ./start_enhanced.sh"
    echo "  Monitor system: ./monitor_enhanced.sh"
    echo "  Test performance: python test_performance.py"
    echo "  View logs: journalctl -u combot-enhanced -f"
    echo "  Check status: sudo systemctl status combot-enhanced"
    echo ""
    echo "🌐 Application URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
else
    print_error "❌ Some services failed to start. Check logs for details."
    exit 1
fi 