#!/usr/bin/env python3
"""
Enhanced Process Manager for Combot Backend
Keeps the Django server running and restarts it when needed
Now includes advanced memory management integration
"""

import subprocess
import time
import signal
import sys
import os
import logging
import psutil
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

class EnhancedProcessManager:
    def __init__(self):
        self.process = None
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10
        
        # Memory management settings
        self.memory_threshold = 0.85  # 85% memory usage
        self.critical_memory_threshold = 0.95  # 95% memory usage
        self.last_memory_check = 0
        self.memory_check_interval = 30  # Check memory every 30 seconds
        
        # Process recycling settings
        self.max_uptime_hours = 4  # Recycle process every 4 hours
        self.start_time = time.time()
        
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
    
    def get_memory_usage(self):
        """Get current memory usage percentage"""
        memory = psutil.virtual_memory()
        return memory.percent / 100.0
    
    def should_recycle_due_to_memory(self):
        """Check if process should be recycled due to memory usage"""
        current_time = time.time()
        if current_time - self.last_memory_check < self.memory_check_interval:
            return False
        
        self.last_memory_check = current_time
        memory_usage = self.get_memory_usage()
        
        if memory_usage > self.critical_memory_threshold:
            logging.critical(f"CRITICAL: Memory usage at {memory_usage:.1%}, forcing restart")
            return True
        elif memory_usage > self.memory_threshold:
            logging.warning(f"WARNING: High memory usage at {memory_usage:.1%}")
        
        return False
    
    def should_recycle_due_to_uptime(self):
        """Check if process should be recycled due to uptime"""
        uptime_hours = (time.time() - self.start_time) / 3600
        if uptime_hours >= self.max_uptime_hours:
            logging.info(f"Process uptime reached {uptime_hours:.1f} hours, recycling")
            return True
        return False
    
    def start_server(self):
        """Start the Django server using Gunicorn with enhanced settings"""
        try:
            logging.info("Starting Django server with enhanced memory management...")
            
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
            
            # Enhanced Gunicorn configuration for memory management
            cmd = [
                gunicorn_path,
                '-c', 'gunicorn.conf.py',
                '--max-requests', '1000',  # Restart workers after 1000 requests
                '--max-requests-jitter', '100',  # Add jitter to prevent thundering herd
                '--timeout', '30',  # Request timeout
                '--keep-alive', '2',  # Keep-alive timeout
                '--preload',  # Preload application code
                'combotBaselineBE.wsgi:application'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            logging.info(f"Server started with PID: {self.process.pid}")
            self.start_time = time.time()  # Reset start time
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
                # Process is running, check for recycling conditions
                should_recycle = False
                
                # Check memory usage
                if self.should_recycle_due_to_memory():
                    should_recycle = True
                    logging.info("Memory-based recycling triggered")
                
                # Check uptime
                if self.should_recycle_due_to_uptime():
                    should_recycle = True
                    logging.info("Uptime-based recycling triggered")
                
                if should_recycle:
                    logging.info("Gracefully terminating server for recycling...")
                    self.process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        self.process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        logging.warning("Server didn't terminate gracefully, forcing kill")
                        self.process.kill()
                    
                    self.process = None
                    self.restart_count = 0  # Reset restart count for recycling
                    logging.info("Server recycled successfully")
                else:
                    # Process is running normally, reset restart count
                    self.restart_count = 0
                
                time.sleep(5)
    
    def run(self):
        """Main run method"""
        logging.info("Enhanced Process Manager starting...")
        logging.info(f"Memory threshold: {self.memory_threshold:.1%}")
        logging.info(f"Critical memory threshold: {self.critical_memory_threshold:.1%}")
        logging.info(f"Max uptime: {self.max_uptime_hours} hours")
        self.monitor_server()
        logging.info("Enhanced Process Manager stopped.")

if __name__ == "__main__":
    manager = EnhancedProcessManager()
    manager.run() 