from functools import wraps

from django.shortcuts import redirect
from rest_framework.permissions import BasePermission

# FIXED: Add missing import for is_deliverer function
from .views import is_admin, is_deliverer


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                # Redirect to the public auth page
                return redirect("/auth/")

            # Check if user has any of the required roles
            has_permission = False
            if "admin" in roles and is_admin(user):
                has_permission = True
            if "deliverer" in roles and is_deliverer(user):
                has_permission = True

            if has_permission:
                return view_func(request, *args, **kwargs)

            # If no permission, redirect to their own dashboard
            if is_admin(user):
                return redirect("dashboard:dashboard-admin")
            elif is_deliverer(user):
                return redirect("dashboard:deliverer_dashboard")
            else:
                # Fallback for regular users trying to access dashboard
                return redirect("dashboard:not_allowed")

        return _wrapped_view

    return decorator


class IsDashboardAdmin(BasePermission):
    """
    Permission class that only allows admin users to access the view.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin(request.user)


class IsDashboardDeliverer(BasePermission):
    """
    Permission class that only allows deliverer users to access the view.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_deliverer(request.user)


class IsDashboardAdminOrDeliverer(BasePermission):
    """
    Permission class that allows both admin and deliverer users to access the view.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin(request.user) or is_deliverer(request.user)
