from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, BanRecord, UserActionHistory


@admin.register(UserActionHistory)
class UserActionHistoryAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "description", "ip_address", "timestamp"]
    list_filter = ["action", "timestamp", "user"]
    search_fields = ["user__email", "action", "description", "ip_address"]
    readonly_fields = [
        "timestamp",
        "user",
        "action",
        "description",
        "ip_address",
        "target_type",
        "target_id",
        "metadata",
    ]
    date_hierarchy = "timestamp"

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "ip_address", "timestamp"]
    list_filter = ["action", "timestamp"]
    search_fields = ["user__email", "action", "ip_address"]
    readonly_fields = ["timestamp", "user", "action", "description", "ip_address", "target_type", "target_id", "meta"]
    date_hierarchy = "timestamp"

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BanRecord)
class BanRecordAdmin(admin.ModelAdmin):
    list_display = [
        "identifier",
        "ban_type_badge",
        "created_at",
        "expires_at",
        "attempts",
        "created_by",
        "is_active_badge",
    ]
    list_filter = ["ban_type", "created_by", "is_active", "created_at"]
    search_fields = ["ip", "fingerprint", "reason"]
    readonly_fields = ["created_at", "meta_display"]
    date_hierarchy = "created_at"

    fieldsets = (
        (_("Identifiers"), {"fields": ("ip", "fingerprint", "user")}),
        (_("Ban Info"), {"fields": ("reason", "ban_type", "created_by", "source")}),
        (_("Timing"), {"fields": ("created_at", "expires_at")}),
        (_("Details"), {"fields": ("attempts", "meta_display", "is_active")}),
    )

    actions = ["unban_records", "mark_inactive"]

    def identifier(self, obj):
        """Show every identifier attached to the ban record."""
        identifiers = []
        if obj.user:
            identifiers.append(f"User: {obj.user.email or obj.user_id}")
        if obj.ip:
            identifiers.append(f"IP: {obj.ip}")
        if obj.fingerprint:
            identifiers.append(f"FP: {obj.fingerprint[:20]}...")
        return " | ".join(identifiers) or "Unknown"

    identifier.short_description = _("Identifier")

    def ban_type_badge(self, obj):
        """Color-coded ban type"""
        colors = {
            "temporary": "#FFA500",  # Orange
            "permanent": "#FF0000",  # Red
        }
        color = colors.get(obj.ban_type, "#gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_ban_type_display(),
        )

    ban_type_badge.short_description = _("Type")

    def is_active_badge(self, obj):
        """Color-coded active status"""
        color = "#00AA00" if obj.is_active else "#CCCCCC"
        text = "✓ Active" if obj.is_active else "✗ Inactive"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)

    is_active_badge.short_description = _("Status")

    def meta_display(self, obj):
        """Display JSON metadata"""
        import json

        if obj.meta:
            return format_html("<pre>{}</pre>", json.dumps(obj.meta, indent=2))
        return "-"

    meta_display.short_description = _("Metadata")

    def unban_records(self, request, queryset):
        """Action to unban (mark inactive)"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"✓ {count} ta ban inactive qilindi")

    unban_records.short_description = _("Unban selected records")

    def mark_inactive(self, request, queryset):
        """Mark as inactive"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"✓ {count} ta record inactive qilindi")

    mark_inactive.short_description = _("Mark as inactive")
