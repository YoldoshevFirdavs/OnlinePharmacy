from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pharmacy.models.history import CustomerUserHistory
from pharmacy.serializers.history import CustomerUserHistorySerializer


class UserHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for customer user history.
    Allows users to view their own history (immutable audit log).
    
    Endpoints:
    - GET /api/v1/user/history/ - List user's own history (paginated, 50 per page)
    - GET /api/v1/user/history/<id>/ - Retrieve specific history entry
    """
    
    serializer_class = CustomerUserHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        """Only return history for the authenticated user"""
        return CustomerUserHistory.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def log_action(self, request):
        """
        Log a user action (called by frontend after viewing product, add to cart, etc.)
        
        Body:
        {
            "action": "view_product",  # Required
            "product_id": 123,  # Optional
            "seller_id": 456,  # Optional
            "meta": {...}  # Optional
        }
        """
        action = request.data.get('action')
        product_id = request.data.get('product_id')
        seller_id = request.data.get('seller_id')
        meta = request.data.get('meta', {})
        
        if not action:
            return Response(
                {'error': 'action is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get IP address
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            history_entry = CustomerUserHistory(
                user=request.user,
                action=action,
                meta=meta,
                ip_address=ip_address,
                user_agent=user_agent[:500],  # Limit to 500 chars
            )
            
            # Add product if provided
            if product_id:
                from pharmacy.models.medicine import Medicine
                try:
                    history_entry.product = Medicine.objects.get(id=product_id)
                except Medicine.DoesNotExist:
                    pass
            
            # Add seller if provided
            if seller_id:
                from users.models import Seller
                try:
                    history_entry.seller = Seller.objects.get(id=seller_id)
                except Seller.DoesNotExist:
                    pass
            
            history_entry.save()
            
            serializer = self.get_serializer(history_entry)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
