import logging
import os
import traceback

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from orders.models import Order
from pharmacy.models import Category, Medicine
from security.models import AuditLog
from users.models import CustomUser, DeliveryDriver, Seller

from .forms import (
    AccountSettingsForm,
    CategoryForm,
    DeliveryDriverForm,
    MedicineForm,
    OrderForm,
    UserForm,
)

logger = logging.getLogger(__name__)


def log_dashboard_error(component: str, user=None, error=None, action: str = ""):
    try:
        timestamp = timezone.now().isoformat()
        user_id = getattr(user, "id", "N/A") if user else "N/A"
        email = getattr(user, "email", "") or ""
        masked_email = (
            f"{email[:1]}***@{email.split('@')[-1]}"
            if email and "@" in email
            else ("***" if email else "N/A")
        )
        error_msg = str(error) if error else "Unknown error"
        exc_tb = traceback.format_exc()

        log_entry = (
            f"TIMESTAMP: {timestamp}\n"
            f"COMPONENT: {component}\n"
            f"USER: id={user_id}; email={masked_email}\n"
            f"ERROR: {error_msg}\n"
            f"ACTION: {action}\n"
            f"TRACEBACK: {exc_tb[:300].strip()}\n"
            f"---\n"
        )
        error_log_path = os.path.join(settings.BASE_DIR, "errors", "dashboard_error.md")
        os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as log_err:
        logger.error(f"Failed to write dashboard error log: {log_err}")


def get_user_display(user):
    if not user or not getattr(user, "is_authenticated", False):
        return {
            "id": None,
            "full_name": "Mehmon",
            "email": "",
            "avatar_url": "/static/dashboard/images/default_avatar.png",
        }
    full_name = (
        (callable(getattr(user, "get_full_name", None)) and user.get_full_name())
        or getattr(user, "full_name", None)
        or getattr(user, "email", None)
        or getattr(user, "phone_number", None)
        or "User"
    )
    avatar_url = None
    if getattr(user, "avatar", None) and getattr(user.avatar, "name", None):
        # Try mediafiles/ first (current MEDIA_ROOT), then legacy media/
        import os

        media_roots = [
            settings.MEDIA_ROOT,
            os.path.join(settings.BASE_DIR, "media"),
        ]
        for root in media_roots:
            full_path = os.path.join(root, user.avatar.name)
            if os.path.isfile(full_path):
                avatar_url = settings.MEDIA_URL + user.avatar.name
                break
        if not avatar_url:
            # File not found on disk but field has value — still return URL
            try:
                avatar_url = user.avatar.url
            except Exception:
                avatar_url = None
    if not avatar_url:
        avatar_url = "/static/dashboard/images/default_avatar.png"
    return {
        "id": getattr(user, "id", None),
        "full_name": full_name,
        "email": getattr(user, "email", "") or "",
        "avatar_url": avatar_url,
    }


def find_and_authenticate_by_identifier(request, identifier, password):
    if not identifier or not password:
        return None
    User = get_user_model()
    identifier_str = str(identifier).strip()

    # 1. Search by email
    user = User.objects.filter(email__iexact=identifier_str).first()

    # 2. Search by phone_number
    if not user:
        user = User.objects.filter(phone_number__iexact=identifier_str).first()

    # 3. Cleaned phone search fallback
    if not user:
        clean_phone = identifier_str.replace("+", "").replace(" ", "").replace("-", "")
        if clean_phone:
            user = User.objects.filter(phone_number__icontains=clean_phone).first()

    if user and user.check_password(password):
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        return user
    return None


def login_required_decorator(function=None, redirect_field_name="next", login_url=None):
    try:
        actual_decorator = user_passes_test(
            lambda u: u.is_authenticated,
            redirect_field_name=redirect_field_name,
            login_url=login_url,
        )
        if function:
            return actual_decorator(function)
        return actual_decorator
    except Exception as e:
        logger.error(f"Error in login_required_decorator: {str(e)}")
        raise


def is_admin(user):
    try:
        return user.is_authenticated and getattr(user, 'role', None) == 'admin'
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False


def is_seller(user):
    try:
        return (
            user.is_authenticated
            and getattr(user, 'role', None) == 'seller'
        )
    except Exception as e:
        logger.error(f"Error checking seller status: {str(e)}")
        return False


def login_page(request):
    try:
        if request.method == "POST":
            try:
                identifier = (
                    request.POST.get("username", "").strip()
                    or request.POST.get("email", "").strip()
                    or request.POST.get("phone", "").strip()
                )
                password = request.POST.get("password", "").strip()

                if not identifier or not password:
                    messages.error(request, "Login va parol majburiy.")
                    return render(request, "dashboard/login.html", {})

                # Authenticate using standard authenticate
                user = authenticate(request, username=identifier, password=password)

                # Fallback: if auth fails, search by email or phone + password
                if user is None:
                    user = find_and_authenticate_by_identifier(
                        request, identifier, password
                    )

                if user is not None:
                    try:
                        login(request, user)
                        full_name = (
                            getattr(user, "full_name", None)
                            or getattr(user, "email", None)
                            or "User"
                        )
                        messages.success(request, f"Xush kelibsiz, {full_name}!")

                        if is_admin(user):
                            return redirect("dashboard:dashboard-admin")
                        elif is_seller(user):
                            return redirect(
                                "dashboard:seller_dashboard"
                            )  # Redirect to seller dashboard
                        else:
                            messages.error(
                                request, "Sizda admin yoki sotuvchi huquqlari yo'q."
                            )
                            logout(request)
                            return redirect("/auth/")
                    except Exception as login_error:
                        log_dashboard_error(
                            "login_page",
                            user,
                            login_error,
                            action="Login failed during login(request, user)",
                        )
                        messages.error(request, "Login jarayonida xatolik yuz berdi.")
                        return render(request, "dashboard/login.html", {})
                else:
                    messages.error(request, "Noto'g'ri login yoki parol.")
                    return redirect("/auth/")

            except Exception as post_error:
                log_dashboard_error(
                    "login_page",
                    None,
                    post_error,
                    action="POST processing error in login_page",
                )
                messages.error(request, "Login jarayonida xatolik yuz berdi.")
                return redirect("/auth/")

        if request.user.is_authenticated:
            try:
                if is_admin(request.user):
                    return redirect("dashboard:dashboard-admin")
                elif is_seller(request.user):
                    return redirect(
                        "dashboard:seller_dashboard"
                    )  # Redirect to seller dashboard
                else:
                    messages.error(request, "Sizda admin yoki sotuvchi huquqlari yo'q.")
                    logout(request)
                    return redirect("/auth/")
            except Exception as auth_check_error:
                log_dashboard_error(
                    "login_page",
                    request.user,
                    auth_check_error,
                    action="Redirected to /auth/",
                )
                logout(request)
                return redirect("/auth/")

        ctx = {"user_display": get_user_display(request.user)}
        return render(request, "dashboard/login.html", ctx)

    except Exception as e:
        log_dashboard_error(
            "login_page",
            getattr(request, "user", None),
            e,
            action="Redirected to /auth/",
        )
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("/auth/")


@login_required_decorator(login_url="dashboard:login_page")
def logout_page(request):
    try:
        logout(request)
        messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
        return redirect("dashboard:login_page")
    except Exception as e:
        log_dashboard_error(
            "logout_page",
            getattr(request, "user", None),
            e,
            action="Error during logout",
        )
        messages.error(request, "Logout jarayonida xatolik yuz berdi.")
        return redirect("dashboard:login_page")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def main_dashboard(request):
    try:
        user = request.user
        # Fallback check if user is Anonymous
        if not user or not getattr(user, "is_authenticated", False):
            identifier = (
                request.POST.get("username")
                or request.POST.get("email")
                or request.POST.get("phone")
            )
            password = request.POST.get("password")
            if identifier and password:
                user = find_and_authenticate_by_identifier(
                    request, identifier, password
                )

        if (
            not user
            or not getattr(user, "is_authenticated", False)
            or not is_admin(user)
        ):
            return redirect("/auth/")

        user_display = get_user_display(user)

        try:
            total_categories = Category.objects.count()
            total_medicines = Medicine.objects.count()
            total_customers = CustomUser.objects.filter(
                is_staff=False, seller__isnull=True
            ).count()
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status="Pending").count()
            delivered_orders = Order.objects.filter(status="Delivered").count()
            total_users = CustomUser.objects.count()
            total_drivers = DeliveryDriver.objects.count()
            out_of_stock = Medicine.objects.filter(stock=0).count()
            total_staff = CustomUser.objects.filter(is_staff=True).count()

            ctx = {
                "user_display": user_display,
                "total_categories": total_categories,
                "total_medicines": total_medicines,
                "total_customers": total_customers,
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "delivered_orders": delivered_orders,
                "total_users": total_users,
                "total_drivers": total_drivers,
                "out_of_stock": out_of_stock,
                "total_staff": total_staff,
            }
            return render(request, "dashboard/index.html", ctx)

        except Exception as query_error:
            log_dashboard_error(
                "main_dashboard",
                user,
                query_error,
                action="Rendered dashboard index with default zero values",
            )
            messages.error(
                request, "Dashboard ma'lumotlarini yuklashda xatolik yuz berdi."
            )
            ctx = {
                "user_display": user_display,
                "total_categories": 0,
                "total_medicines": 0,
                "total_customers": 0,
                "total_orders": 0,
                "pending_orders": 0,
                "delivered_orders": 0,
                "total_users": 0,
                "total_drivers": 0,
                "out_of_stock": 0,
                "total_staff": 0,
            }
            return render(request, "dashboard/index.html", ctx)

    except Exception as e:
        log_dashboard_error(
            "main_dashboard",
            getattr(request, "user", None),
            e,
            action="Redirected to /auth/",
        )
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("/auth/")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(
    is_seller, login_url="dashboard:not_allowed"
)  # Protected by is_seller
def seller_dashboard(request):
    try:
        user = request.user
        if (
            not user
            or not getattr(user, "is_authenticated", False)
            or not is_seller(user)
        ):
            return redirect("/auth/")

        user_display = get_user_display(user)
        # You can add seller-specific data here if needed
        ctx = {
            "user_display": user_display,
            "seller_name": (
                user.seller.shop_name if hasattr(user, "seller") else user.full_name
            ),
            # Add other seller-specific data
        }
        return render(request, "dashboard/seller/index.html", ctx)
    except Exception as e:
        log_dashboard_error(
            "seller_dashboard",
            getattr(request, "user", None),
            e,
            action="Redirected to /auth/",
        )
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("/auth/")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def category_list(request):
    try:
        try:
            categories = (
                Category.objects.annotate(medicine_count=Count("medicines"))
                .all()
                .order_by("id")
            )
            ctx = {"categories": categories}
            return render(request, "dashboard/category/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Database query error in category_list: {str(query_error)}")
            messages.error(request, "Kategoriyalar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/category/list.html", {"categories": []})

    except Exception as e:
        logger.error(f"Unexpected error in category_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return render(request, "dashboard/category/list.html", {"categories": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def category_create(request):
    try:
        if request.method == "POST":
            try:
                form = CategoryForm(request.POST, request.FILES)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            messages.success(
                                request, "Kategoriya muvaffaqiyatli yaratildi."
                            )
                            return redirect("dashboard:category_list")
                    except Exception as save_error:
                        logger.error(f"Error saving category: {str(save_error)}")
                        messages.error(
                            request, "Kategoriyani saqlashda xatolik yuz berdi."
                        )
                        return render(
                            request, "dashboard/category/form.html", {"form": form}
                        )
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(
                        request, "dashboard/category/form.html", {"form": form}
                    )

            except Exception as form_error:
                logger.error(
                    f"Form processing error in category_create: {str(form_error)}"
                )
                messages.error(request, "Kategoriya yaratishda xatolik yuz berdi.")
                form = CategoryForm()
                return render(request, "dashboard/category/form.html", {"form": form})
        else:
            try:
                form = CategoryForm()
                ctx = {"form": form}
                return render(request, "dashboard/category/form.html", ctx)
            except Exception as get_error:
                logger.error(f"Error loading form in category_create: {str(get_error)}")
                messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                return redirect("dashboard:category_list")

    except Exception as e:
        logger.error(f"Unexpected error in category_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:category_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def category_edit(request, pk):
    try:
        try:
            category = get_object_or_404(Category, pk=pk)

            if request.method == "POST":
                try:
                    form = CategoryForm(request.POST, request.FILES, instance=category)
                    if form.is_valid():
                        try:
                            with transaction.atomic():
                                form.save()
                                messages.success(
                                    request, "Kategoriya muvaffaqiyatli yangilandi."
                                )
                                return redirect("dashboard:category_list")
                        except Exception as save_error:
                            logger.error(f"Error updating category: {str(save_error)}")
                            messages.error(
                                request, "Kategoriyani yangilashda xatolik yuz berdi."
                            )
                            return render(
                                request,
                                "dashboard/category/form.html",
                                {"form": form, "category": category},
                            )
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(
                            request,
                            "dashboard/category/form.html",
                            {"form": form, "category": category},
                        )

                except Exception as form_error:
                    logger.error(
                        f"Form processing error in category_edit: {str(form_error)}"
                    )
                    messages.error(request, "Kategoriya yangilashda xatolik yuz berdi.")
                    form = CategoryForm(instance=category)
                    return render(
                        request,
                        "dashboard/category/form.html",
                        {"form": form, "category": category},
                    )
            else:
                try:
                    form = CategoryForm(instance=category)
                    ctx = {"form": form, "category": category}
                    return render(request, "dashboard/category/form.html", ctx)
                except Exception as get_error:
                    logger.error(
                        f"Error loading form in category_edit: {str(get_error)}"
                    )
                    messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                    return redirect("dashboard:category_list")

        except Exception as query_error:
            logger.error(f"Database query error in category_edit: {str(query_error)}")
            messages.error(request, "Kategoriyani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:category_list")

    except Exception as e:
        logger.error(f"Unexpected error in category_edit: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:category_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def category_delete(request, pk):
    try:
        category = get_object_or_404(Category, pk=pk)
        with transaction.atomic():
            category_name = category.name
            category.delete()
            messages.success(
                request,
                f"'{category_name}' kategoriya muvaffaqiyatli o'chirildi.",
            )
            return redirect("dashboard:category_list")
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        messages.error(request, "Kategoriyani o'chirishda xatolik yuz berdi.")
        return redirect("dashboard:category_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def medicine_list(request):
    try:
        try:
            medicines = Medicine.objects.all().order_by("id")
            ctx = {"medicines": medicines}
            return render(request, "dashboard/product/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Database query error in medicine_list: {str(query_error)}")
            messages.error(request, "Dorilar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/product/list.html", {"medicines": []})

    except Exception as e:
        logger.error(f"Unexpected error in medicine_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return render(request, "dashboard/product/list.html", {"medicines": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def medicine_create(request):
    try:
        if request.method == "POST":
            try:
                form = MedicineForm(request.POST, request.FILES)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            messages.success(request, "Dori muvaffaqiyatli yaratildi.")
                            return redirect("dashboard:medicine_list")
                    except Exception as save_error:
                        logger.error(f"Error saving medicine: {str(save_error)}")
                        messages.error(request, "Dorini saqlashda xatolik yuz berdi.")
                        return render(
                            request, "dashboard/product/form.html", {"form": form}
                        )
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(
                        request, "dashboard/product/form.html", {"form": form}
                    )

            except Exception as form_error:
                logger.error(
                    f"Form processing error in medicine_create: {str(form_error)}"
                )
                messages.error(request, "Dori yaratishda xatolik yuz berdi.")
                form = MedicineForm()
                return render(request, "dashboard/product/form.html", {"form": form})
        else:
            try:
                form = MedicineForm()
                ctx = {"form": form}
                return render(request, "dashboard/product/form.html", ctx)
            except Exception as get_error:
                logger.error(f"Error loading form in medicine_create: {str(get_error)}")
                messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                return redirect("dashboard:medicine_list")

    except Exception as e:
        logger.error(f"Unexpected error in medicine_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:medicine_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def medicine_edit(request, pk):
    try:
        try:
            medicine = get_object_or_404(Medicine, pk=pk)

            if request.method == "POST":
                try:
                    form = MedicineForm(request.POST, request.FILES, instance=medicine)
                    if form.is_valid():
                        try:
                            with transaction.atomic():
                                form.save()
                                messages.success(
                                    request, "Dori muvaffaqiyatli yangilandi."
                                )
                                return redirect("dashboard:medicine_list")
                        except Exception as save_error:
                            logger.error(f"Error updating medicine: {str(save_error)}")
                            messages.error(
                                request, "Dorini yangilashda xatolik yuz berdi."
                            )
                            return render(
                                request,
                                "dashboard/product/form.html",
                                {"form": form, "medicine": medicine},
                            )
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(
                            request,
                            "dashboard/product/form.html",
                            {"form": form, "medicine": medicine},
                        )

                except Exception as form_error:
                    logger.error(
                        f"Form processing error in medicine_edit: {str(form_error)}"
                    )
                    messages.error(request, "Dori yangilashda xatolik yuz berdi.")
                    form = MedicineForm(instance=medicine)
                    return render(
                        request,
                        "dashboard/product/form.html",
                        {"form": form, "medicine": medicine},
                    )
            else:
                try:
                    form = MedicineForm(instance=medicine)
                    ctx = {"form": form, "medicine": medicine}
                    return render(request, "dashboard/product/form.html", ctx)
                except Exception as get_error:
                    logger.error(
                        f"Error loading form in medicine_edit: {str(get_error)}"
                    )
                    messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                    return redirect("dashboard:medicine_list")

        except Exception as query_error:
            logger.error(f"Database query error in medicine_edit: {str(query_error)}")
            messages.error(request, "Dorini yuklashda xatolik yuz berdi.")
            return redirect("dashboard:medicine_list")

    except Exception as e:
        logger.error(f"Unexpected error in medicine_edit: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:medicine_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def medicine_delete(request, pk):
    try:
        try:
            medicine = get_object_or_404(Medicine, pk=pk)

            try:
                with transaction.atomic():
                    medicine_name = medicine.name
                    medicine.delete()
                    messages.success(
                        request,
                        f"'{medicine_name}' dori muvaffaqiyatli o'chirildi.",
                    )
                    return redirect("dashboard:medicine_list")
            except Exception as delete_error:
                logger.error(f"Error deleting medicine: {str(delete_error)}")
                messages.error(request, "Dorini o'chirishda xatolik yuz berdi.")
                return redirect("dashboard:medicine_list")

        except Exception as query_error:
            logger.error(f"Database query error in medicine_delete: {str(query_error)}")
            messages.error(request, "Dorini yuklashda xatolik yuz berdi.")
            return redirect("dashboard:medicine_list")

    except Exception as e:
        logger.error(f"Unexpected error in medicine_delete: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:medicine_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def user_list(request):
    try:
        users = CustomUser.objects.select_related("seller").all().order_by("id")
        for user in users:
            if user.is_staff:
                user.real_role = "Admin"
            elif hasattr(user, "seller") and user.seller is not None:
                user.real_role = "Seller"
            else:
                user.real_role = "Foydalanuvchi"

        ctx = {"users": users}
        return render(request, "dashboard/user/list.html", ctx)
    except Exception as query_error:
        logger.error(f"Database query error in user_list: {str(query_error)}")
        messages.error(request, "Foydalanuvchilar yuklashda xatolik yuz berdi.")
        return render(request, "dashboard/user/list.html", {"users": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def user_create(request):
    try:
        if request.method == "POST":
            try:
                form = UserForm(request.POST, request.FILES)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            messages.success(
                                request, "Foydalanuvchi muvaffaqiyatli yaratildi."
                            )
                            return redirect("dashboard:user_list")
                    except Exception as save_error:
                        logger.error(f"Error saving user: {str(save_error)}")
                        messages.error(
                            request, "Foydalanuvchini saqlashda xatolik yuz berdi."
                        )
                        return render(
                            request, "dashboard/user/form.html", {"form": form}
                        )
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(request, "dashboard/user/form.html", {"form": form})

            except Exception as form_error:
                logger.error(f"Form processing error in user_create: {str(form_error)}")
                messages.error(request, "Foydalanuvchi yaratishda xatolik yuz berdi.")
                form = UserForm()
                return render(request, "dashboard/user/form.html", {"form": form})
        else:
            try:
                form = UserForm()
                ctx = {"form": form}
                return render(request, "dashboard/user/form.html", ctx)
            except Exception as get_error:
                logger.error(f"Error loading form in user_create: {str(get_error)}")
                messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                return redirect("dashboard:user_list")

    except Exception as e:
        logger.error(f"Unexpected error in user_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:user_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    try:
        try:
            user = get_object_or_404(CustomUser, pk=pk)

            if request.method == "POST":
                try:
                    form = UserForm(request.POST, request.FILES, instance=user)
                    if form.is_valid():
                        try:
                            with transaction.atomic():
                                form.save()
                                messages.success(
                                    request, "Foydalanuvchi muvaffaqiyatli yangilandi."
                                )
                                return redirect("dashboard:user_list")
                        except Exception as save_error:
                            logger.error(f"Error updating user: {str(save_error)}")
                            messages.error(
                                request,
                                "Foydalanuvchini yangilashda xatolik yuz berdi.",
                            )
                            return render(
                                request,
                                "dashboard/user/form.html",
                                {"form": form, "user": user},
                            )
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(
                            request,
                            "dashboard/user/form.html",
                            {"form": form, "user": user},
                        )

                except Exception as form_error:
                    logger.error(
                        f"Form processing error in user_edit: {str(form_error)}"
                    )
                    messages.error(
                        request, "Foydalanuvchi yangilashda xatolik yuz berdi."
                    )
                    form = UserForm(instance=user)
                    return render(
                        request,
                        "dashboard/user/form.html",
                        {"form": form, "user": user},
                    )
            else:
                try:
                    form = UserForm(instance=user)
                    ctx = {"form": form, "user": user}
                    return render(request, "dashboard/user/form.html", ctx)
                except Exception as get_error:
                    logger.error(f"Error loading form in user_edit: {str(get_error)}")
                    messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                    return redirect("dashboard:user_list")

        except Exception as query_error:
            logger.error(f"Database query error in user_edit: {str(query_error)}")
            messages.error(request, "Foydalanuvchini yuklashda xatolik yuz berdi.")
            return redirect("dashboard:user_list")

    except Exception as e:
        logger.error(f"Unexpected error in user_edit: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:user_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def order_list(request):
    try:
        try:
            from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
            
            # Get params
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 25)
            search = request.GET.get('search', '')
            status = request.GET.get('status', '')
            
            # Base query - use 'user' not 'customer' (model uses user field)
            orders = Order.objects.select_related('user').order_by('-created_at')
            
            # Filter by status
            if status:
                orders = orders.filter(status=status)
            
            # Search - use 'user' not 'customer'
            if search:
                from django.db.models import Q
                orders = orders.filter(
                    Q(id__icontains=search) |
                    Q(user__email__icontains=search) |
                    Q(user__full_name__icontains=search)
                )
            
            # Pagination
            paginator = Paginator(orders, page_size)
            try:
                orders_page = paginator.page(page)
            except PageNotAnInteger:
                orders_page = paginator.page(1)
            except EmptyPage:
                orders_page = paginator.page(paginator.num_pages)
            
            ctx = {
                "orders": orders_page,
                "search": search,
                "status": status,
                "total_orders": paginator.count,
                "num_pages": paginator.num_pages,
            }
            return render(request, "dashboard/order/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Database query error in order_list: {str(query_error)}")
            messages.error(request, "Buyurtmalar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/order/list.html", {"orders": []})

    except Exception as e:
        logger.error(f"Unexpected error in order_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return render(request, "dashboard/order/list.html", {"orders": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def audit_log_list(request):
    try:
        try:
            audit_logs = AuditLog.objects.all().order_by("-timestamp")
            ctx = {"audit_logs": audit_logs}
            return render(request, "dashboard/audit/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Error in audit_log_list: {str(query_error)}")
            messages.error(request, "Audit loglar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/audit/list.html", {"audit_logs": []})

    except Exception as e:
        logger.error(f"Unexpected error in audit_log_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return render(request, "dashboard/audit/list.html", {"audit_logs": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def account_settings(request):
    user = request.user
    if not user or not getattr(user, "is_authenticated", False):
        logger.error("account_settings: unauthenticated or invalid request.user")
        messages.error(request, "Iltimos tizimga qayta kiring.")
        return redirect("dashboard:login_page")

    try:
        user_display = get_user_display(user)
        if request.method == "POST":
            form = AccountSettingsForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                with transaction.atomic():
                    user_obj = form.save(commit=False)
                    new_password1 = form.cleaned_data.get("new_password1")
                    if new_password1:
                        user_obj.set_password(new_password1)
                    user_obj.save()
                    messages.success(
                        request, "Hisob sozlamalari muvaffaqiyatli yangilandi."
                    )
                    return redirect("dashboard:account_settings")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return render(
                    request,
                    "dashboard/account/settings.html",
                    {"form": form, "user_display": user_display},
                )
        else:
            form = AccountSettingsForm(instance=user)
            return render(
                request,
                "dashboard/account/settings.html",
                {"form": form, "user_display": user_display},
            )

    except Exception as e:
        log_dashboard_error(
            "account_settings", user, e, action="Redirected to login_page"
        )
        messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
        return redirect("dashboard:login_page")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def dashboard_customize(request):
    try:
        ctx = {"user_display": get_user_display(request.user)}
        return render(request, "dashboard/customize/index.html", ctx)
    except Exception as e:
        log_dashboard_error(
            "dashboard_customize",
            getattr(request, "user", None),
            e,
            action="Redirected to main_dashboard",
        )
        messages.error(request, "Dashboard sozlamalarini yuklashda xatolik yuz berdi.")
        return redirect("dashboard:main_dashboard")
    except Exception as e:
        logger.error(f"Error in dashboard_customize: {str(e)}")
        messages.error(request, "Dashboard sozlamalarini yuklashda xatolik yuz berdi.")
        return redirect("dashboard:main_dashboard")


def not_allowed(request):
    """Ban/Blocked sahifasi - Enhanced with fingerprint ban support"""
    try:
        from users.services import BanService
        
        user = request.user if request.user.is_authenticated else None
        path_attempted = request.GET.get("next", request.path)
        
        # Ban tafsilotlarini olish
        ban_info = None
        fp_ban_info = None
        
        if user:
            ban_info = BanService.get_ban_info(user)
        
        # Device fingerprint ban tekshirish
        fp = getattr(request, 'device_fingerprint', None)
        if not fp:
            fp = request.COOKIES.get('device_fp') or request.META.get('HTTP_AUTHORIZATION_FINGERPRINT')
        
        if fp:
            fp_ban_info = BanService.get_fp_ban_info(fp)
            
            # Agar user va fingerprint mapping bo'lsa, set up mapping
            if user and not ban_info:
                BanService.map_fp_to_user(fp, user)
        
        ctx = {
            "path_attempted": path_attempted,
            "ban_info": ban_info,
            "fp_ban_info": fp_ban_info,
            "user": user,
            "device_fingerprint": fp[:8] + '...' if fp and len(fp) > 8 else fp,
        }
        
        if ban_info:
            ctx.update({
                "ban_reason": ban_info.get('ban_reason', 'Noma\'lum'),
                "banned_for": ban_info.get('banned_for', 'Noma\'lum'),
                "ban_until": ban_info.get('ban_until'),
                "is_permanent": ban_info.get('is_permanent', False),
            })
        
        if fp_ban_info:
            ctx.update({
                "fp_ban_reason": fp_ban_info.get('ban_reason', 'Noma\'lum'),
                "fp_banned_for": fp_ban_info.get('banned_for', 'Noma\'lum'),
                "fp_ban_expires_at": fp_ban_info.get('ban_expires_at'),
                "fp_is_permanent": fp_ban_info.get('is_permanent', False),
            })
        
        return render(request, "security/not_allowed.html", ctx)
    except Exception as e:
        logger.error(f"Error in not_allowed: {str(e)}")
        return render(request, "security/not_allowed.html", {
            "path_attempted": request.path,
            "error": "Xatolik yuz berdi"
        })


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def delivery_list(request):
    """Delivery list page for admin"""
    try:
        drivers = DeliveryDriver.objects.select_related("user").all().order_by("id")
        ctx = {"drivers": drivers}
        return render(request, "dashboard/delivery/list.html", ctx)
    except Exception as e:
        logger.error(f"Error in delivery_list: {str(e)}")
        messages.error(request, "Haydovchilar ro'yxatini yuklashda xatolik yuz berdi.")
        return render(request, "dashboard/delivery/list.html", {"drivers": []})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def delivery_create(request):
    if request.method == "POST":
        form = DeliveryDriverForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Haydovchi muvaffaqiyatli yaratildi.")
            return redirect("dashboard:delivery_list")
    else:
        form = DeliveryDriverForm()
    return render(request, "dashboard/delivery/form.html", {"form": form})


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def delivery_edit(request, pk):
    driver = get_object_or_404(DeliveryDriver, pk=pk)
    if request.method == "POST":
        form = DeliveryDriverForm(request.POST, request.FILES, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, "Haydovchi muvaffaqiyatli yangilandi.")
            return redirect("dashboard:delivery_list")
    else:
        form = DeliveryDriverForm(instance=driver)
    return render(
        request, "dashboard/delivery/form.html", {"form": form, "driver": driver}
    )


def is_deliverer(user):
    """
    Return True if the user has a related Deliverer profile.
    """
    try:
        return hasattr(user, "deliverer") and user.deliverer is not None
    except Exception:
        return False



@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET"])
def ban_list(request):
    """Ban records ro'yxati - BanRecord model uchun."""
    try:
        from django.utils import timezone
        from security.models import BanRecord
        
        # Barcha ban records
        bans = BanRecord.objects.select_related('user').order_by('-created_at')
        
        # Stats
        total_bans = bans.count()
        active_bans = bans.filter(is_active=True).count()
        permanent_bans = bans.filter(ban_type='permanent').count()
        temporary_bans = bans.filter(ban_type='temporary').count()
        
        ctx = {
            "bans": bans,
            "total_bans": total_bans,
            "active_bans": active_bans,
            "permanent_bans": permanent_bans,
            "temporary_bans": temporary_bans,
            "now": timezone.now(),
        }
        return render(request, "dashboard/bans/list.html", ctx)
    except Exception as query_error:
        logger.error(f"Database query error in ban_list: {str(query_error)}")
        messages.error(request, "Banlar ro'yxatini yuklashda xatolik yuz berdi.")
        return render(request, "dashboard/bans/list.html", {
            "bans": [],
            "total_bans": 0,
            "active_bans": 0,
            "permanent_bans": 0,
            "temporary_bans": 0,
        })


# ═══════ BAN CRUD VIEWS ═══════

@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def ban_create(request):
    """Ban yaratish."""
    try:
        if request.method == "POST":
            try:
                from security.models import BanRecord
                from django.utils import timezone
                
                ban_type = request.POST.get('ban_type', 'temporary')
                reason = request.POST.get('reason', '')
                ip = request.POST.get('ip', '').strip()
                fingerprint = request.POST.get('fingerprint', '').strip()
                user_id = request.POST.get('user', '')
                expires_days = request.POST.get('expires_days', '')
                
                # Validate input
                if not ip and not fingerprint and not user_id:
                    messages.error(request, "IP, fingerprint yoki user kerak")
                    return render(request, "dashboard/bans/form.html", {"form": request.POST})
                
                # Create ban
                ban = BanRecord.objects.create(
                    ban_type=ban_type,
                    reason=reason,
                    ip=ip if ip else None,
                    fingerprint=fingerprint if fingerprint else None,
                    user_id=user_id if user_id else None,
                )
                
                if ban_type == 'temporary' and expires_days:
                    from datetime import timedelta
                    ban.expires_at = timezone.now() + timedelta(days=int(expires_days))
                    ban.save()
                
                messages.success(request, "Ban muvaffaqiyatli yaratildi.")
                return redirect("dashboard:ban_list")
            except Exception as save_error:
                logger.error(f"Error saving ban: {str(save_error)}")
                messages.error(request, "Banni saqlashda xatolik yuz berdi.")
        else:
            from custom_auth.models import CustomUser
            all_users = CustomUser.objects.all().order_by('email')
            return render(request, "dashboard/bans/form.html", {
                "all_users": all_users,
                "expires_days": 7
            })
    except Exception as e:
        logger.error(f"Error in ban_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik.")
        return redirect("dashboard:ban_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def ban_edit(request, pk):
    """Ban tahrirlash."""
    try:
        from security.models import BanRecord
        ban = get_object_or_404(BanRecord, pk=pk)
        
        if request.method == "POST":
            try:
                ban.ban_type = request.POST.get('ban_type', ban.ban_type)
                ban.reason = request.POST.get('reason', ban.reason)
                ban.ip = request.POST.get('ip', ban.ip or '')
                ban.fingerprint = request.POST.get('fingerprint', ban.fingerprint or '')
                
                expires_days = request.POST.get('expires_days', '')
                if ban.ban_type == 'temporary' and expires_days:
                    from datetime import timedelta
                    from django.utils import timezone
                    ban.expires_at = timezone.now() + timedelta(days=int(expires_days))
                else:
                    ban.expires_at = None
                
                ban.save()
                messages.success(request, "Ban muvaffaqiyatli yangilandi.")
                return redirect("dashboard:ban_list")
            except Exception as save_error:
                logger.error(f"Error updating ban: {str(save_error)}")
                messages.error(request, "Banni yangilashda xatolik.")
        else:
            from custom_auth.models import CustomUser
            all_users = CustomUser.objects.all().order_by('email')
            ctx = {"ban": ban, "all_users": all_users}
            return render(request, "dashboard/bans/form.html", ctx)
    except Exception as e:
        logger.error(f"Error in ban_edit: {str(e)}")
        messages.error(request, "Noma'lum xatolik.")
        return redirect("dashboard:ban_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def ban_toggle_status(request, pk):
    """Ban statusini almashtirish (Faol/O'chirilgan)."""
    try:
        from security.models import BanRecord
        ban = get_object_or_404(BanRecord, pk=pk)
        ban.is_active = not ban.is_active
        ban.save()
        status_text = "Faol" if ban.is_active else "O'chirilgan"
        messages.success(request, f"Ban statusi {status_text} qilindi.")
    except Exception as e:
        logger.error(f"Error toggling ban status: {str(e)}")
        messages.error(request, "Statusni almashtirishda xatolik.")
    
    return redirect("dashboard:ban_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def ban_delete(request, pk):
    """Ban o'chirish."""
    try:
        from security.models import BanRecord
        ban = get_object_or_404(BanRecord, pk=pk)
        ban_name = str(ban)
        ban.delete()
        messages.success(request, f"'{ban_name}' ban muvaffaqiyatli o'chirildi.")
    except Exception as e:
        logger.error(f"Error deleting ban: {str(e)}")
        messages.error(request, "Banni o'chirishda xatolik.")
    
    return redirect("dashboard:ban_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET"])
def ban_view(request, pk):
    """Ban ma'lumotlarini ko'rish."""
    try:
        from security.models import BanRecord
        from django.utils import timezone
        ban = get_object_or_404(BanRecord, pk=pk)
        return render(request, "dashboard/bans/view.html", {
            "ban": ban,
            "now": timezone.now()
        })
    except Exception as e:
        logger.error(f"Error viewing ban: {str(e)}")
        messages.error(request, "Ban ma'lumotlarini yuklashda xatolik.")
        return redirect("dashboard:ban_list")


# ═══════ ORDER CRUD VIEWS ═══════

@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def order_create(request):
    """Order yaratish."""
    try:
        if request.method == "POST":
            try:
                form = OrderForm(request.POST)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            messages.success(request, "Buyurtma muvaffaqiyatli yaratildi.")
                            return redirect("dashboard:order_list")
                    except Exception as save_error:
                        logger.error(f"Error saving order: {str(save_error)}")
                        messages.error(request, "Buyurtmani saqlashda xatolik yuz berdi.")
                        return render(request, "dashboard/order/form.html", {"form": form})
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(request, "dashboard/order/form.html", {"form": form})
            except Exception as form_error:
                logger.error(f"Form processing error in order_create: {str(form_error)}")
                messages.error(request, "Buyurtma yaratishda xatolik yuz berdi.")
                form = OrderForm()
                return render(request, "dashboard/order/form.html", {"form": form})
        else:
            try:
                form = OrderForm()
                ctx = {"form": form}
                return render(request, "dashboard/order/form.html", ctx)
            except Exception as get_error:
                logger.error(f"Error loading form in order_create: {str(get_error)}")
                messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                return redirect("dashboard:order_list")
    except Exception as e:
        logger.error(f"Unexpected error in order_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:order_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def order_edit(request, pk):
    """Order tahrirlash."""
    try:
        try:
            order = get_object_or_404(Order, pk=pk)

            if request.method == "POST":
                try:
                    form = OrderForm(request.POST, instance=order)
                    if form.is_valid():
                        try:
                            with transaction.atomic():
                                form.save()
                                messages.success(request, "Buyurtma muvaffaqiyatli yangilandi.")
                                return redirect("dashboard:order_list")
                        except Exception as save_error:
                            logger.error(f"Error updating order: {str(save_error)}")
                            messages.error(request, "Buyurtmani yangilashda xatolik yuz berdi.")
                            return render(
                                request,
                                "dashboard/order/form.html",
                                {"form": form, "order": order},
                            )
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(
                            request,
                            "dashboard/order/form.html",
                            {"form": form, "order": order},
                        )
                except Exception as form_error:
                    logger.error(f"Form processing error in order_edit: {str(form_error)}")
                    messages.error(request, "Buyurtma yangilashda xatolik yuz berdi.")
                    form = OrderForm(instance=order)
                    return render(
                        request,
                        "dashboard/order/form.html",
                        {"form": form, "order": order},
                    )
            else:
                try:
                    form = OrderForm(instance=order)
                    ctx = {"form": form, "order": order}
                    return render(request, "dashboard/order/form.html", ctx)
                except Exception as get_error:
                    logger.error(f"Error loading form in order_edit: {str(get_error)}")
                    messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                    return redirect("dashboard:order_list")

        except Exception as query_error:
            logger.error(f"Database query error in order_edit: {str(query_error)}")
            messages.error(request, "Buyurtmani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:order_list")

    except Exception as e:
        logger.error(f"Unexpected error in order_edit: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:order_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET"])
def order_view(request, pk):
    """Order ko'rish (detail view)."""
    try:
        try:
            order = get_object_or_404(Order, pk=pk)
            ctx = {"order": order}
            return render(request, "dashboard/order/view.html", ctx)
        except Exception as query_error:
            logger.error(f"Database query error in order_view: {str(query_error)}")
            messages.error(request, "Buyurtmani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:order_list")
    except Exception as e:
        logger.error(f"Unexpected error in order_view: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:order_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def order_delete(request, pk):
    """Order o'chirish."""
    try:
        try:
            order = get_object_or_404(Order, pk=pk)

            try:
                with transaction.atomic():
                    order_id = order.id
                    order.delete()
                    messages.success(request, f"Buyurtma #{order_id} muvaffaqiyatli o'chirildi.")
                    return redirect("dashboard:order_list")
            except Exception as delete_error:
                logger.error(f"Error deleting order: {str(delete_error)}")
                messages.error(request, "Buyurtmani o'chirishda xatolik yuz berdi.")
                return redirect("dashboard:order_list")

        except Exception as query_error:
            logger.error(f"Database query error in order_delete: {str(query_error)}")
            messages.error(request, "Buyurtmani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:order_list")

    except Exception as e:
        logger.error(f"Unexpected error in order_delete: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:order_list")



# ═══════ USER DELETE VIEW ═══════

@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def user_delete(request, pk):
    """Foydalanuvchini o'chirish."""
    try:
        try:
            user = get_object_or_404(CustomUser, pk=pk)

            try:
                with transaction.atomic():
                    user_display = user.full_name or user.email or user.phone_number
                    user.delete()
                    messages.success(
                        request,
                        f"'{user_display}' foydalanuvchi muvaffaqiyatli o'chirildi.",
                    )
                    return redirect("dashboard:user_list")
            except Exception as delete_error:
                logger.error(f"Error deleting user: {str(delete_error)}")
                messages.error(request, "Foydalanuvchini o'chirishda xatolik yuz berdi.")
                return redirect("dashboard:user_list")

        except Exception as query_error:
            logger.error(f"Database query error in user_delete: {str(query_error)}")
            messages.error(request, "Foydalanuvchini yuklashda xatolik yuz berdi.")
            return redirect("dashboard:user_list")

    except Exception as e:
        logger.error(f"Unexpected error in user_delete: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:user_list")



# ═══════ DELIVERY DELETE VIEW ═══════

@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["POST"])
def delivery_delete(request, pk):
    """Yetkazib beruvchini o'chirish."""
    try:
        try:
            driver = get_object_or_404(DeliveryDriver, pk=pk)

            try:
                with transaction.atomic():
                    driver_name = driver.user.full_name if driver.user else "Noma'lum haydovchi"
                    driver.delete()
                    messages.success(
                        request,
                        f"'{driver_name}' yetkazib beruvchi muvaffaqiyatli o'chirildi.",
                    )
                    return redirect("dashboard:delivery_list")
            except Exception as delete_error:
                logger.error(f"Error deleting delivery driver: {str(delete_error)}")
                messages.error(request, "Yetkazib beruvchini o'chirishda xatolik yuz berdi.")
                return redirect("dashboard:delivery_list")

        except Exception as query_error:
            logger.error(f"Database query error in delivery_delete: {str(query_error)}")
            messages.error(request, "Yetkazib beruvchini yuklashda xatolik yuz berdi.")
            return redirect("dashboard:delivery_list")

    except Exception as e:
        logger.error(f"Unexpected error in delivery_delete: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:delivery_list")
