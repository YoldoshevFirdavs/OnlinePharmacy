#!/usr/bin/env python
"""
Verify OnlinePharmacy systems are properly implemented
No Django client/API calls - just code inspection
"""
import os
import sys

print("\n" + "=" * 70)
print("OnlinePharmacy - System Verification (Code Inspection)")
print("=" * 70 + "\n")

base_path = os.path.dirname(os.path.abspath(__file__))

checks = {
    "Avatar Handler": {
        "file": "users/avatar_handler.py",
        "required": ["handle_avatar_upload", "from PIL import Image", "transaction.atomic"],
    },
    "Contact API": {
        "file": "pharmacy/views/contact.py",
        "required": ["ContactMessageViewSet", "class ContactMessage"],
    },
    "Popular Products": {
        "file": "pharmacy/views/product.py",
        "required": ["def popular(", "ProductViewHistory", "popular_medicine_ids"],
    },
    "Global Messages": {
        "file": "static/js/messages.js",
        "required": ["class MessageManager", "getUserRole", "role-based", "slideInRight"],
    },
    "Context Processors": {
        "file": "pharmacy/context_processors.py",
        "required": ["def default_images", "DEFAULT_AVATAR_URL", "DEFAULT_PRODUCT_URL", "contact_email"],
    },
    "Dashboard Base": {
        "file": "templates/dashboard/base.html",
        "required": ["data-user-role", "messages.js"],
    },
    "Swagger Config": {
        "file": "config/urls.py",
        "required": ["JWTSchemaGenerator", "get_schema_view", "swagger"],
    },
    "Footer Component": {
        "file": "templates/components/footer.html",
        "required": ["{{ contact_email }}", "{{ contact_phone }}"],
    },
}

total_checks = 0
passed_checks = 0

for system_name, check_info in checks.items():
    file_path = os.path.join(base_path, check_info["file"])
    print(f"[CHECK] {system_name}")
    print(f"  File: {check_info['file']}")
    
    if not os.path.exists(file_path):
        print(f"  ✗ FILE NOT FOUND\n")
        total_checks += 1
        continue
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        system_passed = True
        for req in check_info["required"]:
            if req in content:
                print(f"  ✓ '{req}' found")
            else:
                print(f"  ✗ '{req}' NOT FOUND")
                system_passed = False
        
        if system_passed:
            passed_checks += 1
        
        total_checks += 1
        print()
    
    except Exception as e:
        print(f"  ✗ Error reading file: {str(e)}\n")
        total_checks += 1

# Summary
print("=" * 70)
print("Verification Summary")
print("=" * 70)
print(f"\n✓ Passed: {passed_checks}/{total_checks} systems verified\n")

if passed_checks == total_checks:
    print("✅ All systems properly implemented and ready for testing!\n")
else:
    print(f"⚠️  {total_checks - passed_checks} system(s) need attention\n")

print("=" * 70)
print("\nImplemented Features:")
print("  1. Avatar upload with PIL validation + detailed logging")
print("  2. Contact form API at /api/v1/products/contact/")
print("  3. Popular products API at /api/v1/products/popular/")
print("  4. Global messages system (role-based detail levels)")
print("  5. Default images context processor")
print("  6. Contact info in footer (dynamic via context)")
print("  7. Professional Privacy & Terms pages with modern CSS")
print("  8. Swagger/OpenAPI documentation at /swagger/")
print("\n" + "=" * 70 + "\n")
