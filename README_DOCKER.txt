
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║          ✅ Docker Production Setup - Complete & Ready ✅                 ║
║                                                                            ║
║             OnlinePharmacy Django App in Production                       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

WHAT WAS DONE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ docker-compose.prod.yml UPDATED
   ├─ Now uses HOST PATHS (not Docker volumes)
   ├─ /app/staticfiles    → /home/ec2-user/OnlinePharmacy/staticfiles
   ├─ /app/media          → /home/ec2-user/OnlinePharmacy/media
   └─ PostgreSQL data     → /home/ec2-user/OnlinePharmacy/postgres_data

✅ 4 NEW DOCUMENTATION FILES CREATED

✅ 1 SETUP SCRIPT CREATED (Automated host preparation)

DOCUMENTATION FILES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. README_DOCKER.txt (This file)
   ├─ Quick overview
   └─ Links to other documentation

2. DOCKER_QUICK_REFERENCE.txt ⭐ START HERE
   ├─ Copy-paste commands
   ├─ Common operations
   ├─ Quick troubleshooting
   └─ 5-10 minute read

3. DOCKER_DEPLOYMENT_SUMMARY.txt
   ├─ Complete summary
   ├─ How it works (data flow)
   ├─ Migration path
   ├─ File structure
   └─ 10-15 minute read

4. DOCKER_PROD_DEPLOYMENT.md
   ├─ Step-by-step guide
   ├─ All available commands
   ├─ Detailed troubleshooting
   ├─ Monitoring & maintenance
   └─ 30+ minute comprehensive guide

5. DOCKER_HOST_SETUP.sh (Executable)
   ├─ Automated setup script
   ├─ Creates directories
   ├─ Sets permissions
   └─ Run: bash DOCKER_HOST_SETUP.sh

6. NGINX_SETUP.md (Optional)
   ├─ Nginx configuration
   ├─ Performance optimization
   ├─ SSL/TLS setup
   └─ Only if using separate Nginx

KEY CHANGES EXPLAINED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEFORE (Old docker-compose):
  volumes:
    - static_volume:/app/staticfiles    ← Docker managed volume
    - media_volume:/app/media           ← Docker managed volume

AFTER (New docker-compose):
  volumes:
    - /home/ec2-user/OnlinePharmacy/staticfiles:/app/staticfiles
    - /home/ec2-user/OnlinePharmacy/media:/app/media

WHAT THIS MEANS:
  ✅ Files written inside Docker are visible on EC2 host
  ✅ You can SSH and see all files directly
  ✅ Nginx can serve directly from host filesystem
  ✅ Backup is just copy /home/ec2-user/OnlinePharmacy/
  ✅ No Docker volume export/import needed

BENEFITS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. SIMPLE BACKUPS
   Backup:  cp -r /home/ec2-user/OnlinePharmacy /backups/
   Restore: cp -r /backups/OnlinePharmacy /home/ec2-user/

2. EASY DEBUGGING
   SSH to EC2 and look at files directly
   No need for: docker cp, docker exec, etc.

3. BETTER PERFORMANCE
   Nginx serves static files directly (not through Django)
   Gunicorn handles API requests only

4. SCALABILITY
   Multiple containers can share same files
   Files survive container restart

5. VISIBILITY
   All uploads, logs, and generated files on host
   Easy to monitor disk usage

QUICK START (5 MINUTES):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. SSH to EC2:
   ssh -i your-key.pem ec2-user@your-ec2-ip

2. Go to project:
   cd /home/ec2-user/OnlinePharmacy

3. Prepare directories:
   bash DOCKER_HOST_SETUP.sh

4. Edit environment:
   nano .env.prod
   Update: DB_NAME, DB_USER, DB_PASSWORD, SECRET_KEY, ALLOWED_HOSTS

5. Start Docker:
   docker compose -f docker-compose.prod.yml build
   docker compose -f docker-compose.prod.yml up -d

6. Initialize:
   docker compose -f docker-compose.prod.yml exec web python manage.py migrate
   docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
   docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

7. Verify:
   curl http://localhost:8000/api/v1/health/
   ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/

Done! ✅

DIRECTORY STRUCTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/home/ec2-user/OnlinePharmacy/
├── docker-compose.prod.yml      ← Updated configuration
├── .env.prod                     ← Your environment (KEEP SECRET!)
├── Dockerfile
├── entrypoint.sh
│
├── staticfiles/                  ← Shared with Docker ✓
│   └── static/
│       ├── admin/
│       ├── css/
│       ├── js/
│       └── images/
│
├── media/                        ← Shared with Docker ✓
│   ├── uploads/
│   │   └── avatars/
│   └── ...
│
├── postgres_data/                ← Shared with Docker ✓
│   ├── base/
│   ├── global/
│   └── ...
│
├── nginx/                        ← Optional (if using Nginx)
│   └── nginx.conf
│
├── README_DOCKER.txt             ← This file
├── DOCKER_QUICK_REFERENCE.txt    ← Quick commands
├── DOCKER_DEPLOYMENT_SUMMARY.txt ← Full summary
├── DOCKER_PROD_DEPLOYMENT.md     ← Complete guide
├── DOCKER_HOST_SETUP.sh          ← Setup script
└── NGINX_SETUP.md                ← Nginx guide (optional)

HOW VOLUME MOUNTS WORK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example: Django saves a file

1. Django code inside container:
   with open('/app/media/uploads/avatars/user1.jpg', 'wb') as f:
       f.write(file_data)

2. Docker volume mount maps:
   /app/media/ (inside Docker)
   → /home/ec2-user/OnlinePharmacy/media/ (on EC2 host)

3. File ends up here on host:
   /home/ec2-user/OnlinePharmacy/media/uploads/avatars/user1.jpg

4. You can see it:
   ssh into EC2
   ls -la /home/ec2-user/OnlinePharmacy/media/uploads/avatars/
   → user1.jpg is there! ✓

ENVIRONMENT VARIABLES (.env.prod):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUIRED:
  DB_NAME=onlinepharmacy_prod
  DB_USER=pharmacy_user
  DB_PASSWORD=your-strong-password-16-chars-min
  POSTGRES_DB=onlinepharmacy_prod
  POSTGRES_USER=pharmacy_user
  POSTGRES_PASSWORD=your-strong-password-16-chars-min

DJANGO SECURITY:
  DEBUG=False
  SECRET_KEY=very-long-random-string-64-chars-min
  ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,ip-address
  SECURE_SSL_REDIRECT=True
  SESSION_COOKIE_SECURE=True
  CSRF_COOKIE_SECURE=True

PATHS:
  MEDIA_ROOT=/app/media
  MEDIA_URL=/media/
  STATIC_ROOT=/app/staticfiles
  STATIC_URL=/static/

OTHER:
  REDIS_URL=redis://redis:6379/0
  (+ optional: EMAIL, TELEGRAM, etc.)

COMMON COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View logs:
  docker compose -f docker-compose.prod.yml logs -f web

Check status:
  docker compose -f docker-compose.prod.yml ps

Collect static files:
  docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

Create admin user:
  docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

Restart services:
  docker compose -f docker-compose.prod.yml restart

Stop all:
  docker compose -f docker-compose.prod.yml down

Verify files:
  ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/
  ls -la /home/ec2-user/OnlinePharmacy/media/

See full list: DOCKER_QUICK_REFERENCE.txt

TESTING DEPLOYMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After starting docker, run these tests:

1. Containers running?
   docker compose ps
   → Should show all services as "Up"

2. API responding?
   curl http://localhost:8000/api/v1/health/
   → Should return 200 OK

3. Static files?
   curl -I http://localhost:8000/static/css/main.css
   → Should return 200 OK

4. Admin accessible?
   curl -I http://localhost:8000/admin/
   → Should return 302 (redirect to login)

5. Files on host?
   ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/
   → Should see admin/, css/, js/, images/ directories

If any fail → See DOCKER_PROD_DEPLOYMENT.md Troubleshooting section

NGINX (OPTIONAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To use Nginx for better performance:

1. Create nginx/nginx.conf (see NGINX_SETUP.md)

2. Uncomment nginx service in docker-compose.prod.yml

3. Restart Docker:
   docker compose -f docker-compose.prod.yml up -d

4. Test:
   curl -I http://localhost/static/css/main.css
   curl -I http://localhost/api/v1/health/

See NGINX_SETUP.md for complete configuration.

BACKUP & RECOVERY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BACKUP ALL DATA:
  1. Stop containers:
     docker compose -f docker-compose.prod.yml down

  2. Backup everything:
     tar -czf /backups/pharmacy_backup_$(date +%Y%m%d).tar.gz \
       /home/ec2-user/OnlinePharmacy/

  3. Store backup on S3, Google Cloud, or external drive

RESTORE FROM BACKUP:
  1. Stop containers:
     docker compose -f docker-compose.prod.yml down -v

  2. Restore files:
     tar -xzf /backups/pharmacy_backup_20260829.tar.gz -C /

  3. Start containers:
     docker compose -f docker-compose.prod.yml up -d

  4. Verify:
     docker compose -f docker-compose.prod.yml ps

TROUBLESHOOTING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Container won't start
  SOLUTION: docker compose logs web
  Then check .env.prod for errors

PROBLEM: Static files not found (404)
  SOLUTION:
    1. docker compose exec web python manage.py collectstatic --noinput
    2. ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/
    3. chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles

PROBLEM: Media uploads not working
  SOLUTION:
    1. mkdir -p /home/ec2-user/OnlinePharmacy/media
    2. chmod -R 755 /home/ec2-user/OnlinePharmacy/media
    3. docker compose restart web

PROBLEM: Database connection error
  SOLUTION:
    1. docker compose logs db
    2. Check .env.prod - DB_PASSWORD must match POSTGRES_PASSWORD

For more: DOCKER_PROD_DEPLOYMENT.md → Troubleshooting

NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Read DOCKER_QUICK_REFERENCE.txt (copy-paste commands)

2. Read DOCKER_DEPLOYMENT_SUMMARY.txt (understand how it works)

3. Follow DOCKER_PROD_DEPLOYMENT.md (step-by-step guide)

4. Run setup: bash DOCKER_HOST_SETUP.sh

5. Deploy: docker compose build && up -d

6. Test: Run the 7 verification tests above

7. Monitor: Keep an eye on logs and disk space

PRODUCTION CHECKLIST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before deployment:
  [ ] .env.prod created
  [ ] SECRET_KEY is long & random
  [ ] DB_PASSWORD is strong
  [ ] DEBUG=False
  [ ] ALLOWED_HOSTS set correctly

After deployment:
  [ ] All containers running (docker compose ps)
  [ ] API responds (curl localhost:8000/api/v1/health/)
  [ ] Static files work
  [ ] Media uploads work
  [ ] Admin accessible
  [ ] No error messages in logs
  [ ] Backups configured
  [ ] Monitoring set up

STATUS: ✅ COMPLETE & READY FOR PRODUCTION

Start with DOCKER_QUICK_REFERENCE.txt (5-minute read + deployment)

Questions? See DOCKER_PROD_DEPLOYMENT.md

═════════════════════════════════════════════════════════════════════════════

