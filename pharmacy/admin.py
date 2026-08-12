from django.contrib import admin

from .models.medicine import Category, Medicine
from .models.misc import (
    BotInlineButton,
    BotMenuStep,
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
    list_display = ["name", "price", "stock", "is_active"]
    list_filter = ["is_active", "category"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


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
