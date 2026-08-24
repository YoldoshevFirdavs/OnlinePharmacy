from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from dashboard.views import not_allowed as not_allowed_view
from orders.api_cart_checkout import CartAddAPIView, CartSummaryAPIView, CheckoutAPIView
from pharmacy.views.detail import product_detail, product_full_guide
from pharmacy.views.history import UserHistoryViewSet
from users.views import AccountView, AdminCheckView, AdminLoginViewSet, SubscriptionVerifyPageView, auth_view


class JWTSchemaGenerator(OpenAPISchemaGenerator):
    def get_security_definitions(self):
        security_definitions = super().get_security_definitions()
        security_definitions["Bearer"] = {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
        return security_definitions


schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version="v1",
        description="E-commerce API",
        contact=openapi.Contact(email="contact@myapi.local"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    generator_class=JWTSchemaGenerator,
)


def custom_logout_view(request):
    auth_logout(request)
    return redirect("/auth/")


urlpatterns = [
    path("", TemplateView.as_view(template_name="main.html"), name="home"),
    path("shop/", TemplateView.as_view(template_name="shop.html"), name="shop"),
    path("cart/", login_required(ensure_csrf_cookie(TemplateView.as_view(template_name="cart.html"))), name="cart"),
    path("order/", login_required(ensure_csrf_cookie(TemplateView.as_view(template_name="order.html"))), name="order"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("terms/", TemplateView.as_view(template_name="terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("contact/", TemplateView.as_view(template_name="contact.html"), name="contact"),
    path("auth/", auth_view, name="auth"),
    path("account/", AccountView.as_view(), name="account"),
    path("check/admin/", AdminCheckView.as_view(), name="admin_check"),
    path("subscribe/<str:token>/", SubscriptionVerifyPageView.as_view(), name="subscribe_verify"),
    path("admin/", admin.site.urls),
    path("dashboard/login/", RedirectView.as_view(url="/auth/")),
    path("dashboard/logout/", custom_logout_view),
    path("security/not-allowed/", not_allowed_view, name="not_allowed"),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("accounts/login/", TemplateView.as_view(template_name="auth.html"), name="login"),
    path("api/v1/users/", include("users.urls")),
    path(
        "api/v1/admin/login/",
        AdminLoginViewSet.as_view({"post": "create"}),
        name="admin_login_alias",
    ),
    path("api/v1/products/", include("pharmacy.urls", namespace="pharmacy")),
    path(
        "api/v1/user/history/",
        include(
            [
                path("", UserHistoryViewSet.as_view({"get": "list"}), name="user-history-list"),
                path("log/", UserHistoryViewSet.as_view({"post": "log_action"}), name="user-history-log"),
                path("<int:pk>/", UserHistoryViewSet.as_view({"get": "retrieve"}), name="user-history-detail"),
            ]
        ),
    ),
    path("products/<int:product_id>/", product_detail, name="product_detail_direct"),
    path("products/<int:product_id>/full/", product_full_guide, name="product_full_guide_direct"),
    path("api/v1/orders/", include("orders.urls")),
    path("api/v1/cart/add/", CartAddAPIView.as_view(), name="api_cart_add"),
    path("api/v1/cart/summary/", CartSummaryAPIView.as_view(), name="api_cart_summary"),
    path("api/v1/checkout/", CheckoutAPIView.as_view(), name="api_checkout"),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/dashboard/", include("dashboard.api_urls", namespace="dashboard_api")),
    path("api/v1/security/", include("security.urls", namespace="security")),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)),
]

# Add Prometheus metrics endpoint if prometheus_client is available
try:
    from django.http import HttpResponse
    from prometheus_client import REGISTRY
    from prometheus_client.exposition import generate_latest

    def prometheus_metrics_view(request):
        """Prometheus metrics endpoint"""
        return HttpResponse(generate_latest(REGISTRY), content_type="text/plain; version=0.0.4; charset=utf-8")

    urlpatterns.append(path("metrics/", prometheus_metrics_view, name="prometheus_metrics"))
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Also serve legacy media/ folder (files uploaded before MEDIA_ROOT was changed to mediafiles/)
    import os

    legacy_media = os.path.join(settings.BASE_DIR, "media")
    if os.path.isdir(legacy_media):
        urlpatterns += static(settings.MEDIA_URL, document_root=legacy_media)
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()


def custom_page_not_found(request, exception):
    return render(request, "404.html", status=404)


def custom_server_error(request):
    return render(request, "500.html", status=500)


handler404 = custom_page_not_found
handler500 = custom_server_error
