# dashboard/urls.py
from django.urls import path
from .views import (
    login_page, logout_page, main_dashboard,
    category_list, category_create, category_edit, category_delete,
    medicine_list, medicine_create, medicine_edit, medicine_delete,
    user_list, user_create, user_edit,
    order_list, audit_log_list, account_settings, dashboard_customize,
    deliverer_dashboard, deliverer_order_list, deliverer_order_update,
    not_allowed
)
app_name = 'dashboard'

urlpatterns = [
    # Main Dashboard
    path('', main_dashboard, name='main_dashboard'),

    # Account Dashboard
    path('account/', account_settings, name='account_dashboard'),
    path('account-settings/', account_settings, name='account_settings'),

    # Deliverer Dashboard
    path('delivery/', deliverer_dashboard, name='delivery_dashboard'),
    path('deliverer/', deliverer_dashboard, name='deliverer_dashboard'),
    path('deliverer/orders/', deliverer_order_list, name='deliverer_order_list'),
    path('deliverer/orders/<int:pk>/update/', deliverer_order_update, name='deliverer_order_update'),

    # Login/Logout
    path('login/', login_page, name='login_page'),
    path('logout/', logout_page, name='logout_page'),

    # Category Management
    path('categories/', category_list, name='category_list'),
    path('categories/create/', category_create, name='category_create'),
    path('categories/edit/<int:pk>/', category_edit, name='category_edit'),
    path('categories/delete/<int:pk>/', category_delete, name='category_delete'),

    # Medicine Management
    path('medicines/', medicine_list, name='medicine_list'),
    path('medicines/create/', medicine_create, name='medicine_create'),
    path('medicines/edit/<int:pk>/', medicine_edit, name='medicine_edit'),
    path('medicines/delete/<int:pk>/', medicine_delete, name='medicine_delete'),

    # User Management
    path('users/', user_list, name='user_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/edit/<int:pk>/', user_edit, name='user_edit'),

    # Order Management
    path('orders/', order_list, name='order_list'),

    # Other Features
    path('audit-log/', audit_log_list, name='audit_log_list'),
    path('customize/', dashboard_customize, name='dashboard_customize'),

    # Not Allowed Page
    path('not-allowed/', not_allowed, name='not_allowed'),
]