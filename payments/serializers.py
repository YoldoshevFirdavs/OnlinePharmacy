from rest_framework import serializers

from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    driver_full_name = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Payout
        fields = [
            "id",
            "amount_gross",
            "net_amount",
            "currency",
            "status",
            "driver_full_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "amount_gross",
            "net_amount",
            "currency",
            "status",
            "driver_full_name",
            "created_at",
        ]

    def get_driver_full_name(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.full_name
        return None

    def get_currency(self, obj):
        return "usd"


class AdminPayoutCreateSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    amount_gross = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
