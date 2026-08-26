"""
Audit logging utility for tracking ALL user actions
- UserActionHistory: All users' actions (history)
- AuditLog: Admin/superuser actions only (audit log)
"""

import logging

from django.utils import timezone

from .models import AuditLog, UserActionHistory

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from request"""
    if not request:
        return None

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip


def log_action(
    user, action, description="", target_type=None, target_id=None, ip_address=None, meta=None, request=None
):
    """
    Log an action to both history and audit log

    Args:
        user: User performing the action
        action: Action name (e.g., 'user_create', 'product_edit')
        description: Detailed description
        target_type: Type of object (e.g., 'User', 'Product')
        target_id: ID of object
        ip_address: IP address
        meta: Additional metadata dict
        request: Django request object

    Returns:
        tuple: (history_log, audit_log) or (history_log, None) if not admin
    """
    if not user:
        return None, None

    # Extract IP if not provided
    if not ip_address and request:
        ip_address = get_client_ip(request)

    if meta is None:
        meta = {}

    history_log = None
    audit_log = None

    # 1. ALWAYS log to UserActionHistory (for all users)
    try:
        history_log = UserActionHistory.objects.create(
            user=user,
            action=action,
            description=description,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            metadata=meta,
        )
    except Exception as e:
        logger.error(f"Failed to log to history: {str(e)}")

    # 2. Log to AuditLog ONLY if admin or superuser
    if user.is_staff or user.is_superuser:
        try:
            audit_log = AuditLog.objects.create(
                user=user,
                action=action,
                description=description,
                target_type=target_type,
                target_id=target_id,
                ip_address=ip_address,
                meta=meta,
            )
        except Exception as e:
            logger.error(f"Failed to log to audit log: {str(e)}")

    return history_log, audit_log


def log_user_action(admin_user, target_user, action_type, description="", request=None):
    """Log user-related admin actions"""
    if not admin_user:
        return None, None

    return log_action(
        user=admin_user,
        action=f"user_{action_type}",
        description=description or f"User {action_type}: {target_user.email or target_user.phone_number}",
        target_type="User",
        target_id=target_user.id,
        ip_address=get_client_ip(request) if request else None,
        meta={
            "target_user_id": target_user.id,
            "target_user_email": target_user.email,
            "target_user_phone": target_user.phone_number,
        },
        request=request,
    )


def log_product_action(admin_user, product, action_type, description="", request=None):
    """Log product-related admin actions"""
    if not admin_user:
        return None, None

    return log_action(
        user=admin_user,
        action=f"product_{action_type}",
        description=description or f"Product {action_type}: {product.name}",
        target_type="Product",
        target_id=product.id,
        ip_address=get_client_ip(request) if request else None,
        meta={"product_name": product.name, "product_id": product.id},
        request=request,
    )


def log_category_action(admin_user, category, action_type, description="", request=None):
    """Log category-related admin actions"""
    if not admin_user:
        return None, None

    return log_action(
        user=admin_user,
        action=f"category_{action_type}",
        description=description or f"Category {action_type}: {category.name}",
        target_type="Category",
        target_id=category.id,
        ip_address=get_client_ip(request) if request else None,
        meta={"category_name": category.name},
        request=request,
    )


def log_order_action(admin_user, order, action_type, description="", request=None):
    """Log order-related admin actions"""
    if not admin_user:
        return None, None

    return log_action(
        user=admin_user,
        action=f"order_{action_type}",
        description=description or f"Order {action_type}: #{order.id}",
        target_type="Order",
        target_id=order.id,
        ip_address=get_client_ip(request) if request else None,
        meta={"order_id": order.id, "order_status": order.status},
        request=request,
    )
