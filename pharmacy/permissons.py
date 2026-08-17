from rest_framework import permissions

from users.models import Seller


class IsVerifiedSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        # FIXED: Use Seller.objects.filter() instead of role field check
        if request.user and request.user.is_authenticated:
            try:
                seller = Seller.objects.get(user=request.user)
                return seller.is_verified
            except Seller.DoesNotExist:
                return False
        return False

    def has_object_permission(self, request, view, obj):
        # FIXED: Use Seller.objects.filter() instead of role field check
        if request.user and request.user.is_authenticated:
            try:
                seller = Seller.objects.get(user=request.user)
                return (
                    seller.is_verified
                    and hasattr(obj, "seller")
                    and obj.seller == seller
                )
            except Seller.DoesNotExist:
                return False
        return False
