# EC2 Deployment Guide

## Option 1: Automated Deployment (Recommended)

1. **Update the deployment script** with your EC2 details:
   ```bash
   # Edit deploy_to_ec2.sh and update these lines:
   EC2_USER="ubuntu"  # or "ec2-user" 
   EC2_HOST="3.144.3.186"  # Your EC2 IP
   EC2_KEY_PATH="~/.ssh/your-key.pem"  # Your key file path
   ```

2. **Run the deployment**:
   ```bash
   ./deploy_to_ec2.sh
   ```

## Option 2: Manual Deployment

### Step 1: Connect to your EC2 instance
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@3.144.3.186
```

### Step 2: Upload your code
From your local machine:
```bash
# Create a deployment package
tar -czf deploy.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' .

# Upload to EC2
scp -i ~/.ssh/your-key.pem deploy.tar.gz ubuntu@3.144.3.186:~/
```

### Step 3: Deploy on EC2
On your EC2 instance:
```bash
# Stop any existing processes
pkill -f "python manage.py runserver"
pkill -f "gunicorn"

# Extract the deployment
tar -xzf deploy.tar.gz -C ~/
cd ~/CombotBackend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Make scripts executable
chmod +x *.sh
chmod +x process_manager.py

# Start the server
nohup python process_manager.py > process_manager_output.log 2>&1 &
```

### Step 4: Verify it's running
```bash
# Check if process is running
ps aux | grep process_manager.py

# Check logs
tail -f process_manager_output.log

# Test the server
curl http://localhost:8000
```

## Troubleshooting

### If the server won't start:
1. **Check logs**:
   ```bash
   tail -f process_manager_output.log
   tail -f process_manager.log
   ```

2. **Check if port 8000 is available**:
   ```bash
   lsof -i :8000
   ```

3. **Check virtual environment**:
   ```bash
   which python
   which pip
   ```

4. **Check dependencies**:
   ```bash
   pip list | grep gunicorn
   ```

### If you need to restart:
```bash
# Stop the server
pkill -f "process_manager.py"

# Start again
cd ~/CombotBackend
source venv/bin/activate
nohup python process_manager.py > process_manager_output.log 2>&1 &
```

### To make it start on boot:
```bash
# Create a systemd service
sudo nano /etc/systemd/system/combot-backend.service
```

Add this content:
```ini
[Unit]
Description=Combot Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/CombotBackend
Environment=PATH=/home/ubuntu/CombotBackend/venv/bin
ExecStart=/home/ubuntu/CombotBackend/venv/bin/python /home/ubuntu/CombotBackend/process_manager.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable it:
```bash
sudo systemctl enable combot-backend
sudo systemctl start combot-backend
```

## Security Notes

1. **Update your security group** to allow port 8000
2. **Consider using a reverse proxy** (nginx) for production
3. **Set up HTTPS** for security
4. **Configure firewall rules** properly

## Monitoring

```bash
# Check server status
ps aux | grep process_manager.py

# View real-time logs
tail -f process_manager_output.log

# Check system resources
htop
df -h
``` 