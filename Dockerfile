# Python 3.10 tasviridan foydalanamiz
FROM python:3.10-slim

# Terminalda loglarni ko'rib turish uchun
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Ishchi katalogni yaratamiz
WORKDIR /app

# Tizim paketlarini yangilaymiz (PostgreSQL uchun kerakli kutubxonalar)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Pip-ni yangilaymiz va requirements o'rnatamiz
COPY requirements.txt requirements-dev.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Loyiha fayllarini ko'chirib o'tkazamiz
COPY . /app/

# Static files collection: Copy source static files to staticfiles directories
# This ensures all static assets (CSS, JS, images) are available in the container
RUN echo "🎨 Preparing static files directories..." && \
    mkdir -p /app/staticfiles/static && \
    mkdir -p /app/staticfiles && \
    echo "📁 Removing old static files from staticfiles..." && \
    rm -rf /app/staticfiles/static/* && \
    echo "📋 Copying static files from /app/static to /app/staticfiles/static..." && \
    cp -r /app/static/* /app/staticfiles/static/ 2>/dev/null || true && \
    echo "✅ Static files prepared ($(find /app/staticfiles/static -type f | wc -l) files)"

# Portlarni ochamiz
EXPOSE 8000
# NOTE: SSL certs are mounted via docker-compose volumes, not baked into the image.
# Baking secrets into images is a security risk and breaks builds when certs are missing.
