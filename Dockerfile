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
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko'chirib o'tkazamiz
COPY . /app/

# Portlarni ochamiz
EXPOSE 8000
# NOTE: SSL certs are mounted via docker-compose volumes, not baked into the image.
# Baking secrets into images is a security risk and breaks builds when certs are missing.
