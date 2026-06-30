from rest_framework import permissions

class IsVerifiedSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'seller'):
            return request.user.seller.is_verified
        return False