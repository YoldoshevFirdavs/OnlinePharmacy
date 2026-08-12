from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "amount", "status", "created_at"]
    list_filter = ["status"]  # Search with its status. Example delivered, shipped ...
