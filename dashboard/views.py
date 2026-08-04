from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponseForbidden
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import logging

import os
import traceback
from django.utils import timezone
from django.contrib.auth import get_user_model

from users.models import CustomUser, Deliverer
from pharmacy.models import Category, Medicine
from orders.models import Order
from security.models import AuditLog
from .forms import (
    CategoryForm,
    MedicineForm,
    UserForm,
    AccountSettingsForm,
    DelivererOrderStatusForm,
)

logger = logging.getLogger(__name__)


def log_dashboard_error(component: str, user=None, error=None, action: str = ""):
    try:
        timestamp = timezone.now().isoformat()
        user_id = getattr(user, "id", "N/A") if user else "N/A"
        email = getattr(user, "email", "") or ""
        masked_email = f"{email[:1]}***@{email.split('@')[-1]}" if email and "@" in email else ("***" if email else "N/A")
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
            os.path.join(settings.BASE_DIR, 'media'),
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
        return user.is_authenticated and user.is_staff
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False


def is_deliverer(user):
    try:
        return user.is_authenticated and hasattr(user, "deliverer_profile") and user.deliverer_profile is not None
    except Exception as e:
        logger.error(f"Error checking deliverer status: {str(e)}")
        return False


def is_admin_or_deliverer(user):
    try:
        return is_admin(user) or is_deliverer(user)
    except Exception as e:
        logger.error(f"Error checking admin or deliverer status: {str(e)}")
        return False


def login_page(request):
    try:
        if request.method == "POST":
            try:
                identifier = request.POST.get("username", "").strip() or request.POST.get("email", "").strip() or request.POST.get("phone", "").strip()
                password = request.POST.get("password", "").strip()

                if not identifier or not password:
                    messages.error(request, "Login va parol majburiy.")
                    return render(request, "dashboard/login.html", {})

                # Authenticate using standard authenticate
                user = authenticate(request, username=identifier, password=password)

                # Fallback: if auth fails, search by email or phone + password
                if user is None:
                    user = find_and_authenticate_by_identifier(request, identifier, password)

                if user is not None:
                    try:
                        login(request, user)
                        full_name = getattr(user, 'full_name', None) or getattr(user, 'email', None) or "User"
                        messages.success(request, f"Xush kelibsiz, {full_name}!")

                        if is_admin(user):
                            return redirect("dashboard:dashboard-admin")
                        elif is_deliverer(user):
                            return redirect("dashboard:deliverer_dashboard")
                        else:
                            messages.error(request, "Sizda admin yoki yetkazib beruvchi huquqlari yo'q.")
                            logout(request)
                            return redirect("/auth/")
                    except Exception as login_error:
                        log_dashboard_error("login_page", user, login_error, action="Login failed during login(request, user)")
                        messages.error(request, "Login jarayonida xatolik yuz berdi.")
                        return render(request, "dashboard/login.html", {})
                else:
                    messages.error(request, "Noto'g'ri login yoki parol.")
                    return redirect("/auth/")

            except Exception as post_error:
                log_dashboard_error("login_page", None, post_error, action="POST processing error in login_page")
                messages.error(request, "Login jarayonida xatolik yuz berdi.")
                return redirect("/auth/")

        if request.user.is_authenticated:
            try:
                if is_admin(request.user):
                    return redirect("dashboard:dashboard-admin")
                elif is_deliverer(request.user):
                    return redirect("dashboard:deliverer_dashboard")
                else:
                    messages.error(request, "Sizda admin yoki yetkazib beruvchi huquqlari yo'q.")
                    logout(request)
                    return redirect("/auth/")
            except Exception as auth_check_error:
                log_dashboard_error("login_page", request.user, auth_check_error, action="Redirected to /auth/")
                logout(request)
                return redirect("/auth/")

        ctx = {"user_display": get_user_display(request.user)}
        return render(request, "dashboard/login.html", ctx)

    except Exception as e:
        log_dashboard_error("login_page", getattr(request, 'user', None), e, action="Redirected to /auth/")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("/auth/")


@login_required_decorator(login_url="dashboard:login_page")
def logout_page(request):
    try:
        logout(request)
        messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
        return redirect("dashboard:login_page")
    except Exception as e:
        log_dashboard_error("logout_page", getattr(request, 'user', None), e, action="Error during logout")
        messages.error(request, "Logout jarayonida xatolik yuz berdi.")
        return redirect("dashboard:login_page")


def main_dashboard(request):
    try:
        user = request.user
        # Fallback check if user is Anonymous
        if not user or not getattr(user, 'is_authenticated', False):
            identifier = request.POST.get("username") or request.POST.get("email") or request.POST.get("phone")
            password = request.POST.get("password")
            if identifier and password:
                user = find_and_authenticate_by_identifier(request, identifier, password)

        if not user or not getattr(user, 'is_authenticated', False) or not is_admin_or_deliverer(user):
            return redirect("/auth/")

        user_display = get_user_display(user)

        try:
            total_categories = Category.objects.count()
            total_medicines = Medicine.objects.count()
            total_customers = CustomUser.objects.filter(
                is_staff=False, deliverer_profile__isnull=True
            ).count()
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status="Pending").count()
            delivered_orders = Order.objects.filter(status="Delivered").count()
            total_users = CustomUser.objects.count()
            total_deliverers = Deliverer.objects.count()
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
                "total_deliverers": total_deliverers,
                "out_of_stock": out_of_stock,
                "total_staff": total_staff,
            }
            return render(request, "dashboard/index.html", ctx)

        except Exception as query_error:
            log_dashboard_error("main_dashboard", user, query_error, action="Rendered dashboard index with default zero values")
            messages.error(request, "Dashboard ma'lumotlarini yuklashda xatolik yuz berdi.")
            ctx = {
                "user_display": user_display,
                "total_categories": 0,
                "total_medicines": 0,
                "total_customers": 0,
                "total_orders": 0,
                "pending_orders": 0,
                "delivered_orders": 0,
                "total_users": 0,
                "total_deliverers": 0,
                "out_of_stock": 0,
                "total_staff": 0,
            }
            return render(request, "dashboard/index.html", ctx)

    except Exception as e:
        log_dashboard_error("main_dashboard", getattr(request, 'user', None), e, action="Redirected to /auth/")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("/auth/")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def category_list(request):
    try:
        try:
            categories = Category.objects.all().order_by('id')
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
                            messages.success(request, "Kategoriya muvaffaqiyatli yaratildi.")
                            return redirect("dashboard:category_list")
                    except Exception as save_error:
                        logger.error(f"Error saving category: {str(save_error)}")
                        messages.error(request, "Kategoriyani saqlashda xatolik yuz berdi.")
                        return render(request, "dashboard/category/form.html", {"form": form})
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(request, "dashboard/category/form.html", {"form": form})

            except Exception as form_error:
                logger.error(f"Form processing error in category_create: {str(form_error)}")
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
                                messages.success(request, "Kategoriya muvaffaqiyatli yangilandi.")
                                return redirect("dashboard:category_list")
                        except Exception as save_error:
                            logger.error(f"Error updating category: {str(save_error)}")
                            messages.error(request, "Kategoriyani yangilashda xatolik yuz berdi.")
                            return render(request, "dashboard/category/form.html", {
                                "form": form,
                                "category": category
                            })
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(request, "dashboard/category/form.html", {
                            "form": form,
                            "category": category
                        })

                except Exception as form_error:
                    logger.error(f"Form processing error in category_edit: {str(form_error)}")
                    messages.error(request, "Kategoriya yangilashda xatolik yuz berdi.")
                    form = CategoryForm(instance=category)
                    return render(request, "dashboard/category/form.html", {
                        "form": form,
                        "category": category
                    })
            else:
                try:
                    form = CategoryForm(instance=category)
                    ctx = {"form": form, "category": category}
                    return render(request, "dashboard/category/form.html", ctx)
                except Exception as get_error:
                    logger.error(f"Error loading form in category_edit: {str(get_error)}")
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
@require_http_methods(["GET", "POST"])
def category_delete(request, pk):
    try:
        try:
            category = get_object_or_404(Category, pk=pk)

            if request.method == "POST":
                try:
                    with transaction.atomic():
                        category_name = category.name
                        category.delete()
                        messages.success(request, f"'{category_name}' kategoriya muvaffaqiyatli o'chirildi.")
                        return redirect("dashboard:category_list")
                except Exception as delete_error:
                    logger.error(f"Error deleting category: {str(delete_error)}")
                    messages.error(request, "Kategoriyani o'chirishda xatolik yuz berdi.")
                    return redirect("dashboard:category_list")
            else:
                ctx = {"category": category}
                return render(request, "dashboard/category/list.html", ctx)

        except Exception as query_error:
            logger.error(f"Database query error in category_delete: {str(query_error)}")
            messages.error(request, "Kategoriyani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:category_list")

    except Exception as e:
        logger.error(f"Unexpected error in category_delete: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:category_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def medicine_list(request):
    try:
        try:
            medicines = Medicine.objects.all().order_by('id')
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
                        return render(request, "dashboard/product/form.html", {"form": form})
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                    return render(request, "dashboard/product/form.html", {"form": form})

            except Exception as form_error:
                logger.error(f"Form processing error in medicine_create: {str(form_error)}")
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
                                messages.success(request, "Dori muvaffaqiyatli yangilandi.")
                                return redirect("dashboard:medicine_list")
                        except Exception as save_error:
                            logger.error(f"Error updating medicine: {str(save_error)}")
                            messages.error(request, "Dorini yangilashda xatolik yuz berdi.")
                            return render(request, "dashboard/product/form.html", {
                                "form": form,
                                "medicine": medicine
                            })
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(request, "dashboard/product/form.html", {
                            "form": form,
                            "medicine": medicine
                        })

                except Exception as form_error:
                    logger.error(f"Form processing error in medicine_edit: {str(form_error)}")
                    messages.error(request, "Dori yangilashda xatolik yuz berdi.")
                    form = MedicineForm(instance=medicine)
                    return render(request, "dashboard/product/form.html", {
                        "form": form,
                        "medicine": medicine
                    })
            else:
                try:
                    form = MedicineForm(instance=medicine)
                    ctx = {"form": form, "medicine": medicine}
                    return render(request, "dashboard/product/form.html", ctx)
                except Exception as get_error:
                    logger.error(f"Error loading form in medicine_edit: {str(get_error)}")
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
@require_http_methods(["GET", "POST"])
def medicine_delete(request, pk):
    try:
        try:
            medicine = get_object_or_404(Medicine, pk=pk)

            if request.method == "POST":
                try:
                    with transaction.atomic():
                        medicine_name = medicine.name
                        medicine.delete()
                        messages.success(request, f"'{medicine_name}' dori muvaffaqiyatli o'chirildi.")
                        return redirect("dashboard:medicine_list")
                except Exception as delete_error:
                    logger.error(f"Error deleting medicine: {str(delete_error)}")
                    messages.error(request, "Dorini o'chirishda xatolik yuz berdi.")
                    return redirect("dashboard:medicine_list")
            else:
                ctx = {"medicine": medicine}
                return render(request, "dashboard/product/list.html", ctx)

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
        try:
            users = CustomUser.objects.all().order_by('id')
            ctx = {"users": users}
            return render(request, "dashboard/user/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Database query error in user_list: {str(query_error)}")
            messages.error(request, "Foydalanuvchilar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/user/list.html", {"users": []})

    except Exception as e:
        logger.error(f"Unexpected error in user_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
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
                            messages.success(request, "Foydalanuvchi muvaffaqiyatli yaratildi.")
                            return redirect("dashboard:user_list")
                    except Exception as save_error:
                        logger.error(f"Error saving user: {str(save_error)}")
                        messages.error(request, "Foydalanuvchini saqlashda xatolik yuz berdi.")
                        return render(request, "dashboard/user/form.html", {"form": form})
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
                                messages.success(request, "Foydalanuvchi muvaffaqiyatli yangilandi.")
                                return redirect("dashboard:user_list")
                        except Exception as save_error:
                            logger.error(f"Error updating user: {str(save_error)}")
                            messages.error(request, "Foydalanuvchini yangilashda xatolik yuz berdi.")
                            return render(request, "dashboard/user/form.html", {
                                "form": form,
                                "user": user
                            })
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(request, "dashboard/user/form.html", {
                            "form": form,
                            "user": user
                        })

                except Exception as form_error:
                    logger.error(f"Form processing error in user_edit: {str(form_error)}")
                    messages.error(request, "Foydalanuvchi yangilashda xatolik yuz berdi.")
                    form = UserForm(instance=user)
                    return render(request, "dashboard/user/form.html", {
                        "form": form,
                        "user": user
                    })
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
            orders = Order.objects.all().order_by('-created_at')
            ctx = {"orders": orders}
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
            audit_logs = AuditLog.objects.all().order_by('-timestamp')
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
@user_passes_test(is_admin_or_deliverer, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def account_settings(request):
    user = request.user
    if not user or not getattr(user, 'is_authenticated', False):
        logger.error("account_settings: unauthenticated or invalid request.user")
        messages.error(request, "Iltimos tizimga qayta kiring.")
        return redirect('dashboard:login_page')

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
                    messages.success(request, "Hisob sozlamalari muvaffaqiyatli yangilandi.")
                    return redirect("dashboard:account_settings")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                return render(request, "dashboard/account/settings.html", {"form": form, "user_display": user_display})
        else:
            form = AccountSettingsForm(instance=user)
            return render(request, "dashboard/account/settings.html", {"form": form, "user_display": user_display})

    except Exception as e:
        log_dashboard_error("account_settings", user, e, action="Redirected to login_page")
        messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
        return redirect('dashboard:login_page')


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def dashboard_customize(request):
    try:
        ctx = {"user_display": get_user_display(request.user)}
        return render(request, "dashboard/customize/index.html", ctx)
    except Exception as e:
        log_dashboard_error("dashboard_customize", getattr(request, 'user', None), e, action="Redirected to main_dashboard")
        messages.error(request, "Dashboard sozlamalarini yuklashda xatolik yuz berdi.")
        return redirect("dashboard:main_dashboard")
    except Exception as e:
        logger.error(f"Error in dashboard_customize: {str(e)}")
        messages.error(request, "Dashboard sozlamalarini yuklashda xatolik yuz berdi.")
        return redirect("dashboard:main_dashboard")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
def deliverer_dashboard(request):
    try:
        try:
            deliverer_profile = request.user.deliverer_profile
            if deliverer_profile is None:
                messages.error(request, "Yetkazib beruvchi profili topilmadi.")
                return redirect("dashboard:login_page")

            orders = Order.objects.filter(driver=deliverer_profile).order_by("-created_at")
            ctx = {
                "deliverer_profile": deliverer_profile,
                "orders": orders,
                "pending_orders": orders.filter(status="Assigned").count(),
                "accepted_orders": orders.filter(status="Accepted").count(),
                "delivered_orders": orders.filter(status="Delivered").count(),
            }
            return render(request, "dashboard/delivery/list.html", ctx)

        except Exception as query_error:
            logger.error(f"Database query error in deliverer_dashboard: {str(query_error)}")
            messages.error(request, "Buyurtmalar yuklashda xatolik yuz berdi.")
            ctx = {
                "deliverer_profile": None,
                "orders": [],
                "pending_orders": 0,
                "accepted_orders": 0,
                "delivered_orders": 0,
            }
            return render(request, "dashboard/delivery/list.html", ctx)

    except Exception as e:
        logger.error(f"Unexpected error in deliverer_dashboard: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:login_page")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
def deliverer_order_list(request):
    try:
        try:
            deliverer_profile = request.user.deliverer_profile
            if deliverer_profile is None:
                messages.error(request, "Yetkazib beruvchi profili topilmadi.")
                return redirect("dashboard:login_page")

            orders = Order.objects.filter(driver=deliverer_profile).order_by("-created_at")
            ctx = {"orders": orders}
            return render(request, "dashboard/delivery/list.html", ctx)

        except Exception as query_error:
            logger.error(f"Database query error in deliverer_order_list: {str(query_error)}")
            messages.error(request, "Buyurtmalar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/delivery/list.html", {"orders": []})

    except Exception as e:
        logger.error(f"Unexpected error in deliverer_order_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:login_page")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def deliverer_order_update(request, pk):
    try:
        try:
            deliverer_profile = request.user.deliverer_profile
            if deliverer_profile is None:
                messages.error(request, "Yetkazib beruvchi profili topilmadi.")
                return redirect("dashboard:login_page")

            order = get_object_or_404(Order, pk=pk, driver=deliverer_profile)

            if request.method == "POST":
                try:
                    form = DelivererOrderStatusForm(request.POST, instance=order)
                    if form.is_valid():
                        try:
                            with transaction.atomic():
                                form.save()
                                messages.success(
                                    request, f"Buyurtma #{order.id} statusi muvaffaqiyatli yangilandi."
                                )
                                return redirect("dashboard:deliverer_order_list")
                        except Exception as save_error:
                            logger.error(f"Error updating order status: {str(save_error)}")
                            messages.error(request, "Buyurtma statusini yangilashda xatolik yuz berdi.")
                            return render(request, "dashboard/delivery/update.html", {
                                "form": form,
                                "order": order
                            })
                    else:
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"{field}: {error}")
                        return render(request, "dashboard/delivery/update.html", {
                            "form": form,
                            "order": order
                        })

                except Exception as form_error:
                    logger.error(f"Form processing error in deliverer_order_update: {str(form_error)}")
                    messages.error(request, "Buyurtma statusini yangilashda xatolik yuz berdi.")
                    form = DelivererOrderStatusForm(instance=order)
                    return render(request, "dashboard/delivery/update.html", {
                        "form": form,
                        "order": order
                    })
            else:
                try:
                    form = DelivererOrderStatusForm(instance=order)
                    ctx = {"form": form, "order": order}
                    return render(request, "dashboard/delivery/update.html", ctx)
                except Exception as get_error:
                    logger.error(f"Error loading form in deliverer_order_update: {str(get_error)}")
                    messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                    return redirect("dashboard:deliverer_order_list")

        except Exception as query_error:
            logger.error(f"Database query error in deliverer_order_update: {str(query_error)}")
            messages.error(request, "Buyurtmani yuklashda xatolik yuz berdi.")
            return redirect("dashboard:deliverer_order_list")

    except Exception as e:
        logger.error(f"Unexpected error in deliverer_order_update: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:deliverer_order_list")


def not_allowed(request):
    try:
        from_page = request.GET.get("from", "noma'lum sahifa")
        ctx = {"from_page": from_page}
        return render(request, "dashboard/not_allowed.html", ctx)
    except Exception as e:
        logger.error(f"Error in not_allowed: {str(e)}")
        return render(request, "dashboard/not_allowed.html", {"from_page": "noma'lum"})


# ──────────────────────────────────────────────────────────────────────
# Delivery Dashboard Views
# ──────────────────────────────────────────────────────────────────────


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
def delivery_dashboard(request):
    """Main delivery dashboard page"""
    try:
        from datetime import datetime
        
        ctx = {
            "page_name": "dashboard",
            "page_title": "Asosiy",
            "current_time": datetime.now(),
        }
        return render(request, "delivery/dashboard.html", ctx)
    except Exception as e:
        logger.error(f"Error in delivery_dashboard: {str(e)}")
        messages.error(request, "Dashboard yuklashda xatolik yuz berdi.")
        return redirect("dashboard:login_page")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
def delivery_settings(request):
    """Delivery settings page"""
    try:
        ctx = {
            "page_name": "settings",
            "page_title": "Sozlamalar",
        }
        return render(request, "delivery/settings.html", ctx)
    except Exception as e:
        logger.error(f"Error in delivery_settings: {str(e)}")
        messages.error(request, "Sozlamalar yuklashda xatolik yuz berdi.")
        return redirect("dashboard:delivery_dashboard")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_deliverer, login_url="dashboard:not_allowed")
def delivery_map(request):
    """Delivery map page with placeholder for real-time map"""
    try:
        ctx = {
            "page_name": "map",
            "page_title": "Xarita",
        }
        return render(request, "delivery/map.html", ctx)
    except Exception as e:
        logger.error(f"Error in delivery_map: {str(e)}")
        messages.error(request, "Xarita yuklashda xatolik yuz berdi.")
        return redirect("dashboard:delivery_dashboard")
