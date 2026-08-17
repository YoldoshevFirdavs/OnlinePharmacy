#!/usr/bin/env python
import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from users.models import Seller

U = get_user_model()

# Find an admin user or any user
admin_users = U.objects.filter(is_staff=True)
regular_users = U.objects.filter(is_staff=False)

print("=" * 60)
print("ADMIN USERS:")
print("=" * 60)
for u in admin_users[:3]:
    has_seller = Seller.objects.filter(user=u).exists()
    print(
        f"ID: {u.pk} | Email: {u.email} | Role: {u.role} | is_staff: {u.is_staff} | is_superuser: {u.is_superuser} | has_seller: {has_seller}"
    )

print("\n" + "=" * 60)
print("REGULAR USERS (FIRST 5):")
print("=" * 60)
for u in regular_users[:5]:
    has_seller = Seller.objects.filter(user=u).exists()
    print(
        f"ID: {u.pk} | Email: {u.email} | Role: {u.role} | is_staff: {u.is_staff} | is_superuser: {u.is_superuser} | has_seller: {has_seller}"
    )

print("\n" + "=" * 60)
print("TOTAL COUNTS:")
print("=" * 60)
print(f"Total Users: {U.objects.count()}")
print(f"Admin Users: {admin_users.count()}")
print(f"Regular Users: {regular_users.count()}")
print(f"Sellers: {Seller.objects.count()}")
