from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings
import secrets
from datetime import timedelta
import hashlib

from .models import CustomUser, Seller, Deliverer, SalaryRecord, PayrollStats, TelegrambotUser, Operator, SubscribedUser, OnboardToken


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'full_name', 'is_verified', 'is_staff', 'role']
    search_fields = ['phone_number', 'full_name']


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['shop_name', 'user', 'is_verified', 'rating', 'balance', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['shop_name', 'user__phone_number', 'licence_number']
    actions = ['verify_sellers']

    def verify_sellers(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Tanlangan sotuvchilar muvaffaqiyatli tasdiqlandi!")
    verify_sellers.short_description = "Sotuvchilarni tasdiqlash"


@admin.register(TelegrambotUser)
class TelegrambotUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'bot_status', 'last_status', 'language')
    list_filter = ('language', 'bot_status', 'last_status')
    search_fields = ('telegram_id', 'username', 'first_name')


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'is_busy', 'is_active', 'created_at')
    list_filter = ('is_busy', 'is_active')
    search_fields = ('name', 'phone_number')
    actions = ['mark_as_busy', 'mark_as_free']

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
    list_display = ('email', 'user', 'is_verified', 'subscribed_at')
    search_fields = ('email', 'user__email', 'user__phone_number')
    list_filter = ('is_verified',)


@admin.register(Deliverer)
class DelivererAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'phone_number', 'status', 'rate_per_hour', 'created_at', 'onboarding_link_display')
    search_fields = ('user__email', 'user__full_name', 'phone_number')
    list_filter = ('status',)
    raw_id_fields = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def save_model(self, request, obj, form, change):
        # Handle new Deliverer creation
        if not obj.pk:
            # Set user role and status
            obj.user.role = 'deliverer'
            obj.user.is_staff = False
            obj.user.is_active = True
            obj.user.save()

            # Generate one-time token for onboarding
            onboarding_token_str = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(onboarding_token_str.encode()).hexdigest()
            expires = timezone.now() + timedelta(hours=24)
            
            OnboardToken.objects.create(user=obj.user, token_hash=token_hash, expires_at=expires)

            # Construct onboarding link
            onboarding_link = request.build_absolute_uri(
                reverse('deliverer_onboarding_verify') + f'?token={onboarding_token_str}&deliverer_id={obj.id}'
            )

            try:
                send_deliverer_onboarding_email.delay(obj.user.email, onboarding_link)
                self.message_user(request, f"Deliverer {obj.user.email} created. Onboarding email sent.")
            except Exception as e:
                self.message_user(request, f"Error sending onboarding email: {e}", level='error')
        super().save_model(request, obj, form, change)

    def onboarding_link_display(self, obj):
        if obj.status == 'pending':
            # Link sent via email, not directly accessible from admin
            return "Email orqali yuborilgan"
        return "N/A"
    onboarding_link_display.short_description = 'Onboarding Link'


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = ('deliverer', 'period_start', 'period_end', 'gross_amount', 'net_amount', 'status', 'paid_at')
    list_filter = ('status', 'period_start', 'period_end')
    search_fields = ('deliverer__user__email', 'deliverer__phone_number', 'stripe_payment_id')
    date_hierarchy = 'period_end'


@admin.register(PayrollStats)
class PayrollStatsAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'total_gross', 'total_net', 'total_payouts')
    list_filter = ('year', 'month')
    search_fields = ('year',)