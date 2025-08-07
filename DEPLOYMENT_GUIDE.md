# Combot Backend Deployment Guide

## Overview
This guide will help you safely deploy the refactored Combot Backend code to your server with backup and rollback capabilities.

## Pre-Deployment Checklist

### ✅ Backup Current Version
- **Local backup**: `server-backup-20250807-013406` branch created
- **Server version**: `server-version-20250807-013448` branch created
- **Refactored code**: `fix-chatbot-role` branch ready for deployment

### ✅ Safety Measures
- All current code is backed up on GitHub
- Rollback scripts are ready
- Deployment script includes automatic backup creation
- Health checks are implemented

## Deployment Options

### Option 1: Safe Deployment (Recommended)
Use the comprehensive deployment script that includes automatic backup and rollback:

```bash
./deploy_refactored.sh
```

**Features:**
- ✅ Automatic backup creation
- ✅ Health checks and testing
- ✅ Automatic rollback on failure
- ✅ Detailed logging
- ✅ Service verification

### Option 2: Manual Deployment
If you prefer to deploy manually:

1. **Create backup:**
   ```bash
   mkdir -p /tmp/combot_backup_$(date +%Y%m%d_%H%M%S)
   cp -r chatbot /tmp/combot_backup_$(date +%Y%m%d_%H%M%S)/
   cp combotBaselineBE/settings.py /tmp/combot_backup_$(date +%Y%m%d_%H%M%S)/
   cp db.sqlite3 /tmp/combot_backup_$(date +%Y%m%d_%H%M%S)/
   ```

2. **Stop current services:**
   ```bash
   pkill -f gunicorn
   pkill -f auto_restart_monitor
   ```

3. **Update URL patterns:**
   ```bash
   # Backup current urls.py
   cp chatbot/urls.py chatbot/urls_backup.py
   
   # Update to use refactored views
   # (The deployment script will do this automatically)
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install psutil redis django-redis celery
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Start services:**
   ```bash
   nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &
   nohup python auto_restart_monitor.py --memory-threshold 75 --process-memory-threshold 400 --check-interval 60 > monitor.log 2>&1 &
   ```

## Deployment Steps

### Step 1: Verify Current State
```bash
# Check current branch
git branch

# Should show: * fix-chatbot-role

# Check if all refactored files exist
ls -la chatbot/views_refactored.py
ls -la chatbot/services.py
ls -la chatbot/constants.py
ls -la chatbot/exceptions.py
ls -la chatbot/validators.py
```

### Step 2: Run Safe Deployment
```bash
# Make script executable (if not already)
chmod +x deploy_refactored.sh

# Run deployment
./deploy_refactored.sh
```

### Step 3: Monitor Deployment
The deployment script will:
1. Create backup of current version
2. Stop existing services
3. Update code to refactored version
4. Update URL patterns
5. Install dependencies
6. Run database migrations
7. Test deployment
8. Start production services
9. Perform health checks

### Step 4: Verify Deployment
```bash
# Check if services are running
ps aux | grep gunicorn
ps aux | grep auto_restart_monitor

# Test API endpoints
curl http://localhost:8000/api/random/initial/
curl http://localhost:8000/api/memory-status/

# Check logs
tail -f server.log
tail -f monitor.log
```

## Rollback Instructions

### If Deployment Fails
The deployment script will automatically rollback if any step fails.

### Manual Rollback
If you need to rollback manually:

```bash
./rollback.sh
```

**What the rollback script does:**
- Finds the most recent backup
- Stops current services
- Restores previous version
- Restarts services
- Performs health check

### Emergency Rollback
If the rollback script doesn't work:

```bash
# Find backup directory
ls -la /tmp/combot_backup_*

# Restore manually
cp -r /tmp/combot_backup_*/chatbot ./
cp /tmp/combot_backup_*/settings.py combotBaselineBE/
cp /tmp/combot_backup_*/db.sqlite3 ./
cp /tmp/combot_backup_*/urls_backup.py chatbot/urls.py

# Restart services
pkill -f gunicorn
nohup gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py > server.log 2>&1 &
```

## Post-Deployment Verification

### 1. Check Service Status
```bash
# Check if services are running
ps aux | grep gunicorn
ps aux | grep auto_restart_monitor

# Check memory usage
python monitor_memory.py
```

### 2. Test API Endpoints
```bash
# Test initial message
curl http://localhost:8000/api/random/initial/

# Test memory status
curl http://localhost:8000/api/memory-status/

# Test chat endpoint
curl -X POST http://localhost:8000/api/random/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "index": 0}'
```

### 3. Monitor Logs
```bash
# Server logs
tail -f server.log

# Monitor logs
tail -f monitor.log

# Error logs
tail -f error.log
```

### 4. Performance Check
```bash
# Run performance test
python quick_performance_test.py

# Check memory usage
python monitor_memory.py
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Problem**: `ModuleNotFoundError` for new modules
**Solution**: 
```bash
pip install psutil redis django-redis celery
```

#### 2. URL Pattern Errors
**Problem**: URL patterns not found
**Solution**: Check that `chatbot/urls.py` was updated correctly

#### 3. Database Migration Errors
**Problem**: Migration conflicts
**Solution**:
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 4. Service Not Starting
**Problem**: Gunicorn fails to start
**Solution**:
```bash
# Check logs
tail -f server.log

# Check configuration
cat gunicorn.conf.py

# Try manual start
gunicorn combotBaselineBE.wsgi:application --config gunicorn.conf.py
```

### Emergency Contacts

#### If Server Becomes Unresponsive
1. **SSH into server**
2. **Check processes**: `ps aux | grep python`
3. **Kill processes**: `pkill -f gunicorn`
4. **Rollback**: `./rollback.sh`
5. **Check logs**: `tail -f server.log`

#### If Database Issues
1. **Check database**: `python manage.py check`
2. **Reset migrations**: `python manage.py migrate --fake-initial`
3. **Restore backup**: Copy backup database file

## Benefits of Refactored Deployment

### ✅ Improved Architecture
- Modular service layer
- Separation of concerns
- Reusable components

### ✅ Better Error Handling
- Custom exception hierarchy
- Structured error responses
- Comprehensive logging

### ✅ Enhanced Security
- Input validation
- Error message sanitization
- Secure session management

### ✅ Performance Improvements
- Optimized memory management
- Better caching strategies
- Improved response times

### ✅ Maintainability
- Clean code structure
- Comprehensive documentation
- Easy testing and debugging

## Monitoring and Maintenance

### Daily Monitoring
```bash
# Check service status
ps aux | grep gunicorn

# Monitor memory usage
python monitor_memory.py

# Check logs for errors
tail -f server.log | grep ERROR
```

### Weekly Maintenance
```bash
# Clear old logs
find . -name "*.log" -mtime +7 -delete

# Clear cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Check for updates
git fetch origin
git status
```

### Monthly Review
- Review performance metrics
- Check error logs for patterns
- Update dependencies if needed
- Review memory usage trends

## Success Criteria

Deployment is successful when:
- ✅ All services are running
- ✅ API endpoints respond correctly
- ✅ Memory usage is stable
- ✅ Error logs are minimal
- ✅ Performance meets requirements
- ✅ Rollback capability is confirmed

## Support

If you encounter issues during deployment:

1. **Check the deployment log**: `cat deployment_*.log`
2. **Review server logs**: `tail -f server.log`
3. **Verify backup exists**: `ls -la /tmp/combot_backup_*`
4. **Test rollback**: `./rollback.sh`
5. **Contact support** with logs and error messages

---

**Ready to deploy?** Run `./deploy_refactored.sh` to start the safe deployment process! 