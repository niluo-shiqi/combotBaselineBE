#!/bin/bash
# Deploy optimized server for 30 concurrent users

echo "🚀 Deploying optimized Combot server for 30 concurrent users..."

# Kill existing processes
echo "Stopping existing server..."
pkill -f gunicorn

# Wait for processes to stop
sleep 3

# Start optimized server
echo "Starting optimized server with 6 workers..."
cd ~/CombotBackend
source venv/bin/activate

# Use optimized gunicorn configuration
nohup gunicorn --config gunicorn.conf.py combotBaselineBE.wsgi:application > gunicorn.log 2>&1 &

echo "✅ Optimized server started!"
echo "📊 Monitor with: python monitor_30_users.py"
echo "🌐 Server URL: http://3.144.114.76:8000"
