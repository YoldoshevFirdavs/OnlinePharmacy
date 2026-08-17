# Device Fingerprint Ban & Rate Limiting System

## Overview

A comprehensive device fingerprint-based ban and rate limiting system for the OnlinePharmacy Django project. This system provides enhanced security through device identification, rate limiting, and ban management capabilities.

## Features

### 🔐 Security Features
- **Device Fingerprinting**: Deterministic browser fingerprinting using multiple data points
- **Rate Limiting**: Per-fingerprint request rate limiting (default: 10 req/sec)
- **IP Blocking**: Temporary IP blocks after rate limit violations
- **Main Page Protection**: Special rate limiting for main page refresh attempts
- **Cache-Based Storage**: Redis-backed ban storage with TTL support
- **Admin Management**: Web interface for ban management and statistics

### 🛡️ Ban System
- **Fingerprint Bans**: Ban specific device fingerprints
- **User Bans**: Traditional user-based bans (backward compatible)
- **Temporary Bans**: Time-limited bans with automatic expiration
- **Permanent Bans**: Indefinite bans for severe violations
- **Automatic Cleanup**: Management commands for expired ban cleanup

### 📊 Monitoring & Management
- **Statistics Dashboard**: View ban statistics and active restrictions
- **Admin API**: RESTful endpoints for ban management
- **Management Commands**: CLI tools for maintenance and monitoring
- **Audit Logging**: Comprehensive logging of all ban activities
- **Cross-Platform Scripts**: Automated cleanup tools for Unix and Windows

## Architecture

### Components

1. **Client-Side (JavaScript)**
   - `static/js/device-fingerprint.js`: Fingerprint generation and cookie management
   - Browser property collection (User Agent, Canvas, WebGL, etc.)
   - Secure cookie storage with SameSite protection
   - Automatic header injection for AJAX requests

2. **Server-Side (Python/Django)**
   - `config/middleware.py`: DeviceFingerprintMiddleware for request processing
   - `users/services.py`: BanService for ban management operations
   - `dashboard/admin_api_views.py`: Admin REST API endpoints
   - `dashboard/views.py`: Enhanced not_allowed view with fingerprint info

3. **Management Tools**
   - `users/management/commands/unban_expired.py`: Cleanup expired bans
   - `users/management/commands/fingerprint_ban_cleanup.py`: Advanced fingerprint management
   - `scripts/cleanup_bans.py`: Cross-platform Python automation
   - `scripts/cleanup_bans.sh`: Unix cron automation

4. **Templates & UI**
   - `dashboard/templates/not_allowed.html`: Enhanced ban page with fingerprint details
   - Admin unban functionality with AJAX
   - Real-time fingerprint information display

## Installation & Setup

### 1. Dependencies

The system requires Redis for cache storage:

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Install Python dependencies (already included in requirements.txt)
pip install django-redis
```

### 2. Configuration

Add to your `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Fingerprint Security Settings
FINGERPRINT_RATE_THRESHOLD=10
FINGERPRINT_TEMP_BAN_DURATION=60
FINGERPRINT_IP_BLOCK_DURATION=3600
FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT=20

# Cache & Storage
FINGERPRINT_BAN_CACHE_TTL=86400
FINGERPRINT_USER_MAPPING_TTL=86400

# Security Options
FINGERPRINT_REQUIRE_HTTPS_COOKIE=True
FINGERPRINT_COOKIE_SAMESITE=Lax

# Logging
FINGERPRINT_LOG_LEVEL=WARNING
FINGERPRINT_LOG_BLOCKED_REQUESTS=True
```

### 3. Middleware Setup

The middleware is already configured in `config/settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware
    "config.middleware.DeviceFingerprintMiddleware",
    "config.middleware.BanCheckMiddleware",
    # ... other middleware
]
```

### 4. Database Migration

No database changes required - the system uses cache-based storage.

### 5. Static Files

The fingerprint JavaScript is automatically included in the main template.

## Usage

### Basic Operation

The system works automatically once installed:

1. **Client Fingerprinting**: JavaScript generates device fingerprints on page load
2. **Request Processing**: Middleware checks fingerprints against ban list and rate limits
3. **Ban Enforcement**: Blocked fingerprints are redirected to not_allowed page
4. **Automatic Cleanup**: Expired bans are cleaned up by management commands

### Admin Management

#### View Ban Statistics
```bash
python manage.py fingerprint_ban_cleanup --stats
```

#### Cleanup Expired Bans
```bash
python manage.py unban_expired
```

#### Clear Rate Limits (Emergency)
```bash
python manage.py fingerprint_ban_cleanup --clear-rate-limits
```

#### Check Specific Fingerprint
```bash
python manage.py fingerprint_ban_cleanup --fingerprint abc123...
```

### API Endpoints

#### Admin API (requires staff permission)

- `POST /dashboard/api/admin/unban-fingerprint/`
  ```json
  {"fingerprint": "abc123..."}
  ```

- `POST /dashboard/api/admin/unban-user/<user_id>/`

- `POST /dashboard/api/admin/clear-ip-block/`

- `GET /dashboard/api/admin/fingerprint-ban-status/`

- `GET /dashboard/api/admin/ban-stats/`

### Programmatic Ban Management

```python
from users.services import BanService

# Ban a fingerprint for 1 hour
BanService.ban_by_fp(
    fp='abc123...',
    duration_minutes=60,
    reason='Rate limit exceeded',
    banned_for='rate_limit',
    actor='system'
)

# Check if fingerprint is banned
is_banned = BanService.is_fp_banned('abc123...')

# Unban a fingerprint
BanService.unban_by_fp('abc123...', actor='admin')

# Map fingerprint to user
BanService.map_fp_to_user('abc123...', user)
```

## Automation

### Cron Setup (Unix/Linux)

```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/project/scripts/cleanup_bans.sh cleanup
0 * * * * /path/to/project/scripts/cleanup_bans.sh full  
0 2 * * * /path/to/project/scripts/cleanup_bans.sh reset
```

### Windows Task Scheduler

```bash
# Use Python script for Windows
python scripts/cleanup_bans.py cleanup
python scripts/cleanup_bans.py full
python scripts/cleanup_bans.py reset
```

### Docker Integration

```yaml
# docker-compose.yml
services:
  web:
    # ... other config
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  cleanup:
    build: .
    command: python scripts/cleanup_bans.py full
    depends_on:
      - redis
    # Schedule with cron or external scheduler
```

## Configuration Reference

### Rate Limiting Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `FINGERPRINT_RATE_THRESHOLD` | 10 | Requests per second per fingerprint |
| `FINGERPRINT_TEMP_BAN_DURATION` | 60 | Ban duration in minutes |
| `FINGERPRINT_IP_BLOCK_DURATION` | 3600 | IP block duration in seconds |
| `FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT` | 20 | Main page requests per hour |

### Cache Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `FINGERPRINT_BAN_CACHE_TTL` | 86400 | Ban cache TTL in seconds |
| `FINGERPRINT_USER_MAPPING_TTL` | 86400 | User mapping TTL in seconds |
| `FINGERPRINT_CLEANUP_BATCH_SIZE` | 100 | Cleanup batch size |

### Security Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `FINGERPRINT_REQUIRE_HTTPS_COOKIE` | True | Require HTTPS for cookies |
| `FINGERPRINT_COOKIE_SAMESITE` | Lax | Cookie SameSite policy |
| `FINGERPRINT_HEADER_NAME` | Authorization-Fingerprint | HTTP header name |

## Testing

### Run All Tests
```bash
python test_runner.py
```

### Run Specific Test Types
```bash
# Python/Django tests only
python manage.py test users.tests.test_fingerprint_system config.tests.test_middleware

# JavaScript tests (in browser console)
# Open browser dev tools and load: static/js/tests/device-fingerprint.test.js

# Integration tests
python test_runner.py
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Monitoring & Troubleshooting

### Log Analysis

Check Django logs for fingerprint activities:
```bash
grep "FINGERPRINT\|BAN_FP" logs/django.log
```

### Redis Inspection

```bash
# Connect to Redis
redis-cli

# List fingerprint keys
KEYS ban_fp:*
KEYS rate_fp:*
KEYS ip_block:*

# Check specific ban
GET ban_fp:abc123...
```

### Performance Monitoring

Monitor Redis memory usage and request latency:
```bash
redis-cli INFO memory
redis-cli SLOWLOG GET 10
```

### Common Issues

1. **High Redis Memory Usage**
   - Increase cleanup frequency
   - Reduce cache TTL values
   - Monitor for memory leaks

2. **False Positive Bans**
   - Review rate limiting thresholds
   - Check for shared devices/networks
   - Implement whitelist for trusted fingerprints

3. **Fingerprint Collisions**
   - Very rare with SHA256 hashing
   - Monitor for unusual ban patterns
   - Add more entropy sources if needed

## Security Considerations

### Privacy Protection
- Fingerprints are hashed, not storing raw browser data
- No personally identifiable information collected
- Compliant with privacy regulations (GDPR, etc.)

### Attack Mitigation
- Rate limiting prevents DoS attacks
- IP blocking adds network-level protection
- Fingerprint rotation resistance through multiple data points
- Admin audit logging for accountability

### Production Hardening
- Use HTTPS-only cookies in production
- Implement proper Redis authentication
- Monitor for suspicious fingerprint patterns
- Regular security audits and updates

## Performance Optimization

### Redis Optimization
```redis
# redis.conf optimizations
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
```

### Django Settings
```python
# Cache optimization
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
        },
    }
}
```

## Contributing

### Development Setup
1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure Redis connection
4. Run tests: `python test_runner.py`
5. Make changes and add tests

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Add docstrings for all public functions
- Write tests for new features

### Pull Request Process
1. Fork repository
2. Create feature branch
3. Add tests for changes
4. Update documentation
5. Submit pull request

## License

This fingerprint ban system is part of the OnlinePharmacy project and follows the same licensing terms.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review system logs
3. Run diagnostic commands
4. Create GitHub issue with details

---

**Last Updated**: August 2026  
**Version**: 1.0.0  
**Compatibility**: Django 4.x, Redis 6.x+, Python 3.8+