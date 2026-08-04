from functools import wraps
from django.shortcuts import redirect
from .views import is_admin, is_deliverer

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return redirect('dashboard:login_page')

            # Check if user has any of the required roles
            has_permission = False
            if 'admin' in roles and is_admin(user):
                has_permission = True
            if 'deliverer' in roles and is_deliverer(user):
                has_permission = True
            
            if has_permission:
                return view_func(request, *args, **kwargs)
            
            # If no permission, redirect to their own dashboard
            if is_admin(user):
                return redirect('dashboard:dashboard-admin')
            elif is_deliverer(user):
                return redirect('dashboard:deliverer_dashboard')
            else:
                # Fallback for regular users trying to access dashboard
                return redirect('dashboard:not_allowed')

        return _wrapped_view
    return decorator
