from django.contrib import admin

from .models.medicine import Category, Medicine
from .models.misc import (
    BotInlineButton,
    BotMenuStep,
    ContactMessage,
    FlashSale,
    MedicineImage,
    Review,
    SiteConfiguration,
)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return self.model.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "stock", "is_active", "average_rating", "reviews_count"]
    list_filter = ["is_active", "category"]
    search_fields = ["name"]
    list_per_page = 50
    list_max_show_all = 50  # Limit "Show all" to prevent loading all records
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images")


class BotInlineButtonInline(admin.TabularInline):
    model = BotInlineButton
    extra = 1


@admin.register(BotMenuStep)
class BotMenuStepAdmin(admin.ModelAdmin):
    list_display = ["status_key", "text_uz", "created_at"]
    inlines = [BotInlineButtonInline]


@admin.register(BotInlineButton)
class BotInlineButtonAdmin(admin.ModelAdmin):
    list_display = ["title_uz", "callback_id", "menu_step", "row_number", "sort_order"]
    list_filter = ["menu_step"]


admin.site.register(MedicineImage)
admin.site.register(Review)
admin.site.register(FlashSale)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "created_at", "is_read", "replied"]
    list_filter = ["is_read", "replied", "created_at"]
    search_fields = ["name", "email", "message"]
    readonly_fields = ["name", "email", "message", "created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Contact Info", {"fields": ("name", "email")}),
        ("Message", {"fields": ("message",)}),
        ("Status", {"fields": ("is_read", "replied")}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Admin can update is_read and replied, but not name/email/message
        if request.method == "POST" and obj:
            # Allow partial updates for is_read and replied
            return True
        return obj is None  # Allow change form to load
