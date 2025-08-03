#!/bin/bash

echo "🔄 Restarting Combot Backend Server..."

# Kill existing processes
echo "📋 Stopping existing processes..."
pkill -f gunicorn
pkill -f "python.*manage.py"

# Wait a moment for processes to stop
sleep 2

# Clear any cached files
echo "🧹 Clearing cache..."
rm -rf ./cache
rm -rf ./__pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Clear Django cache
echo "🗑️  Clearing Django cache..."
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Clear sessions (optional - uncomment if you want to clear all sessions)
# echo "🗑️  Clearing sessions..."
# python manage.py shell -c "from django.contrib.sessions.models import Session; Session.objects.all().delete()"

# Restart the server
echo "🚀 Starting server..."
nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &

echo "✅ Server restarted successfully!"
echo "📊 Check server status with: ps aux | grep gunicorn"
echo "📋 View logs with: tail -f server.log" 