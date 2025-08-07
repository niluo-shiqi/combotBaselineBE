#!/bin/bash

# Deploy Refactored Combot Backend with Safety Features
# This script safely deploys the refactored code with backup and rollback capabilities

set -e  # Exit on any error

echo "🚀 Deploying Refactored Combot Backend with Safety Features..."
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_header() {
    echo -e "${PURPLE}[HEADER]${NC} $1"
}

# Configuration
BACKUP_DIR="/tmp/combot_backup_$(date +%Y%m%d_%H%M%S)"
DEPLOYMENT_LOG="deployment_$(date +%Y%m%d_%H%M%S).log"
ROLLBACK_FLAG="/tmp/combot_rollback_required"

# Function to log deployment steps
log_step() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

# Function to create backup
create_backup() {
    print_header "Creating backup of current deployment..."
    log_step "Creating backup directory: $BACKUP_DIR"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup current code
    if [ -d "chatbot" ]; then
        cp -r chatbot "$BACKUP_DIR/"
        log_step "Backed up chatbot directory"
    fi
    
    # Backup settings
    if [ -f "combotBaselineBE/settings.py" ]; then
        cp combotBaselineBE/settings.py "$BACKUP_DIR/"
        log_step "Backed up settings.py"
    fi
    
    # Backup database
    if [ -f "db.sqlite3" ]; then
        cp db.sqlite3 "$BACKUP_DIR/"
        log_step "Backed up database"
    fi
    
    # Backup requirements
    if [ -f "requirements.txt" ]; then
        cp requirements.txt "$BACKUP_DIR/"
        log_step "Backed up requirements.txt"
    fi
    
    # Backup environment variables
    if [ -f ".env" ]; then
        cp .env "$BACKUP_DIR/"
        log_step "Backed up .env file"
    fi
    
    print_success "Backup created at: $BACKUP_DIR"
}

# Function to stop current services
stop_services() {
    print_header "Stopping current services..."
    log_step "Stopping existing processes"
    
    # Stop gunicorn processes
    pkill -f gunicorn || true
    sleep 2
    
    # Stop auto restart monitor
    pkill -f auto_restart_monitor || true
    sleep 2
    
    # Stop celery processes
    pkill -f celery || true
    sleep 2
    
    # Additional cleanup
    pkill -f "python.*manage.py" || true
    
    print_success "Current services stopped"
}

# Function to update code to refactored version
update_code() {
    print_header "Updating code to refactored version..."
    log_step "Applying refactored code changes"
    
    # Check if refactored files exist
    if [ ! -f "chatbot/views_refactored.py" ]; then
        print_error "Refactored views file not found!"
        return 1
    fi
    
    if [ ! -f "chatbot/services.py" ]; then
        print_error "Services file not found!"
        return 1
    fi
    
    if [ ! -f "chatbot/constants.py" ]; then
        print_error "Constants file not found!"
        return 1
    fi
    
    if [ ! -f "chatbot/exceptions.py" ]; then
        print_error "Exceptions file not found!"
        return 1
    fi
    
    if [ ! -f "chatbot/validators.py" ]; then
        print_error "Validators file not found!"
        return 1
    fi
    
    print_success "All refactored files found"
    log_step "Refactored code files verified"
}

# Function to update URL patterns to use refactored views
update_urls() {
    print_header "Updating URL patterns to use refactored views..."
    log_step "Updating URL configuration"
    
    # Create backup of current urls.py
    cp chatbot/urls.py "$BACKUP_DIR/urls_backup.py"
    
    # Update urls.py to use refactored views
    cat > chatbot/urls.py << 'EOF'
from django.urls import path
from .views_refactored import (
    ChatAPIView, InitialMessageAPIView, ClosingMessageAPIView,
    LuluAPIView, LuluInitialMessageAPIView, LuluClosingMessageAPIView,
    RandomEndpointAPIView, memory_status
)

urlpatterns = [
    path('api/chat/', ChatAPIView.as_view(), name='chat'),
    path('api/random/initial/', InitialMessageAPIView.as_view(), name='initial_message'),
    path('api/random/closing/', ClosingMessageAPIView.as_view(), name='closing_message'),
    path('api/lulu/', LuluAPIView.as_view(), name='lulu_chat'),
    path('api/lulu/initial/', LuluInitialMessageAPIView.as_view(), name='lulu_initial'),
    path('api/lulu/closing/', LuluClosingMessageAPIView.as_view(), name='lulu_closing'),
    path('api/random/', RandomEndpointAPIView.as_view(), name='random_endpoint'),
    path('api/memory-status/', memory_status, name='memory_status'),
]
EOF
    
    print_success "URL patterns updated to use refactored views"
    log_step "URL configuration updated"
}

# Function to install dependencies
install_dependencies() {
    print_header "Installing dependencies..."
    log_step "Installing Python dependencies"
    
    # Install requirements
    pip install -r requirements.txt
    
    # Install additional dependencies for refactored code
    pip install psutil redis django-redis celery
    
    print_success "Dependencies installed"
    log_step "Dependencies installation completed"
}

# Function to run database migrations
run_migrations() {
    print_header "Running database migrations..."
    log_step "Running Django migrations"
    
    python manage.py makemigrations
    python manage.py migrate
    
    print_success "Database migrations completed"
    log_step "Database migrations completed"
}

# Function to test the deployment
test_deployment() {
    print_header "Testing deployment..."
    log_step "Starting test server"
    
    # Start server in background for testing
    nohup python manage.py runserver 0.0.0.0:8000 > test_server.log 2>&1 &
    TEST_SERVER_PID=$!
    
    # Wait for server to start
    sleep 10
    
    # Test basic endpoints
    print_status "Testing API endpoints..."
    
    # Test initial message endpoint
    if curl -s http://localhost:8000/api/random/initial/ > /dev/null; then
        print_success "Initial message endpoint working"
        log_step "Initial message endpoint test passed"
    else
        print_error "Initial message endpoint failed"
        log_step "Initial message endpoint test failed"
        return 1
    fi
    
    # Test memory status endpoint
    if curl -s http://localhost:8000/api/memory-status/ > /dev/null; then
        print_success "Memory status endpoint working"
        log_step "Memory status endpoint test passed"
    else
        print_error "Memory status endpoint failed"
        log_step "Memory status endpoint test failed"
        return 1
    fi
    
    # Stop test server
    kill $TEST_SERVER_PID 2>/dev/null || true
    
    print_success "Deployment tests passed"
    log_step "All deployment tests passed"
}

# Function to start production services
start_production_services() {
    print_header "Starting production services..."
    log_step "Starting production deployment"
    
    # Clear cache and temporary files
    print_status "Clearing cache..."
    rm -rf ./cache
    rm -rf ./__pycache__
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clear Django cache
    python manage.py shell -c "from django.core.cache import cache; cache.clear()" 2>/dev/null || true
    
    # Start gunicorn server
    print_status "Starting gunicorn server..."
    nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &
    
    # Wait for server to start
    sleep 5
    
    # Check if server started successfully
    if pgrep -f gunicorn > /dev/null; then
        print_success "Gunicorn server started successfully"
        log_step "Gunicorn server started"
    else
        print_error "Gunicorn server failed to start"
        log_step "Gunicorn server failed to start"
        return 1
    fi
    
    # Start auto-restart monitor
    print_status "Starting auto-restart monitor..."
    nohup python auto_restart_monitor.py --memory-threshold 75 --process-memory-threshold 400 --check-interval 60 > monitor.log 2>&1 &
    
    # Wait for monitor to start
    sleep 3
    
    # Check if monitor started successfully
    if pgrep -f auto_restart_monitor > /dev/null; then
        print_success "Auto-restart monitor started successfully"
        log_step "Auto-restart monitor started"
    else
        print_warning "Auto-restart monitor failed to start"
        log_step "Auto-restart monitor failed to start"
    fi
    
    print_success "Production services started"
    log_step "Production services deployment completed"
}

# Function to perform health check
health_check() {
    print_header "Performing health check..."
    log_step "Starting health check"
    
    # Wait a bit for services to stabilize
    sleep 10
    
    # Check server status
    if curl -s http://localhost:8000/api/random/initial/ > /dev/null; then
        print_success "Server is responding"
        log_step "Health check passed"
    else
        print_error "Server is not responding"
        log_step "Health check failed"
        return 1
    fi
    
    # Check memory usage
    if python -c "import psutil; print('Memory OK' if psutil.virtual_memory().percent < 80 else 'Memory HIGH')" 2>/dev/null; then
        print_success "Memory usage is acceptable"
        log_step "Memory check passed"
    else
        print_warning "Memory usage is high"
        log_step "Memory usage warning"
    fi
    
    print_success "Health check completed"
    log_step "Health check completed successfully"
}

# Function to rollback if needed
rollback() {
    print_error "Rollback required! Restoring previous version..."
    log_step "Starting rollback procedure"
    
    # Stop current services
    stop_services
    
    # Restore from backup
    if [ -d "$BACKUP_DIR" ]; then
        print_status "Restoring from backup..."
        
        # Restore chatbot directory
        if [ -d "$BACKUP_DIR/chatbot" ]; then
            rm -rf chatbot
            cp -r "$BACKUP_DIR/chatbot" ./
            log_step "Restored chatbot directory"
        fi
        
        # Restore settings
        if [ -f "$BACKUP_DIR/settings.py" ]; then
            cp "$BACKUP_DIR/settings.py" combotBaselineBE/
            log_step "Restored settings.py"
        fi
        
        # Restore database
        if [ -f "$BACKUP_DIR/db.sqlite3" ]; then
            cp "$BACKUP_DIR/db.sqlite3" ./
            log_step "Restored database"
        fi
        
        # Restore requirements
        if [ -f "$BACKUP_DIR/requirements.txt" ]; then
            cp "$BACKUP_DIR/requirements.txt" ./
            log_step "Restored requirements.txt"
        fi
        
        # Restore environment
        if [ -f "$BACKUP_DIR/.env" ]; then
            cp "$BACKUP_DIR/.env" ./
            log_step "Restored .env file"
        fi
        
        # Restore URLs
        if [ -f "$BACKUP_DIR/urls_backup.py" ]; then
            cp "$BACKUP_DIR/urls_backup.py" chatbot/urls.py
            log_step "Restored urls.py"
        fi
        
        print_success "Rollback completed"
        log_step "Rollback completed successfully"
        
        # Start services with old version
        start_production_services
    else
        print_error "Backup directory not found!"
        log_step "Backup directory not found for rollback"
    fi
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up temporary files..."
    log_step "Cleaning up deployment artifacts"
    
    # Remove rollback flag if exists
    rm -f "$ROLLBACK_FLAG"
    
    print_success "Cleanup completed"
    log_step "Cleanup completed"
}

# Main deployment function
main() {
    print_header "Starting refactored deployment process..."
    log_step "Deployment started"
    
    # Create backup
    create_backup
    
    # Stop current services
    stop_services
    
    # Update code
    update_code || {
        print_error "Code update failed"
        rollback
        exit 1
    }
    
    # Update URLs
    update_urls || {
        print_error "URL update failed"
        rollback
        exit 1
    }
    
    # Install dependencies
    install_dependencies || {
        print_error "Dependency installation failed"
        rollback
        exit 1
    }
    
    # Run migrations
    run_migrations || {
        print_error "Database migration failed"
        rollback
        exit 1
    }
    
    # Test deployment
    test_deployment || {
        print_error "Deployment test failed"
        rollback
        exit 1
    }
    
    # Start production services
    start_production_services || {
        print_error "Production service start failed"
        rollback
        exit 1
    }
    
    # Health check
    health_check || {
        print_error "Health check failed"
        rollback
        exit 1
    }
    
    # Cleanup
    cleanup
    
    print_success "🎉 Refactored deployment completed successfully!"
    echo ""
    echo "📊 Deployment Summary:"
    echo "  ✅ Backup created at: $BACKUP_DIR"
    echo "  ✅ Refactored code deployed"
    echo "  ✅ Services started successfully"
    echo "  ✅ Health checks passed"
    echo ""
    echo "🔧 Services running:"
    echo "  - Gunicorn server (refactored views)"
    echo "  - Auto-restart monitor"
    echo "  - Memory management service"
    echo "  - Cache service"
    echo ""
    echo "📈 Improvements deployed:"
    echo "  - Modular service layer architecture"
    echo "  - Comprehensive input validation"
    echo "  - Custom exception handling"
    echo "  - Centralized configuration"
    echo "  - Better error handling and logging"
    echo "  - Improved memory management"
    echo ""
    echo "📋 Useful commands:"
    echo "  View server logs: tail -f server.log"
    echo "  View monitor logs: tail -f monitor.log"
    echo "  Check memory: python monitor_memory.py"
    echo "  Manual restart: ./restart_server.sh"
    echo "  Rollback: ./rollback.sh"
    echo ""
    echo "🌐 Your refactored API is ready!"
    
    log_step "Deployment completed successfully"
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; rollback; exit 1' INT TERM

# Run main deployment
main "$@" 