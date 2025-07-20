#!/bin/bash

# Launcher script for Combot Backend
echo "Launching Combot Backend Server..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
elif [ -d "new_env" ]; then
    echo "Activating virtual environment (new_env)..."
    source new_env/bin/activate
else
    echo "No virtual environment found. Please create one first."
    exit 1
fi

# Install dependencies
echo "Installing/updating dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Check if process manager is already running
if pgrep -f "process_manager.py" > /dev/null; then
    echo "Process manager is already running. Stopping it first..."
    pkill -f "process_manager.py"
    sleep 2
fi

# Start the process manager in the background
echo "Starting process manager..."
nohup python process_manager.py > process_manager_output.log 2>&1 &

# Get the PID
PID=$!
echo "Process manager started with PID: $PID"
echo "Server should be available at http://localhost:8000"
echo ""
echo "To stop the server, run: pkill -f 'process_manager.py'"
echo "To view logs, run: tail -f process_manager_output.log"
echo "To view process manager logs, run: tail -f process_manager.log" 