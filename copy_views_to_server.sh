#!/bin/bash

# Quick script to copy views.py to EC2 server
echo "Copying views.py to EC2 server..."

# Configuration - Update these with your EC2 details
EC2_USER="ec2-user"
EC2_HOST="18.222.168.169"
EC2_KEY_PATH="~/.ssh/ec2-key-new.pem"

echo "Copying to: $EC2_USER@$EC2_HOST"

# Copy the views.py file
scp -i $EC2_KEY_PATH chatbot/views.py $EC2_USER@$EC2_HOST:~/CombotBackend/chatbot/

# Restart the server on EC2
echo "Restarting server on EC2..."
ssh -i $EC2_KEY_PATH $EC2_USER@$EC2_HOST << 'EOF'
    cd ~/CombotBackend
    
    # Stop existing processes
    pkill -f "process_manager.py" 2>/dev/null || echo "No existing process to stop"
    pkill -f "gunicorn" 2>/dev/null || echo "No existing gunicorn to stop"
    
    # Wait a moment
    sleep 2
    
    # Start the server again
    echo "Starting the server..."
    nohup python3 process_manager.py > process_manager_output.log 2>&1 &
    
    # Wait a moment and check if it's running
    sleep 5
    if pgrep -f "process_manager.py" > /dev/null; then
        echo "✅ Server restarted successfully!"
        echo "Server should be available at http://$EC2_HOST:8000"
    else
        echo "❌ Server failed to restart. Check logs:"
        tail -20 process_manager_output.log
    fi
EOF

echo "Copy and restart completed!"
echo "Check your server at: http://$EC2_HOST:8000" 