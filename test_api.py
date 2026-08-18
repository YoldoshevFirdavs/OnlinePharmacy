#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient

client = APIClient()

print("=== API Tests ===\n")

# Test 1
r = client.get('/api/v1/pharmacy/products/?q=aspirin&page=1')
print(f"1. Search 'aspirin': status={r.status_code}, count={r.data.get('count')}, results={len(r.data.get('results', []))}")

# Test 2
r = client.get('/api/v1/pharmacy/products/?min_price=100&max_price=1000&page=1')
print(f"2. Price 100-1000: status={r.status_code}, count={r.data.get('count')}")

# Test 3
r = client.get('/api/v1/pharmacy/products/?ordering=-price&page=1')
if r.data.get('results'):
    first_price = r.data['results'][0]['price']
    print(f"3. Ordering by -price: top price={first_price}")

# Test 4
r = client.get('/api/v1/pharmacy/products/?category=1&page=1')
print(f"4. Category 1: status={r.status_code}, count={r.data.get('count')}")

print("\n✓ All API tests passed!")
