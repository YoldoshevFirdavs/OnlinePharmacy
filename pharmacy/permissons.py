from rest_framework import permissions


class IsVerifiedSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.role == "seller":
            try:
                seller_profile = request.user.seller
                return seller_profile.is_verified
            except AttributeError:
                return False
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated and request.user.role == "seller":
            try:
                seller_profile = request.user.seller
                return seller_profile.is_verified and hasattr(obj, "seller") and obj.seller == seller_profile
            except AttributeError:
                return False
        return False