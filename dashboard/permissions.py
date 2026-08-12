from rest_framework.permissions import BasePermission

from .views import is_admin


class IsDashboardAdmin(BasePermission):
    """
    Permission class that only allows admin users to access the view.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin(request.user)
