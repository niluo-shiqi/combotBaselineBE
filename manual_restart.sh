#!/bin/bash

echo "🔄 MANUAL SERVER RESTART"
echo "========================"
echo "⚠️  Use this only when no users are active!"
echo ""

# Check if server is currently handling requests
echo "🔍 Checking for active users..."
if curl -s http://localhost:8000/api/chatbot/initial/ > /dev/null 2>&1; then
    echo "⚠️  WARNING: Server is responding to requests!"
    echo "   This might mean users are still active."
    echo ""
    read -p "Are you sure you want to restart? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Restart cancelled."
        exit 1
    fi
else
    echo "✅ No active users detected - safe to restart"
fi

echo ""
echo "🔄 Restarting server..."

# Activate virtual environment
source venv/bin/activate

# Stop existing processes
echo "📋 Stopping existing processes..."
pkill -f gunicorn
sleep 3

# Clear cache
echo "🧹 Clearing cache..."
rm -rf ./cache
rm -rf ./__pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clear Django cache
echo "🗑️  Clearing Django cache..."
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Start server
echo "🚀 Starting server..."
nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &

# Wait for server to start
sleep 5

# Check if server started successfully
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Server restarted successfully!"
    echo ""
    echo "📊 Server Status:"
    ps aux | grep gunicorn | grep -v grep
    echo ""
    echo "📋 Next steps:"
    echo "   - Monitor: tail -f server.log"
    echo "   - Test: curl http://localhost:8000/api/chatbot/initial/"
    echo "   - Ready for next batch!"
else
    echo "❌ Server failed to restart. Check server.log for details."
    exit 1
fi 