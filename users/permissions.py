from rest_framework import permissions

from users.models import Seller


class IsAdminOrSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            # FIXED: Use Seller.objects.filter() instead of role field check
            if Seller.objects.filter(user=request.user).exists():
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if (
                Seller.objects.filter(user=request.user).exists()
                and hasattr(obj, "user")
                and obj.user == request.user
            ):
                return True
        return False


class IsAdminOrDeliverer(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if (
                hasattr(request.user, "deliverer_profile")
                and request.user.deliverer_profile is not None
            ):
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if (
                hasattr(request.user, "deliverer_profile")
                and request.user.deliverer_profile is not None
            ):
                if hasattr(obj, "user") and obj.user == request.user:
                    return True
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if hasattr(obj, "user") and obj.user == request.user:
                return True
            if isinstance(obj, type(request.user)) and obj == request.user:
                return True
        return False


class IsDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            return (
                request.user.deliverer_profile is not None
                and request.user.deliverer_profile.status == "active"
            )
        except Exception:
            return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsVerifiedSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        # FIXED: Use Seller.objects.filter() instead of hasattr() check
        return bool(
            request.user
            and request.user.is_authenticated
            and Seller.objects.filter(user=request.user, is_verified=True).exists()
        )
