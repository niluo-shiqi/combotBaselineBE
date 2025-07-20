#!/bin/bash

# Deployment script for EC2
echo "Deploying Combot Backend to EC2..."

# Configuration - Update these with your EC2 details
EC2_USER="ec2-user"  # Amazon Linux 2023 uses ec2-user
EC2_HOST="3.149.2.252"  # Your EC2 public IP
EC2_KEY_PATH="~/.ssh/ec2-key-new.pem"  # Update with your key path
PROJECT_NAME="CombotBackend"

echo "Deploying to: $EC2_USER@$EC2_HOST"
echo "Make sure you have your EC2 key file and it's properly configured!"

# Create a deployment package
echo "Creating deployment package..."
tar -czf deploy.tar.gz \
    --exclude='venv' \
    --exclude='new_env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='db.sqlite3' \
    .

# Upload to EC2
echo "Uploading to EC2..."
scp -i $EC2_KEY_PATH deploy.tar.gz $EC2_USER@$EC2_HOST:~/

# Execute deployment commands on EC2
echo "Running deployment commands on EC2..."
ssh -i $EC2_KEY_PATH $EC2_USER@$EC2_HOST << 'EOF'
    echo "Starting deployment on EC2..."
    
    # Stop any existing processes
    pkill -f "process_manager.py" 2>/dev/null || echo "No existing process to stop"
    pkill -f "gunicorn" 2>/dev/null || echo "No existing gunicorn to stop"
    
    # Remove old deployment if exists
    rm -rf ~/CombotBackend_old 2>/dev/null || echo "No old deployment to remove"
    
    # Backup current deployment if exists
    if [ -d "~/CombotBackend" ]; then
        mv ~/CombotBackend ~/CombotBackend_old
    fi
    
    # Extract new deployment
    tar -xzf deploy.tar.gz -C ~/
    cd ~/CombotBackend
    
    # List files to debug
    echo "Files in directory:"
    ls -la
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Run migrations
    echo "Running migrations..."
    python manage.py migrate
    
    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Make scripts executable
    chmod +x *.sh 2>/dev/null || echo "No .sh files found"
    chmod +x process_manager.py 2>/dev/null || echo "process_manager.py not found"
    
    # Start the server
    echo "Starting the server..."
    nohup python process_manager.py > process_manager_output.log 2>&1 &
    
    # Wait a moment and check if it's running
    sleep 5
    if pgrep -f "process_manager.py" > /dev/null; then
        echo "✅ Server started successfully!"
        echo "Server should be available at http://$EC2_HOST:8000"
    else
        echo "❌ Server failed to start. Check logs:"
        tail -20 process_manager_output.log
    fi
    
    # Clean up
    rm ~/deploy.tar.gz
EOF

# Clean up local deployment package
rm deploy.tar.gz

echo "Deployment completed!"
echo "Check your server at: http://$EC2_HOST:8000"
echo ""
echo "To view logs on EC2:"
echo "ssh -i $EC2_KEY_PATH $EC2_USER@$EC2_HOST"
echo "tail -f ~/CombotBackend/process_manager_output.log" 