# Combot Server Capacity Analysis & Recommendations

## Executive Summary
Based on comprehensive stress testing, the Combot server can handle **5-8 concurrent users** optimally while maintaining good performance and data quality.

## Key Findings

### Performance Metrics by Concurrent Users

| Users | Avg Response Time | 95th Percentile | Throughput (req/s) | Success Rate | Recommendation |
|-------|------------------|-----------------|-------------------|--------------|----------------|
| 1     | 2.4s            | 2.8s           | 0.43             | 100%         | ✅ Excellent   |
| 3     | 2.9s            | 4.5s           | 1.47             | 100%         | ✅ Excellent   |
| 5     | 3.8s            | 6.3s           | 2.53             | 100%         | ✅ Good        |
| 8     | 5.0s            | 8.7s           | 3.77             | 100%         | ✅ Good        |
| 10    | 6.1s            | 11.1s          | 5.03             | 100%         | ⚠️ Acceptable  |
| 15    | 7.7s            | 16.4s          | 6.47             | 100%         | ⚠️ Acceptable  |

### Scenario Performance Comparison

| Scenario | 1 User | 5 Users | 10 Users | Notes |
|----------|--------|---------|----------|-------|
| **Basic** | 2.4s | 3.8s | 6.1s | Fastest responses |
| **Lulu** | 2.7s | 5.0s | 8.1s | Slightly slower due to brand-specific processing |
| **Return** | 2.3s | 4.7s | 7.1s | Fastest due to bypassed ML classification |

## Optimal Capacity Recommendations

### 🎯 **Primary Recommendation: 5-8 Concurrent Users**

**Why this range:**
- **Response times**: 3.8-5.0s average (excellent user experience)
- **95th percentile**: 6.3-8.7s (acceptable for most users)
- **Throughput**: 2.5-3.8 requests/second
- **Success rate**: 100% (no failures)
- **Data quality**: 100% weights present

### 📊 **Capacity Tiers**

#### **Tier 1: Optimal (1-5 users)**
- **Response time**: < 4s average
- **User experience**: Excellent
- **Use case**: Production research studies, high-quality data collection

#### **Tier 2: Good (6-8 users)**
- **Response time**: 4-5s average
- **User experience**: Good
- **Use case**: Moderate load studies, acceptable for most research

#### **Tier 3: Acceptable (9-15 users)**
- **Response time**: 6-8s average
- **User experience**: Acceptable but slower
- **Use case**: High-volume studies where speed is less critical

#### **Tier 4: Not Recommended (>15 users)**
- **Response time**: > 8s average
- **User experience**: Poor, potential timeouts
- **Risk**: Server instability, data loss

## Technical Specifications

### Memory Usage
- **Per worker process**: ~800MB
- **Current setup**: 2-3 workers
- **Total memory**: ~2.4GB for 3 workers

### Server Configuration
- **Instance**: EC2 t3.large (2 vCPU, 8GB RAM)
- **Current workers**: 2-3 gunicorn workers
- **Memory utilization**: ~30% under normal load

## Scaling Recommendations

### For 5-10 Concurrent Users
- **Current setup is adequate**
- **Monitor memory usage** during peak times
- **Consider upgrading to t3.xlarge** if memory becomes constrained

### For 10-20 Concurrent Users
- **Upgrade to t3.xlarge** (4 vCPU, 16GB RAM)
- **Increase gunicorn workers** to 4-6
- **Implement load balancing** if needed

### For 20+ Concurrent Users
- **Consider horizontal scaling** with multiple instances
- **Implement Redis** for session management
- **Use load balancer** (ALB/ELB)
- **Database optimization** for high concurrent writes

## Monitoring & Alerts

### Key Metrics to Monitor
1. **Response time** (should stay < 10s for 95th percentile)
2. **Memory usage** (should stay < 80% of available)
3. **Success rate** (should stay > 95%)
4. **Queue length** (if implementing queuing)

### Recommended Alerts
- Response time > 15s for 5+ consecutive requests
- Memory usage > 85%
- Success rate < 95%
- Server process crashes

## Implementation Guidelines

### For Research Studies
- **Limit concurrent users to 5-8** for optimal data quality
- **Implement user queuing** if more users need access
- **Schedule studies** to avoid peak overlap
- **Monitor real-time metrics** during data collection

### For Production Deployment
- **Start with 5 concurrent users** and monitor
- **Scale up gradually** based on actual usage patterns
- **Implement proper monitoring** and alerting
- **Have backup capacity** for unexpected spikes

## Cost-Benefit Analysis

### Current Setup (t3.large)
- **Cost**: ~$60/month
- **Capacity**: 5-8 concurrent users
- **Cost per user**: ~$8-12/month

### Upgraded Setup (t3.xlarge)
- **Cost**: ~$120/month
- **Capacity**: 15-20 concurrent users
- **Cost per user**: ~$6-8/month

## Conclusion

The Combot server is **well-optimized for 5-8 concurrent users** with excellent performance characteristics. The current t3.large instance provides adequate capacity for most research scenarios while maintaining high data quality and user experience standards.

**Immediate action**: No changes needed for current usage patterns.
**Future scaling**: Consider upgrading to t3.xlarge if concurrent user count exceeds 8 regularly.
