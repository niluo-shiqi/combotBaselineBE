# Combot Backend Deployment Guide

This guide explains how to deploy the Combot Backend Django application for production use.

## Quick Start

### Option 1: Using the Launcher Script (Recommended)
```bash
./launch_server.sh
```

This will:
- Activate your virtual environment
- Install dependencies
- Run database migrations
- Start the process manager in the background
- Keep the server running even when you close your terminal

### Option 2: Manual Start
```bash
# Activate virtual environment
source venv/bin/activate  # or source new_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the process manager
python process_manager.py
```

## What's New

### Production Server (Gunicorn)
- Replaced Django's development server with Gunicorn
- Better performance and stability
- Multiple worker processes
- Automatic restart on crashes

### Process Manager
- Keeps the server running continuously
- Automatically restarts if the server crashes
- Logs all activities
- Handles graceful shutdowns

### Configuration Files
- `gunicorn.conf.py`: Gunicorn server configuration
- `process_manager.py`: Process monitoring and restart logic
- `launch_server.sh`: Easy startup script

## Management Commands

### Start the Server
```bash
./launch_server.sh
```

### Stop the Server
```bash
pkill -f "process_manager.py"
```

### View Logs
```bash
# View process manager output
tail -f process_manager_output.log

# View process manager logs
tail -f process_manager.log

# View Django logs
tail -f logging/django_debug.log
tail -f logging/django_errors.log
```

### Check Server Status
```bash
# Check if process manager is running
ps aux | grep process_manager.py

# Check if Gunicorn is running
ps aux | grep gunicorn
```

## Systemd Service (Optional)

If you want the server to start automatically on boot:

1. Copy the service file to systemd:
```bash
sudo cp combot-backend.service /etc/systemd/system/
```

2. Enable and start the service:
```bash
sudo systemctl enable combot-backend
sudo systemctl start combot-backend
```

3. Check status:
```bash
sudo systemctl status combot-backend
```

## Troubleshooting

### Server Won't Start
1. Check if virtual environment is activated
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Check logs: `tail -f process_manager_output.log`

### Server Keeps Restarting
1. Check Django logs for errors: `tail -f logging/django_errors.log`
2. Verify database migrations: `python manage.py migrate`
3. Check if port 8000 is available: `lsof -i :8000`

### Permission Issues
1. Make sure scripts are executable: `chmod +x *.sh`
2. Check file permissions in the project directory

## Environment Variables

Make sure your `.env` file contains:
- `SECRET_KEY`: Django secret key
- `GOOGLE_SHEETS_SPREADSHEET_ID`: Google Sheets integration
- `GOOGLE_SHEETS_CREDENTIALS_FILE`: Google Sheets credentials

## Security Notes

- The server runs on `0.0.0.0:8000` - make sure your firewall is configured
- Consider using HTTPS in production
- Review `ALLOWED_HOSTS` in `settings.py`
- Set `DEBUG = False` in production (already done)

## Performance

- Gunicorn uses multiple worker processes based on CPU cores
- Workers restart after 1000 requests to prevent memory leaks
- Logging is configured for both console and file output
- Static files are collected automatically

## Monitoring

The process manager provides:
- Automatic restart on crashes
- Logging of all activities
- Maximum restart attempts (10) to prevent infinite loops
- Graceful shutdown handling 