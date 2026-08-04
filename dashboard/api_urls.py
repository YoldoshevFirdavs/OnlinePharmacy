from django.urls import path

from . import api_views

app_name = "dashboard_api"

urlpatterns = [
    path("session/", api_views.SessionCheckView.as_view(), name="session"),
    path("stats/sales/", api_views.SalesStatsView.as_view(), name="sales_stats"),
    path("categories/", api_views.CategoryListView.as_view(), name="categories"),
    path("products/", api_views.ProductListView.as_view(), name="products"),
    path("orders/", api_views.OrderListView.as_view(), name="orders"),
    path("orders/recent/", api_views.RecentOrderListView.as_view(), name="orders_recent"),
    path(
        "orders/<int:pk>/status/",
        api_views.OrderStatusUpdateView.as_view(),
        name="order_status",
    ),
    path("users/", api_views.UserListView.as_view(), name="users"),
    path("settings/", api_views.SettingsView.as_view(), name="settings"),
    path("calendar/events/", api_views.CalendarEventsView.as_view(), name="calendar_events"),
]
