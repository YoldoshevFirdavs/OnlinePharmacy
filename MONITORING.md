# Monitoring & Observability Stack

## Table of Contents
1. [Overview](#overview)
2. [Monitoring Stack Components](#monitoring-stack-components)
3. [Prometheus Configuration](#prometheus-configuration)
4. [Grafana Setup](#grafana-setup)
5. [Metrics Collection](#metrics-collection)
6. [Alerting](#alerting)
7. [Logging & Debugging](#logging--debugging)
8. [Development Monitoring](#development-monitoring)
9. [Production Monitoring](#production-monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Overview

OnlinePharmacy implements comprehensive monitoring using:

- **Prometheus** — Metrics collection and time-series database
- **Grafana** — Visualization and dashboarding
- **Django Prometheus Exporter** — Application metrics
- **Structured Logging** — Centralized log collection

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Application                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ prometheus_client (metrics exporter)                   │  │
│  │ - HTTP requests (latency, status codes)                │  │
│  │ - Database queries (duration, count)                   │  │
│  │ - Cache hits/misses                                    │  │
│  │ - Custom app metrics (orders, payments, etc.)          │  │
│  └────────────────────────────────────────────────────────┘  │
│                         ↓                                     │
│                   /metrics/ endpoint                          │
└─────────────────────────────────────────────────────────────┘
         ↓
    [Prometheus]  ← scrapes every 15 seconds
         ↓
    [Grafana]     ← queries time-series data
         ↓
   [Dashboards]   ← visualizes metrics
         ↓
   [Alerts]       ← triggers notifications
```

---

## Monitoring Stack Components

### 1. Prometheus

**Purpose:** Time-series database and metrics collection engine.

**Key Responsibilities:**
- Scrape metrics from Django application
- Store metrics with timestamps
- Execute alert rules
- Expose metrics API for Grafana

**Configuration:**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s          # Collect metrics every 15 seconds
  evaluation_interval: 15s      # Evaluate alert rules every 15 seconds
  external_labels:
    monitor: 'pharmacy-monitor'

scrape_configs:
  - job_name: 'django'
    static_configs:
      - targets: ['web:8000']   # Django application
    metrics_path: '/metrics/'
    scrape_interval: 15s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']  # Optional: PostgreSQL metrics
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']    # Optional: Redis metrics
    scrape_interval: 30s
```

**Docker Integration:**

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'  # Keep 15 days of metrics
    networks:
      - pharmacy_network

volumes:
  prometheus_data:
```

**Access Prometheus UI:**

```
http://localhost:9090
```

Useful queries:
- `rate(http_requests_total[5m])` — Request rate (5-minute average)
- `histogram_quantile(0.95, http_request_duration_seconds)` — 95th percentile latency
- `django_db_query_duration_seconds` — Database query duration

---

### 2. Grafana

**Purpose:** Visualization and alerting for metrics.

**Key Responsibilities:**
- Query Prometheus data
- Create dashboards
- Set up alerts
- Send notifications

**Configuration:**

```yaml
# docker-compose.yml
services:
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    networks:
      - pharmacy_network

volumes:
  grafana_data:
```

**Access Grafana:**

```
http://localhost:3000
Default credentials: admin/admin
```

**First-Time Setup:**

1. Log in with admin/admin
2. Change password (Admin → Profile → Change password)
3. Add Prometheus data source:
   - Data Sources → Add data source
   - Type: Prometheus
   - URL: `http://prometheus:9090`
   - Save & test
4. Import dashboards (see Dashboards section)

---

### 3. Django Prometheus Client

**Purpose:** Export Django application metrics.

**Installation:**

```bash
pip install prometheus-client
```

**Configuration:**

```python
# config/settings.py
INSTALLED_APPS = [
    # ...
    'prometheus_client',
]

MIDDLEWARE = [
    # ...
    'prometheus_client.middleware.PrometheusMiddleware',  # Add early
    # ... other middleware
]

# Prometheus metrics configuration
PROMETHEUS_METRICS = {
    'scrape_path': '/metrics/',
    'client_version': 'v1',
}
```

**URL Configuration:**

```python
# config/urls.py
from prometheus_client import generate_latest
from django.http import HttpResponse

def metrics(request):
    """Export Prometheus metrics"""
    return HttpResponse(generate_latest(), content_type='text/plain')

urlpatterns = [
    # ...
    path('metrics/', metrics, name='prometheus-metrics'),
]
```

**Metrics Exported:**

```
# HTTP Metrics
http_requests_total{method="GET", status="200"}        2500
http_request_duration_seconds{method="GET"}            0.025  (seconds)

# Django ORM Metrics
django_db_query_duration_seconds{operation="SELECT"}   0.003
django_db_queries_total{operation="INSERT"}            145

# Cache Metrics
django_cache_hits_total                                1240
django_cache_misses_total                              320

# Celery Task Metrics
celery_task_duration_seconds{task_name="send_email"}   0.500
celery_tasks_total{task_name="process_order", status="success"}  450
```

---

## Prometheus Configuration

### Query Language (PromQL)

**Basic Queries:**

```promql
# Current value
http_requests_total

# With label matching
http_requests_total{method="GET"}
http_requests_total{status=~"5.."}  # 5xx status codes

# Rate of change (5-minute average)
rate(http_requests_total[5m])

# Sum over time
sum(http_requests_total)

# Average latency
avg(http_request_duration_seconds)

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Database queries per second
rate(django_db_queries_total[1m])

# Cache hit ratio
rate(django_cache_hits_total[5m]) / (rate(django_cache_hits_total[5m]) + rate(django_cache_misses_total[5m]))
```

### Recording Rules

Create pre-computed metrics for expensive queries:

```yaml
# prometheus_recording_rules.yml
groups:
  - name: django_app
    interval: 15s
    rules:
      - record: 'http:requests:rate5m'
        expr: 'sum(rate(http_requests_total[5m]))'

      - record: 'http:latency:p95'
        expr: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

      - record: 'db:queries:rate1m'
        expr: 'sum(rate(django_db_queries_total[1m]))'

      - record: 'cache:hit_ratio'
        expr: 'sum(rate(django_cache_hits_total[5m])) / (sum(rate(django_cache_hits_total[5m])) + sum(rate(django_cache_misses_total[5m])))'
```

---

## Grafana Setup

### Dashboard Templates

**1. Application Health Dashboard**

Track real-time application status:

```json
{
  "dashboard": {
    "title": "Application Health",
    "panels": [
      {
        "title": "Request Rate (req/s)",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "P95 Latency (ms)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000"
          }
        ]
      },
      {
        "title": "Error Rate (%)",
        "targets": [
          {
            "expr": "(sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m]))) * 100"
          }
        ]
      },
      {
        "title": "Database Query Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(django_db_query_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

**2. Business Metrics Dashboard**

Track domain-specific metrics:

```json
{
  "dashboard": {
    "title": "Business Metrics",
    "panels": [
      {
        "title": "Orders Created (per hour)",
        "targets": [
          {
            "expr": "increase(orders_created_total[1h])"
          }
        ]
      },
      {
        "title": "Total Revenue (USD)",
        "targets": [
          {
            "expr": "sum(orders_total_revenue)"
          }
        ]
      },
      {
        "title": "Failed Payments (%)",
        "targets": [
          {
            "expr": "(sum(payments_failed_total) / sum(payments_total)) * 100"
          }
        ]
      },
      {
        "title": "Active Users (5 min window)",
        "targets": [
          {
            "expr": "count(rate(http_requests_total[5m]) > 0)"
          }
        ]
      }
    ]
  }
}
```

**3. Infrastructure Dashboard**

Monitor system resources:

```json
{
  "dashboard": {
    "title": "Infrastructure",
    "panels": [
      {
        "title": "Memory Usage (%)",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
          }
        ]
      },
      {
        "title": "CPU Usage (%)",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
          }
        ]
      },
      {
        "title": "Disk Usage (%)",
        "targets": [
          {
            "expr": "(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100"
          }
        ]
      }
    ]
  }
}
```

### Creating Custom Dashboards

**Step 1: Add Data Source**

```
Data Sources → Add data source → Prometheus
URL: http://prometheus:9090
```

**Step 2: Create Dashboard**

```
+ Create → Dashboard
Add panel → Metrics query
```

**Step 3: Configure Panel**

```
Title: "Request Rate"
Query: rate(http_requests_total[5m])
Legend: {{method}} {{status}}
Y-axis: Requests/sec
```

**Step 4: Save Dashboard**

```
Save dashboard as JSON for version control
```

---

## Metrics Collection

### Custom Application Metrics

Define business metrics in Django:

```python
# pharmacy/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Summary
import time

# Counters (monotonically increasing)
orders_created_total = Counter(
    'orders_created_total',
    'Total orders created',
    ['status']
)

payments_total = Counter(
    'payments_total',
    'Total payments processed',
    ['method', 'status']
)

# Gauges (can go up/down)
active_orders = Gauge(
    'active_orders',
    'Currently active orders',
    ['status']
)

inventory_stock = Gauge(
    'inventory_stock',
    'Current medicine stock',
    ['medicine_id', 'medicine_name']
)

# Histograms (track distribution)
order_processing_time = Histogram(
    'order_processing_time_seconds',
    'Time to process order',
    buckets=(1, 5, 10, 30, 60, 300)
)

# Summaries (compute quantiles)
payment_amount = Summary(
    'payment_amount_usd',
    'Payment amount in USD'
)
```

**Recording Metrics:**

```python
# orders/views.py
from pharmacy.metrics import orders_created_total, active_orders, order_processing_time

class OrderCreateView(APIView):
    def post(self, request):
        start_time = time.time()
        
        # Create order
        order = Order.objects.create(...)
        
        # Record metrics
        orders_created_total.labels(status='pending').inc()
        active_orders.labels(status='pending').inc()
        
        duration = time.time() - start_time
        order_processing_time.observe(duration)
        
        return Response(serializer.data)
```

---

## Alerting

### Alert Rules

Define alert conditions:

```yaml
# prometheus_alert_rules.yml
groups:
  - name: pharmacy_alerts
    interval: 1m
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: 'rate(http_requests_total{status=~"5.."}[5m]) > 0.05'
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanize }}% (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1'
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency is high"
          description: "P95 latency is {{ $value | humanize }}s (threshold: 1s)"

      # Database connection issues
      - alert: DatabaseConnectionPoolExhausted
        expr: 'django_db_connections_current >= django_db_connections_max * 0.9'
        for: 2m
        labels:
          severity: warning

      # Payment failures
      - alert: PaymentFailureRate
        expr: '(sum(rate(payments_failed_total[5m])) / sum(rate(payments_total[5m]))) > 0.1'
        for: 5m
        labels:
          severity: critical

      # Low inventory
      - alert: LowInventory
        expr: 'inventory_stock < 10'
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Low stock for {{ $labels.medicine_name }}"
```

### Notification Channels

Configure alert destinations:

**Email Notifications:**

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'email'
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 3h

receivers:
  - name: 'email'
    email_configs:
      - to: 'admin@onlinepharmacy.uz'
        from: 'alerts@onlinepharmacy.uz'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@onlinepharmacy.uz'
        auth_password: '${EMAIL_PASSWORD}'
```

**Slack Notifications:**

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'
        title: 'Pharmacy Alert'
        text: '{{ .GroupLabels.alertname }}'
```

---

## Logging & Debugging

### Django Logging Configuration

```python
# config/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'pharmacy': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}
```

### Structured Logging

Use JSON-formatted logs for better parsing:

```python
import logging
import json

logger = logging.getLogger(__name__)

# Log structured data
logger.info(json.dumps({
    'event': 'order_created',
    'order_id': order.id,
    'user_id': order.user.id,
    'total_price': float(order.total_price),
    'timestamp': timezone.now().isoformat()
}))
```

### Debug Toolbar (Development Only)

```python
# config/settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

Access at bottom-right corner of browser in development.

---

## Development Monitoring

### Local Prometheus & Grafana

**Quick Start:**

```bash
# Start monitoring stack
docker-compose up -d prometheus grafana

# Access Prometheus
http://localhost:9090

# Access Grafana
http://localhost:3000
```

**Prometheus Queries (Development):**

```promql
# Last 1 hour of metrics
http_requests_total[1h]

# Current request rate
rate(http_requests_total[5m])

# Recent errors
increase(http_requests_total{status=~"5.."}[1m])

# Slow queries
histogram_quantile(0.99, rate(django_db_query_duration_seconds_bucket[5m]))
```

### Debugging Performance Issues

**1. High Latency**

```promql
# Find slowest endpoints
topk(5, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="django"}[5m])))

# Check database query time
avg by (operation) (rate(django_db_query_duration_seconds[5m]))
```

**2. High Memory Usage**

```bash
# Check application memory
docker stats pharmacy_web
```

**3. Database Connection Issues**

```promql
# Active connections
django_db_connections_current

# Connection pool usage
django_db_connections_current / django_db_connections_max
```

---

## Production Monitoring

### Production Configuration

**Environment Variables:**

```env
# .env.prod
PROMETHEUS_SCRAPE_INTERVAL=30s
GRAFANA_PASSWORD=<strong_password>
ALERT_EMAIL=admin@onlinepharmacy.uz
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

**Persistent Data:**

```yaml
# docker-compose.prod.yml
volumes:
  prometheus_data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs-server.example.com,vers=4,soft,timeo=180,bg,tcp,rw
      device: ":/data/prometheus"
  
  grafana_data:
    driver: local
```

### Production Alerts

Set up critical alerts:

```yaml
# Critical alerts (immediate notification)
- alert: ServiceDown
  expr: 'up{job="django"} == 0'
  for: 1m
  severity: critical

- alert: DatabaseDown
  expr: 'up{job="postgres"} == 0'
  for: 1m
  severity: critical

# Warning alerts (aggregated)
- alert: HighCPUUsage
  expr: 'rate(cpu_usage[5m]) > 80'
  for: 5m
  severity: warning

- alert: DiskSpaceLow
  expr: 'disk_available_percent < 10'
  for: 10m
  severity: warning
```

---

## Troubleshooting

### Prometheus Not Scraping Metrics

**Check scrape targets:**

```
Prometheus UI → Status → Targets
```

**Verify metrics endpoint:**

```bash
curl http://localhost:8000/metrics/
```

**Check Prometheus logs:**

```bash
docker logs pharmacy_prometheus
```

### Grafana Data Source Connection Failed

**Verify Prometheus URL:**

```
Data Sources → Prometheus → URL
http://prometheus:9090  (Docker internal)
```

**Test connection:**

```
Data Sources → Prometheus → Save & test
```

### No Data in Grafana Dashboard

**Check metric names:**

```
Explore → Metrics explorer → Type metric name
```

**Verify scrape interval:**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
```

Allow 15-30 seconds for initial data collection.

### High Memory Usage by Prometheus

**Reduce retention period:**

```yaml
# prometheus.yml
command:
  - '--storage.tsdb.retention.time=7d'  # Default: 15d
```

**Remove unused metrics:**

```yaml
# Metric relabeling
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'go_.*|process_.*'
    action: drop
```

---

## Summary

OnlinePharmacy monitoring stack provides:

- **Real-time metrics** via Prometheus (15-second collection)
- **Interactive dashboards** via Grafana
- **Custom application metrics** (orders, payments, inventory)
- **Alert rules** for critical conditions
- **Structured logging** for debugging
- **Production-grade** configuration with persistent storage

### Quick Reference

| Component | Purpose | Access |
|-----------|---------|--------|
| Prometheus | Metrics collection | `http://localhost:9090` |
| Grafana | Visualization | `http://localhost:3000` |
| `/metrics/` | Django metrics export | `http://localhost:8000/metrics/` |
| prometheus.yml | Configuration | `./prometheus.yml` |
| Alert rules | Alerting logic | `./prometheus_alert_rules.yml` |

### Key Metrics to Monitor

- **Request rate** (`rate(http_requests_total[5m])`)
- **Error rate** (`rate(http_requests_total{status=~"5.."}[5m])`)
- **P95 latency** (`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`)
- **Database queries/sec** (`rate(django_db_queries_total[1m])`)
- **Cache hit ratio** (`rate(django_cache_hits_total[5m]) / (... + rate(django_cache_misses_total[5m]))`)
- **Active orders** (`active_orders`)
- **Payment failures** (`rate(payments_failed_total[5m])`)

---

## Files & Configuration

Key monitoring files:
- `prometheus.yml` — Prometheus scrape configuration
- `prometheus_alert_rules.yml` — Alert definitions
- `prometheus_recording_rules.yml` — Pre-computed metrics
- `grafana/provisioning/` — Dashboard provisioning
- `config/settings.py` — Django Prometheus middleware
- `pharmacy/metrics.py` — Custom application metrics
- `docker-compose.yml` — Service definitions

All monitoring is optional but recommended for production deployments.
