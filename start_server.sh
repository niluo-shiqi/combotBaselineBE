#!/bin/bash

# Start the Django production server
echo "Starting Combot Backend Server..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "new_env" ]; then
    echo "Activating virtual environment..."
    source new_env/bin/activate
fi

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn server
echo "Starting Gunicorn server..."
gunicorn -c gunicorn.conf.py combotBaselineBE.wsgi:application 