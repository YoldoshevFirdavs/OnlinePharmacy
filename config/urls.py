from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from users.views import AccountView, AdminCheckView, AdminLoginViewSet, auth_view, SubscriptionVerifyPageView


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
    path("cart/", TemplateView.as_view(template_name="cart.html"), name="cart"),
    path("order/", TemplateView.as_view(template_name="order.html"), name="order"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("terms/", TemplateView.as_view(template_name="terms.html"), name="terms"),
    path(
        "privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"
    ),
    path(
        "contact/", TemplateView.as_view(template_name="contact.html"), name="contact"
    ),
    path("auth/", auth_view, name="auth"),
    path("account/", AccountView.as_view(), name="account"),
    path("check/admin/", AdminCheckView.as_view(), name="admin_check"),
    path("subscribe/<str:token>/", SubscriptionVerifyPageView.as_view(), name="subscribe_verify"),
    path("admin/", admin.site.urls),
    path("dashboard/login/", RedirectView.as_view(url="/auth/")),
    path("dashboard/logout/", custom_logout_view),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path(
        "accounts/login/", TemplateView.as_view(template_name="auth.html"), name="login"
    ),
    path("api/v1/users/", include("users.urls")),
    path(
        "api/v1/admin/login/",
        AdminLoginViewSet.as_view({"post": "create"}),
        name="admin_login_alias",
    ),
    path("api/v1/pharmacy/", include("pharmacy.urls", namespace='pharmacy')),
    path("api/v1/orders/", include("orders.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/dashboard/", include("dashboard.api_urls", namespace="dashboard_api")),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
]

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