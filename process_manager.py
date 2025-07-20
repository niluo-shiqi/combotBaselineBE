#!/usr/bin/env python3
"""
Process Manager for Combot Backend
Keeps the Django server running and restarts it when needed
"""

import subprocess
import time
import signal
import sys
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_manager.log'),
        logging.StreamHandler()
    ]
)

class ProcessManager:
    def __init__(self):
        self.process = None
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.process:
            self.process.terminate()
        sys.exit(0)
    
    def start_server(self):
        """Start the Django server using Gunicorn"""
        try:
            logging.info("Starting Django server...")
            
            # Change to project directory
            os.chdir('/home/ec2-user/CombotBackend')
            
            # Activate virtual environment
            venv_path = None
            if os.path.exists('venv'):
                venv_path = 'venv'
            elif os.path.exists('new_env'):
                venv_path = 'new_env'
            
            if venv_path:
                # Set environment variables for virtual environment
                os.environ['VIRTUAL_ENV'] = os.path.abspath(venv_path)
                os.environ['PATH'] = os.path.join(os.environ['VIRTUAL_ENV'], 'bin') + os.pathsep + os.environ['PATH']
                logging.info(f"Activated virtual environment: {venv_path}")
            
            # Start Gunicorn with full path to virtual environment
            if venv_path:
                gunicorn_path = os.path.join(venv_path, 'bin', 'gunicorn')
            else:
                gunicorn_path = 'gunicorn'
            
            cmd = [
                gunicorn_path,
                '-c', 'gunicorn.conf.py',
                'combotBaselineBE.wsgi:application'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            logging.info(f"Server started with PID: {self.process.pid}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
            return False
    
    def monitor_server(self):
        """Monitor the server process and restart if needed"""
        while self.running:
            if self.process is None:
                if self.restart_count >= self.max_restarts:
                    logging.error("Max restart attempts reached. Exiting.")
                    break
                
                if not self.start_server():
                    self.restart_count += 1
                    time.sleep(5)
                    continue
            
            # Check if process is still running
            if self.process.poll() is not None:
                logging.warning(f"Server process died with return code: {self.process.returncode}")
                self.process = None
                self.restart_count += 1
                
                if self.restart_count <= self.max_restarts:
                    logging.info(f"Restarting server (attempt {self.restart_count}/{self.max_restarts})")
                    time.sleep(2)
                else:
                    logging.error("Max restart attempts reached. Exiting.")
                    break
            else:
                # Process is running, reset restart count
                self.restart_count = 0
                time.sleep(5)
    
    def run(self):
        """Main run method"""
        logging.info("Process Manager starting...")
        self.monitor_server()
        logging.info("Process Manager stopped.")

if __name__ == "__main__":
    manager = ProcessManager()
    manager.run() 