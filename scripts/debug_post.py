import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings_test')
django.setup()
from django.test import Client
c=Client()
r=c.post('/api/v1/users/subscribers/', data='{"email":"user@example.com"}', content_type='application/json')
print('STATUS', r.status_code)
print(r.content)
print(r.headers if hasattr(r, 'headers') else {})
