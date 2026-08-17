from rest_framework import serializers

from .models import Salary


class SalarySerializer(serializers.ModelSerializer):
    driver_full_name = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Salary
        fields = [
            "id",
            "amount",
            "currency",
            "status",
            "driver_full_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "amount",
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


class AdminSalaryCreateSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
