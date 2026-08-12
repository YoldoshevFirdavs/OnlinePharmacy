from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginViewSet,
    CheckSessionView,
    CookieRefreshView,
    CustomUserViewSet,
    DetermineRoleView,
    EmailLoginView,
    LogoutJWTView,
    LogoutView,
    RegistrationView,
    SellerViewSet,
    StripeConfigView,
    SubscribedUserViewSet,
    SubscriberCreateView,
    TelegramLoginView,
    TestAdminLoginView,
    UserProfileViewSet,
    VerifyOtpView,
    VerifySubscriptionView,
)

router = DefaultRouter()
router.register(r"users", CustomUserViewSet, basename="users")
router.register(r"sellers", SellerViewSet, basename="sellers")
router.register(r"subscribed-users", SubscribedUserViewSet, basename="subscribers")

urlpatterns = [
    path("login/telegram/", TelegramLoginView.as_view(), name="login-telegram"),
    path("login/email/", EmailLoginView.as_view(), name="login-email"),
    path("login/verify-otp/", VerifyOtpView.as_view(), name="user-verify-otp"),
    path(
        "login/check-session/", CheckSessionView.as_view(), name="login-check-session"
    ),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "token/refresh/cookie/",
        CookieRefreshView.as_view(),
        name="token_refresh_cookie",
    ),
    path("registration/", RegistrationView.as_view(), name="registration"),
    path("me/", UserProfileViewSet.as_view(), name="user_profile"),
    path(
        "subscribe/verify/<str:token>/",
        VerifySubscriptionView.as_view(),
        name="subscribe-verify",
    ),
    path("subscribers/", SubscriberCreateView.as_view(), name="subscribers-list"),
    path(
        "admin/login/",
        AdminLoginViewSet.as_view({"post": "create", "get": "verify"}),
        name="admin_login",
    ),
    path(
        "admin/login/verify-otp/",
        AdminLoginViewSet.as_view({"post": "verify_otp"}),
        name="admin_login_verify_otp",
    ),
    path("payments/stripe-config/", StripeConfigView.as_view(), name="stripe_config"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("logout/jwt/", LogoutJWTView.as_view(), name="logout-jwt"),
    path("determine_role/", DetermineRoleView.as_view(), name="determine-role"),
    path("admin/check/", TestAdminLoginView.as_view(), name="admin-check"),
    path("", include(router.urls)),
]
