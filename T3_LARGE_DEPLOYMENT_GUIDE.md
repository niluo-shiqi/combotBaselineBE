# T3.Large Deployment Guide
## IP: 3.144.114.76

### 🚀 Quick Deployment Steps

#### 1. **Connect to Your New t3.large Instance**
```bash
ssh -i your-key.pem ec2-user@3.144.114.76
```

#### 2. **Clone or Upload Your Code**
```bash
# Option A: Clone from git
git clone <your-repository-url>
cd CombotBackend

# Option B: Upload via SCP
scp -r /path/to/your/CombotBackend ec2-user@3.144.114.76:~/
```

#### 3. **Run the Enhanced Deployment Script**
```bash
cd CombotBackend
chmod +x deploy_t3_large.sh
./deploy_t3_large.sh
```

#### 4. **Verify Installation**
```bash
# Check services
sudo systemctl status redis
sudo systemctl status combot-enhanced

# Test the application
curl http://3.144.114.76:8000/api/health/
```

### 📊 **What Gets Installed:**

✅ **Redis** - Advanced caching (512MB limit)
✅ **Enhanced Process Manager** - Memory management
✅ **Optimized Gunicorn** - 2 workers for t3.large
✅ **Monitoring Scripts** - Real-time system monitoring
✅ **Performance Testing** - Load testing tools

### 🔧 **Key Features for t3.large:**

- **Memory Management**: 8GB RAM optimized
- **Process Recycling**: Every 50 users
- **Model Unloading**: Between batches
- **Redis Caching**: 2-hour TTL
- **Connection Pooling**: Database optimization

### 📈 **Expected Performance:**

- **Concurrent Users**: 50-100
- **Response Time**: <2 seconds
- **Memory Usage**: <6GB (75%)
- **Cache Hit Rate**: >80%

### 🛠️ **Useful Commands:**

```bash
# Start all services
./start_enhanced.sh

# Monitor system
./monitor_enhanced.sh

# Test performance
python test_performance.py

# View logs
journalctl -u combot-enhanced -f

# Check status
sudo systemctl status combot-enhanced
```

### 🌐 **Access Your Application:**

- **Main API**: http://3.144.114.76:8000
- **Health Check**: http://3.144.114.76:8000/api/health/
- **Admin Panel**: http://3.144.114.76:8000/admin/

### 🔍 **Monitoring Dashboard:**

The enhanced monitoring script provides:
- System memory usage
- CPU and disk usage
- Redis cache statistics
- ML model status
- Process memory usage
- Network I/O

### 🚨 **Troubleshooting:**

#### If Redis fails to start:
```bash
sudo systemctl restart redis
sudo systemctl status redis
```

#### If the application fails to start:
```bash
sudo systemctl restart combot-enhanced
journalctl -u combot-enhanced -f
```

#### If memory usage is high:
```bash
./monitor_enhanced.sh
# Check if process recycling is working
```

### 📝 **Environment Configuration:**

The deployment script creates a `.env` file with:
- **ALLOWED_HOSTS**: 3.144.114.76
- **Redis**: localhost:6379
- **Memory Limits**: 85% warning, 95% critical
- **Cache TTL**: 7200 seconds (2 hours)

### 🎯 **Next Steps:**

1. **Test the API**: Make a test request to verify everything works
2. **Monitor Performance**: Use the monitoring scripts
3. **Load Test**: Run performance tests
4. **Update Frontend**: Point your frontend to the new IP

### 📞 **Support:**

If you encounter issues:
1. Check logs: `journalctl -u combot-enhanced -f`
2. Monitor memory: `./monitor_enhanced.sh`
3. Test performance: `python test_performance.py`
4. Restart services: `sudo systemctl restart combot-enhanced`

---

**Instance**: t3.large (2 vCPU, 8GB RAM)
**IP Address**: 3.144.114.76
**Deployment Script**: `deploy_t3_large.sh`
**Documentation**: `ADVANCED_MEMORY_MANAGEMENT.md` 