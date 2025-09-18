#!/bin/bash
# Deploy server optimized for 30 concurrent users

echo "🚀 Deploying server optimized for 30 concurrent users..."

# Kill existing processes
echo "Stopping existing server..."
pkill -f gunicorn

# Wait for processes to stop
sleep 5

# Start optimized server
echo "Starting server with 8 workers for 30 concurrent users..."
cd ~/CombotBackend
source venv/bin/activate

# Use optimized gunicorn configuration
nohup gunicorn --config gunicorn_30_users.conf.py combotBaselineBE.wsgi:application > gunicorn.log 2>&1 &

echo "✅ Server started with 8 workers!"
echo "📊 Monitor with: ps aux | grep gunicorn"
echo "🌐 Server URL: http://3.144.114.76:8000"
echo "👥 Optimized for: 30 concurrent users"
