# Advanced Memory Management for Combot Backend (t3.large)

## Overview

This document describes the advanced memory management system implemented for optimal performance on t3.large instances (2 vCPU, 8GB RAM). The system includes model unloading, process recycling, Redis caching, and connection pooling.

## 🚀 Key Features

### 1. **Model Unloading Between Batches**
- Automatically unloads ML models after processing to free memory
- Reloads models only when needed
- Prevents memory leaks from large ML models

### 2. **Process Recycling Every 50 Users**
- Tracks user count and recycles processes after 50 users
- Clears all caches and unloads models during recycling
- Resets memory pressure and starts fresh

### 3. **Redis for Distributed Caching**
- 2-hour TTL for ML classification results
- Intelligent cache key generation
- Automatic cache cleanup when memory pressure is high

### 4. **Connection Pooling**
- Manages database connections efficiently
- Prevents connection leaks
- Optimized for concurrent requests

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django API     │    │   Redis Cache   │
│                 │◄──►│                  │◄──►│                 │
│                 │    │  • MemoryManager │    │  • ML Results   │
│                 │    │  • Process Recycle│   │  • Product Data │
│                 │    │  • Model Unload  │    │  • Session Data │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Database       │
                       │                  │
                       │  • Connection    │
                       │    Pooling       │
                       └──────────────────┘
```

## 📊 Memory Management Components

### MemoryManager Class
```python
class MemoryManager:
    def __init__(self):
        self.user_count = 0
        self.max_users_per_process = 50
        self.ml_model = None
        self.memory_threshold = 0.8  # 80%
        self.force_cleanup_threshold = 0.9  # 90%
```

### Key Methods:
- `increment_user_count()`: Tracks users and triggers recycling
- `recycle_process()`: Clears caches and unloads models
- `unload_ml_model()`: Frees ML model memory
- `force_cleanup()`: Aggressive memory cleanup
- `get_cached_result()`: Redis-based caching
- `set_cached_result()`: Cache with TTL

## 🔧 Configuration

### Environment Variables
```bash
# Memory Management Settings
MAX_MEMORY_USAGE=0.85
CRITICAL_MEMORY_USAGE=0.95
MAX_USERS_PER_PROCESS=50
PROCESS_RECYCLE_INTERVAL=4

# Cache Settings
CACHE_TTL=7200
MAX_CACHE_SIZE=100

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Gunicorn Configuration (t3.large optimized)
```python
# Worker processes
workers = 2  # Optimal for t3.large (2 vCPU)
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

## 📈 Performance Optimizations

### 1. **Memory Thresholds**
- **Normal**: 80% memory usage
- **High**: 85% memory usage (warnings)
- **Critical**: 90% memory usage (force cleanup)

### 2. **Cache Management**
- **Redis TTL**: 2 hours for ML results
- **In-memory cache**: 50 entries max
- **Cleanup**: 50% reduction when full

### 3. **Process Recycling**
- **User count**: Every 50 users
- **Uptime**: Every 4 hours
- **Memory pressure**: When >90% usage

## 🛠️ Deployment

### Quick Start
```bash
# Clone and setup
git clone <repository>
cd CombotBackend

# Run deployment script
chmod +x deploy_t3_large.sh
./deploy_t3_large.sh
```

### Manual Setup
```bash
# Install Redis
sudo yum install -y redis
sudo systemctl enable redis
sudo systemctl start redis

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate
python manage.py collectstatic --noinput

# Start enhanced process manager
sudo systemctl start combot-enhanced.service
```

## 📊 Monitoring

### Enhanced Monitoring Script
```bash
./monitor_enhanced.sh
```

**Output includes:**
- System memory usage
- CPU and disk usage
- Redis cache statistics
- ML model status
- Process memory usage
- Network I/O

### Performance Testing
```bash
python test_performance.py
```

**Tests:**
- 50 concurrent requests
- Response time analysis
- Requests per second calculation
- Memory usage during load

## 🔍 Troubleshooting

### Common Issues

#### 1. **High Memory Usage**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Force cleanup
sudo systemctl restart combot-enhanced
```

#### 2. **Redis Connection Issues**
```bash
# Check Redis status
sudo systemctl status redis
redis-cli ping

# Restart Redis
sudo systemctl restart redis
```

#### 3. **ML Model Loading Failures**
```bash
# Check model status
python manage.py shell -c "from chatbot.views import memory_manager; print(memory_manager.ml_model is not None)"

# Force model reload
sudo systemctl restart combot-enhanced
```

### Log Analysis
```bash
# View application logs
journalctl -u combot-enhanced -f

# View Redis logs
sudo tail -f /var/log/redis/redis.log

# View system logs
journalctl -f
```

## 📋 Service Management

### Systemd Services
```bash
# Enhanced Process Manager
sudo systemctl status combot-enhanced
sudo systemctl start combot-enhanced
sudo systemctl stop combot-enhanced
sudo systemctl restart combot-enhanced

# Redis
sudo systemctl status redis
sudo systemctl restart redis
```

### Useful Commands
```bash
# Start all services
./start_enhanced.sh

# Monitor system
./monitor_enhanced.sh

# Test performance
python test_performance.py

# View logs
journalctl -u combot-enhanced -f
```

## 🎯 Performance Benchmarks

### t3.large Expected Performance
- **Concurrent Users**: 50-100
- **Response Time**: <2 seconds
- **Memory Usage**: <6GB (75%)
- **CPU Usage**: <80%
- **Requests/Second**: 10-20

### Memory Optimization Results
- **Model Loading**: 30-60 seconds
- **Cache Hit Rate**: >80%
- **Memory Cleanup**: <5 seconds
- **Process Recycling**: <10 seconds

## 🔄 Process Lifecycle

### Normal Operation
1. **Startup**: Load ML model, initialize caches
2. **Request Processing**: Use cached results when possible
3. **Memory Monitoring**: Check thresholds every request
4. **Cache Management**: Clean up when full

### Recycling Process
1. **Trigger**: 50 users or memory pressure
2. **Cleanup**: Clear all caches
3. **Model Unload**: Free ML model memory
4. **Garbage Collection**: Multiple passes
5. **Reset**: Start fresh with new process

### Emergency Cleanup
1. **Memory Pressure**: >90% usage
2. **Force Unload**: All models and caches
3. **Database**: Close connections
4. **Restart**: Fresh process if needed

## 📚 API Endpoints

### Memory Management Endpoints
- `GET /api/health/`: System health check
- `GET /api/memory/`: Memory usage statistics
- `POST /api/cleanup/`: Force memory cleanup
- `GET /api/cache/stats/`: Cache statistics

### Monitoring Endpoints
- `GET /api/metrics/`: Performance metrics
- `GET /api/process/status/`: Process status
- `GET /api/redis/status/`: Redis status

## 🔐 Security Considerations

### Memory Protection
- **Process Isolation**: Each worker in separate process
- **Memory Limits**: Systemd memory limits
- **Resource Quotas**: CPU and file descriptor limits

### Cache Security
- **TTL Enforcement**: Automatic cache expiration
- **Key Sanitization**: MD5 hashing for cache keys
- **Access Control**: Redis authentication

## 📈 Scaling Considerations

### Vertical Scaling (t3.large → t3.xlarge)
- **Memory**: 8GB → 16GB
- **Workers**: 2 → 4
- **Cache Size**: 100 → 200 entries
- **User Limit**: 50 → 100 users

### Horizontal Scaling
- **Load Balancer**: Multiple instances
- **Redis Cluster**: Shared cache
- **Database**: Connection pooling
- **Session Storage**: Redis-based

## 🚨 Alerts and Notifications

### Memory Alerts
- **Warning**: >80% memory usage
- **Critical**: >90% memory usage
- **Emergency**: >95% memory usage

### Process Alerts
- **Recycling**: Every 50 users
- **Uptime**: Every 4 hours
- **Errors**: Failed requests >5%

### Cache Alerts
- **Hit Rate**: <70% cache hit rate
- **Size**: Cache >80% full
- **TTL**: Expired entries >50%

## 📝 Best Practices

### Development
1. **Test Locally**: Use same memory constraints
2. **Monitor Early**: Start monitoring from development
3. **Profile Memory**: Use memory profiling tools
4. **Cache Strategically**: Cache expensive operations

### Production
1. **Monitor Continuously**: Use monitoring scripts
2. **Set Alerts**: Configure memory alerts
3. **Regular Recycling**: Schedule process recycling
4. **Backup Data**: Regular Redis and database backups

### Maintenance
1. **Log Rotation**: Regular log cleanup
2. **Cache Warming**: Preload frequently used data
3. **Health Checks**: Regular system health checks
4. **Performance Testing**: Regular load testing

## 🔗 Related Files

- `chatbot/views.py`: Main memory management implementation
- `process_manager.py`: Enhanced process manager
- `monitor_memory.py`: Memory monitoring script
- `deploy_t3_large.sh`: Deployment script
- `gunicorn.conf.py`: Optimized Gunicorn configuration
- `requirements.txt`: Python dependencies

## 📞 Support

For issues with the advanced memory management system:

1. **Check Logs**: `journalctl -u combot-enhanced -f`
2. **Monitor Memory**: `./monitor_enhanced.sh`
3. **Test Performance**: `python test_performance.py`
4. **Restart Services**: `sudo systemctl restart combot-enhanced`

---

**Last Updated**: December 2024
**Version**: 2.0 (Advanced Memory Management)
**Compatibility**: t3.large instances and above 