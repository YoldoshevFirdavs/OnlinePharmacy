from django.contrib import admin

from .models import (
    CustomUser,
    Deliverer,
    Operator,
    PayrollStats,
    SalaryRecord,
    Seller,
    SubscribedUser,
    TelegrambotUser,
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "full_name", "is_verified", "is_staff", "role"]
    search_fields = ["phone_number", "full_name"]


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = [
        "shop_name",
        "user",
        "is_verified",
        "rating",
        "balance",
        "created_at",
    ]
    list_filter = ["is_verified", "created_at"]
    search_fields = ["shop_name", "user__phone_number", "licence_number"]
    actions = ["verify_sellers"]

    def verify_sellers(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Tanlangan sotuvchilar muvaffaqiyatli tasdiqlandi!")

    verify_sellers.short_description = "Sotuvchilarni tasdiqlash"


@admin.register(TelegrambotUser)
class TelegrambotUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "first_name",
        "bot_status",
        "last_status",
        "language",
    )
    list_filter = ("language", "bot_status", "last_status")
    search_fields = ("telegram_id", "username", "first_name")


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "is_busy", "is_active", "created_at")
    list_filter = ("is_busy", "is_active")
    search_fields = ("name", "phone_number")
    actions = ["mark_as_busy", "mark_as_free"]

    def mark_as_busy(self, request, queryset):
        queryset.update(is_busy=True)
        self.message_user(request, "Tanlangan operatorlar band deb belgilandi.")

    mark_as_busy.short_description = "Operatorlarni band qilish"

    def mark_as_free(self, request, queryset):
        queryset.update(is_busy=False)
        self.message_user(request, "Tanlangan operatorlar bo'sh deb belgilandi.")

    mark_as_free.short_description = "Operatorlarni bo'sh qilish"


@admin.register(SubscribedUser)
class SubscribedUserAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "is_verified", "subscribed_at")
    search_fields = ("email", "user__email", "user__phone_number")
    list_filter = ("is_verified",)


@admin.register(Deliverer)
class DelivererAdmin(admin.ModelAdmin):
    list_display = (
        "user_email",
        "phone_number",
        "status",
        "rate_per_hour",
        "created_at",
    )
    search_fields = ("user__email", "user__full_name", "phone_number")
    list_filter = ("status",)
    autocomplete_fields = ("user",)

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = (
        "deliverer",
        "period_start",
        "period_end",
        "gross_amount",
        "net_amount",
        "status",
        "paid_at",
    )
    list_filter = ("status", "period_start", "period_end")
    search_fields = (
        "deliverer__user__email",
        "deliverer__phone_number",
        "stripe_payment_id",
    )
    date_hierarchy = "period_end"


@admin.register(PayrollStats)
class PayrollStatsAdmin(admin.ModelAdmin):
    list_display = ("month", "year", "total_gross", "total_net", "total_payouts")
    list_filter = ("year", "month")
    search_fields = ("year",)
