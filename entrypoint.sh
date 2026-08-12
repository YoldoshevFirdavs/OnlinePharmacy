#!/bin/sh

# Bazani kutish
echo "Bazani kutilmoqda..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Baza tayyor!"

# Migratsiyalar
python manage.py migrate
python manage.py collectstatic --noinput

# Asosiy buyruqni ishga tushirish (CMD dan keladi)
exec "$@"