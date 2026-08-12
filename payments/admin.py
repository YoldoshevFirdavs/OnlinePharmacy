from django.contrib import admin

from .models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "driver",
        "amount_gross",
        "tax_amount",
        "net_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "driver")
    search_fields = (
        "driver__user__full_name",
        "driver__user__phone_number",
        "stripe_transfer_id",
    )
    raw_id_fields = ("driver",)


# import openpyxl
# from django.http import HttpResponse
# from io import BytesIO
#
# def export_payouts_to_xlsx(modeladmin, request, queryset):
#     wb = openpyxl.Workbook()
#     ws = wb.active
#     ws.append(['id','driver','amount_gross','tax_amount','commission_amount','amount_net','status','created_at'])
#     for p in queryset:
#         ws.append([p.id, str(p.driver), float(p.amount_gross), float(p.tax_amount), float(p.commission_amount), float(p.amount_net), p.status, p.created_at.isoformat()])
#     stream = BytesIO()
#     wb.save(stream)
#     stream.seek(0)
#     response = HttpResponse(stream.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#     response['Content-Disposition'] = 'attachment; filename=payouts.xlsx'
#     return response
