#!/bin/bash

# Quick Rollback Script for Combot Backend
# This script quickly reverts to the previous version

set -e

echo "🔄 COMBOT BACKEND ROLLBACK"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Find the most recent backup
BACKUP_DIR=$(ls -td /tmp/combot_backup_* 2>/dev/null | head -1)

if [ -z "$BACKUP_DIR" ]; then
    print_error "No backup found! Cannot rollback."
    exit 1
fi

print_status "Found backup: $BACKUP_DIR"

# Confirm rollback
echo ""
echo "⚠️  WARNING: This will rollback to the previous version!"
echo "   Backup location: $BACKUP_DIR"
echo ""
read -p "Are you sure you want to rollback? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Rollback cancelled"
    exit 0
fi

print_status "Starting rollback..."

# Stop current services
print_status "Stopping current services..."
pkill -f gunicorn || true
pkill -f auto_restart_monitor || true
pkill -f celery || true
sleep 3

# Restore from backup
print_status "Restoring from backup..."

# Restore chatbot directory
if [ -d "$BACKUP_DIR/chatbot" ]; then
    rm -rf chatbot
    cp -r "$BACKUP_DIR/chatbot" ./
    print_success "Restored chatbot directory"
fi

# Restore settings
if [ -f "$BACKUP_DIR/settings.py" ]; then
    cp "$BACKUP_DIR/settings.py" combotBaselineBE/
    print_success "Restored settings.py"
fi

# Restore database
if [ -f "$BACKUP_DIR/db.sqlite3" ]; then
    cp "$BACKUP_DIR/db.sqlite3" ./
    print_success "Restored database"
fi

# Restore requirements
if [ -f "$BACKUP_DIR/requirements.txt" ]; then
    cp "$BACKUP_DIR/requirements.txt" ./
    print_success "Restored requirements.txt"
fi

# Restore environment
if [ -f "$BACKUP_DIR/.env" ]; then
    cp "$BACKUP_DIR/.env" ./
    print_success "Restored .env file"
fi

# Restore URLs
if [ -f "$BACKUP_DIR/urls_backup.py" ]; then
    cp "$BACKUP_DIR/urls_backup.py" chatbot/urls.py
    print_success "Restored urls.py"
fi

# Clear cache
print_status "Clearing cache..."
rm -rf ./cache
rm -rf ./__pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
print_status "Running migrations..."
python manage.py migrate

# Start services
print_status "Starting services..."

# Start gunicorn server
nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &
sleep 5

# Check if server started
if pgrep -f gunicorn > /dev/null; then
    print_success "Gunicorn server started"
else
    print_error "Gunicorn server failed to start"
    exit 1
fi

# Start auto-restart monitor
nohup python auto_restart_monitor.py --memory-threshold 75 --process-memory-threshold 400 --check-interval 60 > monitor.log 2>&1 &
sleep 3

if pgrep -f auto_restart_monitor > /dev/null; then
    print_success "Auto-restart monitor started"
else
    print_warning "Auto-restart monitor failed to start"
fi

# Health check
print_status "Performing health check..."
sleep 10

if curl -s http://localhost:8000/api/random/initial/ > /dev/null; then
    print_success "Server is responding"
else
    print_error "Server is not responding"
    exit 1
fi

print_success "🎉 Rollback completed successfully!"
echo ""
echo "📊 Rollback Summary:"
echo "  ✅ Previous version restored"
echo "  ✅ Services restarted"
echo "  ✅ Health check passed"
echo ""
echo "📋 Useful commands:"
echo "  View server logs: tail -f server.log"
echo "  View monitor logs: tail -f monitor.log"
echo "  Check memory: python monitor_memory.py"
echo "  Manual restart: ./restart_server.sh"
echo ""
echo "🌐 Your previous version is ready!" 