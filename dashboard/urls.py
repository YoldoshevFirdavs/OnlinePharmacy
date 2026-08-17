from django.urls import path
from django.views.generic import TemplateView

from users.views import TestAdminLoginView

from .api_views import (
    DeliveryDriverViewSet, SessionCheckView, SalesStatsView, CategoryListView,
    ProductListView, OrderListView, RecentOrderListView, OrderStatusUpdateView,
    UserListView, SettingsView, CalendarEventsView, DashboardStatsApiView,
    DriverApiView, BannedUsersListView, BanUserView, UnbanUserView, UserBanDetailView
)
from .views import seller_dashboard  # Added seller_dashboard
from .views import (
    account_settings,
    audit_log_list,
    category_create,
    category_delete,
    category_edit,
    category_list,
    dashboard_customize,
    delivery_create,
    delivery_delete,
    delivery_edit,
    delivery_list,
    login_page,
    logout_page,
    main_dashboard,
    medicine_create,
    medicine_delete,
    medicine_edit,
    medicine_list,
    not_allowed,
    order_create,
    order_delete,
    order_edit,
    order_list,
    order_view,
    user_create,
    user_delete,
    user_edit,
    user_list,
    ban_list,  # Added ban list view
)

app_name = "dashboard"

urlpatterns = [
    path("admin/", main_dashboard, name="dashboard-admin"),
    path(
        "seller/", seller_dashboard, name="seller_dashboard"
    ),  # Added seller dashboard URL
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
    path("users/<int:pk>/delete/", user_delete, name="user_delete"),
    path("orders/", order_list, name="order_list"),
    path("orders/create/", order_create, name="order_create"),
    path("orders/<int:pk>/edit/", order_edit, name="order_edit"),
    path("orders/<int:pk>/view/", order_view, name="order_view"),
    path("orders/<int:pk>/delete/", order_delete, name="order_delete"),
    path("audit-log/", audit_log_list, name="audit_log_list"),
    path("bans/", ban_list, name="ban_list"),  # Added ban list URL
    path("customize/", dashboard_customize, name="dashboard_customize"),
    path("delivery/", delivery_list, name="delivery_list"),
    path("delivery/create/", delivery_create, name="delivery_create"),
    path("delivery/<int:pk>/edit/", delivery_edit, name="delivery_edit"),
    path("delivery/<int:pk>/delete/", delivery_delete, name="delivery_delete"),
    path("api/delivery/", DeliveryDriverViewSet.as_view(), name="delivery-list-create"),
    path(
        "api/delivery/<int:pk>/",
        DeliveryDriverViewSet.as_view(),
        name="delivery-detail",
    ),
    path("api/session/", SessionCheckView.as_view(), name="api_session"),
    path("not-allowed/", not_allowed, name="not_allowed"),
    path(
        "test-admin-login/",
        TemplateView.as_view(template_name="check_admin.html"),
        name="test_admin_login",
    ),
]
