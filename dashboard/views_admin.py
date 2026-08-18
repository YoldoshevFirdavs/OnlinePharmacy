"""
Admin dashboard HTML views
- Analytics dashboard page with AJAX charts
- User history page
- Order detail page
"""

from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from users.models import CustomUser
from orders.models import Order


def is_admin(user):
    """Check if user is admin"""
    try:
        return user.is_authenticated and getattr(user, 'role', None) == 'admin'
    except:
        return False


@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def admin_analytics_dashboard(request):
    """
    Admin analytics dashboard with AJAX charts
    Charts auto-refresh every 60 seconds (1 minute)
    """
    context = {
        'page_title': 'Analytics Dashboard',
        'refresh_interval': 60000,  # 1 minute in milliseconds
    }
    return render(request, 'dashboard/admin/analytics.html', context)


@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def user_history_view(request, user_id):
    """
    User history page - shows immutable audit log for specific user
    Paginated list with action type, product, timestamp
    """
    try:
        user = get_object_or_404(CustomUser, id=user_id)
    except:
        return HttpResponseForbidden("User not found")
    
    context = {
        'page_title': f'User History - {user.full_name or user.phone_number}',
        'target_user': user,
        'user_id': user_id,
    }
    return render(request, 'dashboard/admin/user_history.html', context)


@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def order_detail_admin_view(request, user_id, order_id):
    """
    Order detail page for admin - standalone page (not modal)
    Shows full order info, line items, customer details, status
    """
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        order = get_object_or_404(Order, id=order_id, user=user)
    except:
        return HttpResponseForbidden("Order not found")
    
    context = {
        'page_title': f'Order #{order.id}',
        'target_user': user,
        'order': order,
        'user_id': user_id,
        'order_id': order_id,
    }
    return render(request, 'dashboard/admin/order_detail.html', context)


@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def order_detail_view(request, user_id, order_id):
    """
    Order detail page for admin
    Shows full order info, line items, customer details, status
    """
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        order = get_object_or_404(Order, id=order_id, user=user)
    except:
        return HttpResponseForbidden("Order not found")
    
    context = {
        'page_title': f'Order #{order.id}',
        'target_user': user,
        'order': order,
        'user_id': user_id,
        'order_id': order_id,
    }
    return render(request, 'dashboard/admin/order_detail.html', context)
@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def order_detail_view(request, user_id, order_id):
    """
    Order detail page for admin
    Shows full order info, line items, customer details, status
    """
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        order = get_object_or_404(Order, id=order_id, user=user)
    except:
        return HttpResponseForbidden("Order not found")
    
    context = {
        'page_title': f'Order #{order.id}',
        'target_user': user,
        'order': order,
        'user_id': user_id,
        'order_id': order_id,
    }
    return render(request, 'dashboard/admin/order_detail.html', context)


@login_required(login_url='dashboard:login_page')
@user_passes_test(is_admin, redirect_field_name=None)
def admin_order_view(request, order_id):
    """
    Admin order detail page - standalone page (not modal)
    URL: /dashboard/admin/orders/<order_id>/view/
    Shows full order info with base.html and theme.css
    """
    try:
        from orders.models import Order
        order = get_object_or_404(Order.objects.select_related('user', 'deliveryorder__driver__user').prefetch_related('items__product'), id=order_id)
    except:
        return HttpResponseForbidden("Order not found")
    
    context = {
        'page_title': f'Buyurtma #{order.id}',
        'order': order,
    }
    return render(request, 'dashboard/admin/order_detail.html', context)
