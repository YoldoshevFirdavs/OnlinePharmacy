from rest_framework import serializers
from pharmacy.models.history import CustomerUserHistory
from pharmacy.models.medicine import Medicine


class CustomerUserHistorySerializer(serializers.ModelSerializer):
    """Serializer for user history audit logs"""
    
    user_id = serializers.IntegerField(read_only=True, source='user.id')
    user_name = serializers.SerializerMethodField(read_only=True)
    product_name = serializers.CharField(read_only=True, source='product.name', allow_null=True)
    seller_name = serializers.CharField(read_only=True, source='seller.shop_name', allow_null=True)
    action_display = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CustomerUserHistory
        fields = [
            'id',
            'user_id',
            'user_name',
            'action',
            'action_display',
            'product_name',
            'seller_name',
            'meta',
            'timestamp',
            'ip_address',
        ]
        read_only_fields = fields
    
    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.phone_number or obj.user.email
    
    def get_action_display(self, obj):
        return obj.get_action_display()
