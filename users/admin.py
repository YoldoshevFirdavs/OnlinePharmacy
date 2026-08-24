from django.contrib import admin

from .models import CustomUser, DeliveryDriver, Operator, Seller, SubscribedUser, TelegrambotUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_display_name",
        "email",
        "role",
        "is_active",
        "date_joined",
    ]
    search_fields = ["full_name", "email", "phone_number"]


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


@admin.register(DeliveryDriver)
class DeliveryDriverAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "status",
        "created_at",
    )
    search_fields = ("user__email", "user__full_name", "phone_number")
    list_filter = ("status",)
    autocomplete_fields = ("user",)
