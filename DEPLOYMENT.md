# Deployment Guide

This project is intended to run behind a reverse proxy with Gunicorn as the WSGI server and Nginx as the entry point.

## EC2 setup

1. Launch an Ubuntu EC2 instance.
2. Install system packages:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv nginx git certbot python3-certbot-nginx
   ```
3. Clone the repository and create a virtual environment.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
5. Create `.env` with production values; never store it in git.

## Gunicorn systemd service

```ini
[Unit]
Description=OnlinePharmacy Gunicorn service
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/OnlinePharmacy
Environment="PATH=/home/ubuntu/OnlinePharmacy/.venv/bin"
ExecStart=/home/ubuntu/OnlinePharmacy/.venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now onlinepharmacy
```

## Nginx site config

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/OnlinePharmacy/staticfiles/;
    }
}
```

## Production steps

```bash
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py check
```

## TLS

Use Certbot when the domain is ready:

```bash
sudo certbot --nginx -d example.com -d www.example.com
```
