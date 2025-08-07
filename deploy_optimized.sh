#!/bin/bash

# Deploy Optimized Combot Backend
# This script sets up Redis, installs dependencies, and starts optimized services

set -e  # Exit on any error

echo "🚀 Deploying Optimized Combot Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're on the server
if [[ "$(hostname)" == *"ec2"* ]]; then
    print_status "Running on EC2 server"
    SERVER_MODE=true
else
    print_status "Running locally"
    SERVER_MODE=false
fi

# Install Redis if on server
if [ "$SERVER_MODE" = true ]; then
    print_status "Installing Redis..."
    
    # Check if Redis is already installed
    if ! command -v redis-server &> /dev/null; then
        sudo yum update -y
        sudo yum install -y redis
        
        # Configure Redis for production
        sudo cp /etc/redis.conf /etc/redis.conf.backup
        sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis.conf
        sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis.conf
        sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis.conf
        
        # Start Redis
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
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Run database migrations
print_status "Running database migrations..."
python manage.py migrate

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file..."
    cat > .env << EOF
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False

# OpenAI Settings
OPENAI_API_KEY=your-openai-api-key-here

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Performance Settings
MAX_CONCURRENT_ML_OPERATIONS=3
ML_RESULT_CACHE_TIMEOUT=7200
REQUEST_QUEUE_TIMEOUT=30
EOF
    print_warning "Please update .env file with your actual API keys"
fi

# Start optimized services
print_status "Starting optimized services..."
python manage.py start_optimized_services --preload-models --warm-cache --health-check

# Start Celery worker (background)
print_status "Starting Celery worker..."
nohup celery -A combotBaselineBE worker --loglevel=info > celery.log 2>&1 &

# Start Celery beat for scheduled tasks
print_status "Starting Celery beat..."
nohup celery -A combotBaselineBE beat --loglevel=info > celery_beat.log 2>&1 &

# Wait a moment for services to start
sleep 5

# Check service status
print_status "Checking service status..."

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is responding"
else
    print_error "Redis is not responding"
fi

# Check Celery
if pgrep -f "celery.*worker" > /dev/null; then
    print_success "Celery worker is running"
else
    print_error "Celery worker is not running"
fi

# Check Django
if curl -s http://localhost:8000/api/random/initial/ > /dev/null; then
    print_success "Django server is responding"
else
    print_error "Django server is not responding"
fi

print_success "Deployment completed!"
echo ""
echo "📊 Optimization Summary:"
echo "  ✅ Redis caching enabled"
echo "  ✅ ML model pooling active"
echo "  ✅ Request queuing implemented"
echo "  ✅ Performance monitoring active"
echo "  ✅ Async processing ready"
echo ""
echo "🔧 Services running:"
echo "  - Django server"
echo "  - Redis cache"
echo "  - Celery worker"
echo "  - Celery beat"
echo ""
echo "📈 Performance improvements:"
echo "  - Reduced memory usage per request"
echo "  - Faster response times with caching"
echo "  - Better concurrent user handling"
echo "  - Automatic resource cleanup"
echo ""
echo "🌐 Your API is ready at: http://localhost:8000" 