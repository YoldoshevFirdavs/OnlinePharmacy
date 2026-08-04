from rest_framework import permissions


class IsAdminOrSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if request.user.role == "seller":
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if request.user.role == "seller" and hasattr(obj, "user") and obj.user == request.user:
                return True
        return False


class IsAdminOrDeliverer(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if request.user.role == "deliverer":
                return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
            if request.user.role == "deliverer" and hasattr(obj, "user") and obj.user == request.user:
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
        return bool(request.user and request.user.is_authenticated and request.user.role == "deliverer")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsVerifiedSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, 'seller_profile'))


