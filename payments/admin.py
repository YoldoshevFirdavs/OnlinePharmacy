from django.contrib import admin

from .models import Salary


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = (
        "driver",
        "amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "driver")
    search_fields = (
        "driver__user__full_name",
        "driver__user__phone_number",
    )
    raw_id_fields = ("driver",)
