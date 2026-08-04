from django.urls import path
from django.views.generic import TemplateView
from .views import (
    login_page,
    logout_page,
    main_dashboard,
    category_list,
    category_create,
    category_edit,
    category_delete,
    medicine_list,
    medicine_create,
    medicine_edit,
    medicine_delete,
    user_list,
    user_create,
    user_edit,
    order_list,
    audit_log_list,
    account_settings,
    dashboard_customize,
    deliverer_dashboard,
    deliverer_order_list,
    deliverer_order_update,
    not_allowed,
    # Delivery dashboard views
    delivery_dashboard,
    delivery_settings,
    delivery_map,
)
from users.views import TestAdminLoginView 
app_name = "dashboard"

urlpatterns = [
    path("admin/", main_dashboard, name="dashboard-admin"),
    path("login/", login_page, name="login_page"),
    path("logout/", logout_page, name="logout_page"),

    path("account/", account_settings, name="account_dashboard"),
    path("account-settings/", account_settings, name="account_settings"),

    path("categories/", category_list, name="category_list"),
    path("categories/create/", category_create, name="category_create"),
    path("categories/<int:pk>/edit/", category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", category_delete, name="category_delete"),

    path("medicines/", medicine_list, name="medicine_list"),
    path("medicines/create/", medicine_create, name="medicine_create"),
    path("medicines/<int:pk>/edit/", medicine_edit, name="medicine_edit"),
    path("medicines/<int:pk>/delete/", medicine_delete, name="medicine_delete"),

    path("users/", user_list, name="user_list"),
    path("users/create/", user_create, name="user_create"),
    path("users/<int:pk>/edit/", user_edit, name="user_edit"),

    path("orders/", order_list, name="order_list"),
    path("audit-log/", audit_log_list, name="audit_log_list"),

    path("customize/", dashboard_customize, name="dashboard_customize"),

    # Delivery dashboard routes
    path("delivery/", delivery_dashboard, name="delivery_dashboard"),
    path("delivery/settings/", delivery_settings, name="delivery_settings"),
    path("delivery/map/", delivery_map, name="delivery_map"),
    
    path("deliverer/", deliverer_dashboard, name="deliverer_dashboard"),
    path("deliverer/orders/", deliverer_order_list, name="deliverer_order_list"),
    path("deliverer/orders/<int:pk>/update/", deliverer_order_update, name="deliverer_order_update"),

    path("not-allowed/", not_allowed, name="not_allowed"),
    path("test-admin-login/", TemplateView.as_view(template_name="check_admin.html"), name="test_admin_login"),
]