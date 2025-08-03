#!/bin/bash

echo "🚀 COMBOT BACKEND PRODUCTION DEPLOYMENT (SMART)"
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install required packages
echo "📦 Installing required packages..."
pip install psutil gunicorn requests

# Stop any existing processes
echo "🛑 Stopping existing processes..."
pkill -f gunicorn
pkill -f auto_restart_monitor
sleep 3

# Clear cache and temporary files
echo "🧹 Clearing cache..."
rm -rf ./cache
rm -rf ./__pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clear Django cache
echo "🗑️  Clearing Django cache..."
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Start the server
echo "🚀 Starting server..."
nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &

# Wait for server to start
sleep 5

# Check if server started successfully
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Server started successfully"
else
    echo "❌ Server failed to start. Check server.log for details."
    exit 1
fi

# Start smart auto-restart monitor
echo "🔍 Starting SMART auto-restart monitor..."
echo "🛡️  Safety: Won't restart during active user sessions"
nohup python auto_restart_monitor.py --memory-threshold 75 --process-memory-threshold 400 --check-interval 60 > monitor.log 2>&1 &

# Wait for monitor to start
sleep 3

# Check if monitor started successfully
if pgrep -f auto_restart_monitor > /dev/null; then
    echo "✅ Smart auto-restart monitor started successfully"
else
    echo "❌ Smart auto-restart monitor failed to start. Check monitor.log for details."
    exit 1
fi

echo ""
echo "🎉 SMART PRODUCTION DEPLOYMENT COMPLETE!"
echo "========================================"
echo "📊 Server Status:"
ps aux | grep gunicorn | grep -v grep
echo ""
echo "📊 Smart Monitor Status:"
ps aux | grep auto_restart_monitor | grep -v grep
echo ""
echo "📋 Useful Commands:"
echo "   View server logs: tail -f server.log"
echo "   View monitor logs: tail -f monitor.log"
echo "   Check memory usage: python monitor_memory.py"
echo "   Manual restart: ./restart_server.sh"
echo "   Stop all: pkill -f gunicorn && pkill -f auto_restart_monitor"
echo ""
echo "🎯 Ready for real user batches!"
echo "   - Smart auto-restart when memory > 75%"
echo "   - Smart auto-restart when process memory > 400MB"
echo "   - Checks every 60 seconds"
echo "   - 🛡️  WON'T restart during active user sessions"
echo "   - Handles 6-8 concurrent users easily"
echo ""
echo "🛡️  SAFETY FEATURES:"
echo "   - Waits 5 minutes after last user activity"
echo "   - Checks server responsiveness before restart"
echo "   - Minimum 10 minutes between restarts"
echo "   - Only restarts when truly necessary" 