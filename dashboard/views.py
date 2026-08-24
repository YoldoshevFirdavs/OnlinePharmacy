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
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from orders.models import Order, OrderItem
from pharmacy.models import Category, Medicine
from security.models import AuditLog
from users.models import CustomUser, DeliveryDriver, Seller

from .forms import AccountSettingsForm, CategoryForm, DeliveryDriverForm, MedicineForm, OrderForm, UserForm

logger = logging.getLogger(__name__)


def log_dashboard_error(component: str, user=None, error=None, action: str = ""):
    try:
        timestamp = timezone.now().isoformat()
        user_id = getattr(user, "id", "N/A") if user else "N/A"
        email = getattr(user, "email", "") or ""
        masked_email = (
            f"{email[:1]}***@{email.split('@')[-1]}" if email and "@" in email else ("***" if email else "N/A")
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
            "avatar_url": "/static/images/default/default_avatar.png",
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
        avatar_url = "/static/images/default/default_avatar.png"
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
        # Normalize login_url: prefer central /auth/ public login page
        if not login_url or str(login_url).lower() in (
            "dashboard:login_page",
            "login_page",
            "/dashboard/login/",
            "/login/",
        ):
            resolved_login = "/auth/"
        else:
            resolved_login = login_url

        actual_decorator = user_passes_test(
            lambda u: u.is_authenticated,
            redirect_field_name=redirect_field_name,
            login_url=resolved_login,
        )
        if function:
            return actual_decorator(function)
        return actual_decorator
    except Exception as e:
        logger.error(f"Error in login_required_decorator: {str(e)}")
        raise


def is_admin(user):
    try:
        return user.is_authenticated and getattr(user, "role", None) == "admin"
    except Exception as e:
        logger.error(f"Error checking admin status: {str(e)}")
        return False


def is_seller(user):
    try:
        return user.is_authenticated and getattr(user, "role", None) == "seller"
    except Exception as e:
        logger.error(f"Error checking seller status: {str(e)}")
        return False


def log_admin_history(request, action, meta, ip_address=None):
    """Record an admin action in the acting admin's personal history."""
    from pharmacy.models.history import CustomerUserHistory

    with transaction.atomic():
        CustomerUserHistory.objects.create(
            user=request.user,
            action=action,
            meta=meta,
            ip_address=ip_address or request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )


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
                    user = find_and_authenticate_by_identifier(request, identifier, password)

                if user is not None:
                    try:
                        login(request, user)
                        full_name = getattr(user, "full_name", None) or getattr(user, "email", None) or "User"
                        messages.success(request, f"Xush kelibsiz, {full_name}!")

                        if is_admin(user):
                            return redirect("dashboard:dashboard-admin")
                        elif is_seller(user):
                            return redirect("dashboard:seller_dashboard")  # Redirect to seller dashboard
                        else:
                            messages.error(request, "Sizda admin yoki sotuvchi huquqlari yo'q.")
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
                    return redirect("dashboard:seller_dashboard")  # Redirect to seller dashboard
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
            identifier = request.POST.get("username") or request.POST.get("email") or request.POST.get("phone")
            password = request.POST.get("password")
            if identifier and password:
                user = find_and_authenticate_by_identifier(request, identifier, password)

        if not user or not getattr(user, "is_authenticated", False) or not is_admin(user):
            return redirect("/auth/")

        user_display = get_user_display(user)

        try:
            total_categories = Category.objects.count()
            total_medicines = Medicine.objects.count()
            total_customers = CustomUser.objects.filter(is_staff=False, seller__isnull=True).count()
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
@user_passes_test(is_seller, login_url="dashboard:not_allowed")  # Protected by is_seller
def seller_dashboard(request):
    try:
        user = request.user
        if not user or not getattr(user, "is_authenticated", False) or not is_seller(user):
            return redirect("/auth/")

        user_display = get_user_display(user)
        # You can add seller-specific data here if needed
        ctx = {
            "user_display": user_display,
            "seller_name": (user.seller.shop_name if hasattr(user, "seller") else user.full_name),
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
            from django.core.paginator import Paginator

            categories = Category.objects.annotate(medicine_count=Count("medicines")).all().order_by("id")

            # Server-side pagination: 50 items per page
            paginator = Paginator(categories, 50)
            page_number = request.GET.get("page", 1)
            page_obj = paginator.get_page(page_number)

            ctx = {
                "categories": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            }
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
                    logger.error(f"Form processing error in category_edit: {str(form_error)}")
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
@require_http_methods(["POST"])
def category_delete(request, pk):
    try:
        category = get_object_or_404(Category, pk=pk)
        with transaction.atomic():
            category_name = category.name

            # Create undo log BEFORE deleting to capture fields reliably
            from security.models import UndoLog

            try:
                UndoLog.create_for_delete(category, "category", deleted_by=request.user)
            except Exception as undo_error:
                logger.warning(f"Failed to create undo log for category: {str(undo_error)}")

            # Delete the category
            category.delete()

            # AuditLog creation scheduled after commit to avoid breaking main transaction
            if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                def _audit_and_history_cat():
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action=f"Category deleted",
                            description=f"Category '{category_name}' (ID: {category.id}) deleted by {request.user.email}",
                            ip_address=request.META.get("REMOTE_ADDR"),
                            target_type="category",
                            target_id=category.id,
                            meta={"name": category_name},
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to create audit log for category delete: {str(audit_error)}")
                    try:
                        log_admin_history(
                            request,
                            "admin_delete",
                            {"entity": "category", "entity_id": category.id, "name": category_name},
                        )
                    except Exception as history_error:
                        logger.warning(f"Failed to create history log for category delete: {str(history_error)}")

                try:
                    transaction.on_commit(_audit_and_history_cat)
                except Exception as schedule_err:
                    logger.warning(f"Failed to schedule audit/history for category delete: {schedule_err}")

            # AJAX response yoki page redirect
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": f"'{category_name}' o'chirildi",
                        "undo_url": "/dashboard/api/admin/undo-delete/",
                    }
                )
            else:
                messages.success(
                    request,
                    f"'{category_name}' kategoriya muvaffaqiyatli o'chirildi.",
                )
                return redirect("dashboard:category_list")
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        error_msg = "Kategoriyani o'chirishda xatolik yuz berdi."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        else:
            messages.error(request, error_msg)
            return redirect("dashboard:category_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def medicine_list(request):
    try:
        try:
            from django.core.paginator import Paginator

            medicines = Medicine.objects.all().order_by("id")

            # Server-side pagination: 50 items per page
            paginator = Paginator(medicines, 50)
            page_number = request.GET.get("page", 1)
            page_obj = paginator.get_page(page_number)

            ctx = {
                "medicines": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
            }
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
                    logger.error(f"Form processing error in medicine_edit: {str(form_error)}")
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
@require_http_methods(["POST"])
def medicine_delete(request, pk):
    try:
        try:
            medicine = get_object_or_404(Medicine, pk=pk)

            try:
                with transaction.atomic():
                    medicine_name = medicine.name

                    # Create undo log BEFORE deleting to ensure we capture all fields
                    from security.models import UndoLog

                    try:
                        UndoLog.create_for_delete(medicine, "medicine", deleted_by=request.user)
                    except Exception as undo_error:
                        logger.warning(f"Failed to create undo log for medicine: {str(undo_error)}")

                    # Delete the medicine record
                    medicine.delete()

                    # AuditLog creation scheduled after commit to avoid breaking main transaction
                    if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                        def _audit_and_history_med():
                            try:
                                AuditLog.objects.create(
                                    user=request.user,
                                    action=f"Medicine deleted",
                                    description=f"Medicine '{medicine_name}' (ID: {medicine.id}) deleted by {request.user.email}",
                                    ip_address=request.META.get("REMOTE_ADDR"),
                                    target_type="medicine",
                                    target_id=medicine.id,
                                    meta={"name": medicine_name},
                                )
                            except Exception as audit_error:
                                logger.warning(f"Failed to create audit log for medicine delete: {str(audit_error)}")
                            try:
                                log_admin_history(
                                    request,
                                    "admin_delete",
                                    {"entity": "medicine", "entity_id": medicine.id, "name": medicine_name},
                                )
                            except Exception as history_error:
                                logger.warning(
                                    f"Failed to create history log for medicine delete: {str(history_error)}"
                                )

                        try:
                            transaction.on_commit(_audit_and_history_med)
                        except Exception as schedule_err:
                            logger.warning(f"Failed to schedule audit/history for medicine delete: {schedule_err}")

                    # AJAX response yoki page redirect
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"'{medicine_name}' o'chirildi",
                                "undo_url": "/dashboard/api/admin/undo-delete/",
                            }
                        )
                    else:
                        messages.success(
                            request,
                            f"'{medicine_name}' dori muvaffaqiyatli o'chirildi.",
                        )
                        return redirect("dashboard:medicine_list")
            except Exception as delete_error:
                logger.error(f"Error deleting medicine: {str(delete_error)}")
                error_msg = "Dorini o'chirishda xatolik yuz berdi."

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
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
        from django.core.paginator import Paginator

        users = CustomUser.objects.select_related("seller").all().order_by("id")
        for user in users:
            if user.is_staff:
                user.real_role = "Admin"
            elif hasattr(user, "seller") and user.seller is not None:
                user.real_role = "Seller"
            else:
                user.real_role = "Foydalanuvchi"

        # Server-side pagination: 50 items per page
        paginator = Paginator(users, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        ctx = {
            "users": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
        }
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
                    logger.error(f"Form processing error in user_edit: {str(form_error)}")
                    messages.error(request, "Foydalanuvchi yangilashda xatolik yuz berdi.")
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
            from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

            # Get params
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 25)
            search = request.GET.get("search", "")
            status = request.GET.get("status", "")
            sort = request.GET.get("sort", "-created_at")

            # Validate sort parameter
            allowed_sorts = ["id", "-id", "created_at", "-created_at"]
            if sort not in allowed_sorts:
                sort = "-created_at"

            # Base query - use 'user' not 'customer' (model uses user field)
            orders = Order.objects.select_related("user").order_by(sort)

            # Filter by status
            if status:
                orders = orders.filter(status=status)

            # Search - use 'user' not 'customer'
            if search:
                from django.db.models import Q

                orders = orders.filter(
                    Q(id__icontains=search) | Q(user__email__icontains=search) | Q(user__full_name__icontains=search)
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
                "sort": sort,
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
            from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 25)
            try:
                page_size = int(page_size)
            except (TypeError, ValueError):
                page_size = 25
            page_size = max(1, min(page_size, 50))

            queryset = AuditLog.objects.select_related("user").order_by("-timestamp")
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages or 1)

            ctx = {
                "audit_logs": page_obj.object_list,
                "page_obj": page_obj,
                "page_size": page_size,
                "total_logs": paginator.count,
            }
            return render(request, "dashboard/audit/list.html", ctx)
        except Exception as query_error:
            logger.error(f"Error in audit_log_list: {str(query_error)}")
            messages.error(request, "Audit loglar yuklashda xatolik yuz berdi.")
            return render(request, "dashboard/audit/list.html", {"audit_logs": [], "page_obj": None})

    except Exception as e:
        logger.error(f"Unexpected error in audit_log_list: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return render(request, "dashboard/audit/list.html", {"audit_logs": [], "page_obj": None})


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
                    messages.success(request, "Hisob sozlamalari muvaffaqiyatli yangilandi.")
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
        log_dashboard_error("account_settings", user, e, action="Redirected to login_page")
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
        fp = getattr(request, "device_fingerprint", None)
        if not fp:
            fp = request.COOKIES.get("device_fp") or request.META.get("HTTP_AUTHORIZATION_FINGERPRINT")

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
            "device_fingerprint": fp[:8] + "..." if fp and len(fp) > 8 else fp,
        }

        if ban_info:
            ctx.update(
                {
                    "ban_reason": ban_info.get("ban_reason", "Noma'lum"),
                    "banned_for": ban_info.get("banned_for", "Noma'lum"),
                    "ban_until": ban_info.get("ban_until"),
                    "is_permanent": ban_info.get("is_permanent", False),
                }
            )

        if fp_ban_info:
            ctx.update(
                {
                    "fp_ban_reason": fp_ban_info.get("ban_reason", "Noma'lum"),
                    "fp_banned_for": fp_ban_info.get("banned_for", "Noma'lum"),
                    "fp_ban_expires_at": fp_ban_info.get("ban_expires_at"),
                    "fp_is_permanent": fp_ban_info.get("is_permanent", False),
                }
            )

        return render(request, "security/not_allowed.html", ctx)
    except Exception as e:
        logger.error(f"Error in not_allowed: {str(e)}")
        return render(
            request, "security/not_allowed.html", {"path_attempted": request.path, "error": "Xatolik yuz berdi"}
        )


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
def delivery_list(request):
    """Delivery list page for admin"""
    try:
        from django.core.paginator import Paginator

        drivers = DeliveryDriver.objects.select_related("user").all().order_by("id")

        # Server-side pagination: 50 items per page
        paginator = Paginator(drivers, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        ctx = {
            "drivers": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
        }
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
    return render(request, "dashboard/delivery/form.html", {"form": form, "driver": driver})


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
        from django.core.paginator import Paginator
        from django.utils import timezone

        from security.models import BanRecord

        # Barcha ban records
        bans = BanRecord.objects.select_related("user").order_by("-created_at")

        # Server-side pagination: 50 items per page
        paginator = Paginator(bans, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Stats
        total_bans = paginator.count
        active_bans = bans.filter(is_active=True).count()
        permanent_bans = bans.filter(ban_type="permanent").count()
        temporary_bans = bans.filter(ban_type="temporary").count()

        ctx = {
            "bans": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
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
        return render(
            request,
            "dashboard/bans/list.html",
            {
                "bans": [],
                "total_bans": 0,
                "active_bans": 0,
                "permanent_bans": 0,
                "temporary_bans": 0,
            },
        )


# ═══════ BAN CRUD VIEWS ═══════


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def ban_create(request):
    """Ban yaratish."""
    try:
        if request.method == "POST":
            try:
                from datetime import timedelta

                from django.utils import timezone

                from security.models import BanRecord

                ban_type = request.POST.get("ban_type", "temporary")
                reason = request.POST.get("reason", "")
                ip = request.POST.get("ip", "").strip()
                fingerprint = request.POST.get("fingerprint", "").strip()
                user_id = request.POST.get("user", "")

                # Auto-generate fingerprint if not provided
                if not fingerprint and not ip and user_id:
                    # Generate unique fingerprint for this user's session
                    import hashlib
                    import uuid

                    unique_str = f"{user_id}_{uuid.uuid4().hex}"
                    fingerprint = hashlib.sha256(unique_str.encode()).hexdigest()[:32]

                # Get time value and unit
                expires_value = request.POST.get("expires_value", "")
                expires_unit = request.POST.get("expires_unit", "days")

                # Validate input
                if not ip and not fingerprint and not user_id:
                    messages.error(request, "IP, fingerprint yoki user kerak")
                    from users.models import CustomUser

                    all_users = CustomUser.objects.all().order_by("email")
                    return render(
                        request,
                        "dashboard/bans/form.html",
                        {"all_users": all_users, "expires_value": expires_value, "expires_unit": expires_unit},
                    )

                # Create ban
                ban = BanRecord.objects.create(
                    ban_type=ban_type,
                    reason=reason,
                    ip=ip if ip else None,
                    fingerprint=fingerprint if fingerprint else None,
                    user_id=user_id if user_id else None,
                )

                # Calculate expiry time
                if ban_type == "temporary" and expires_value:
                    try:
                        value = int(expires_value)
                        # Convert to seconds based on unit, then to timedelta
                        unit_to_seconds = {
                            "seconds": 1,
                            "minutes": 60,
                            "hours": 3600,
                            "days": 86400,
                            "weeks": 604800,
                            "months": 2592000,  # 30 days
                            "years": 31536000,  # 365 days
                        }

                        seconds = value * unit_to_seconds.get(expires_unit, 86400)
                        ban.expires_at = timezone.now() + timedelta(seconds=seconds)
                        ban.save()
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid time value: {expires_value}")
                        ban.save()

                messages.success(request, "Ban muvaffaqiyatli yaratildi.")
                return redirect("dashboard:ban_list")
            except Exception as save_error:
                logger.error(f"Error saving ban: {str(save_error)}")
                messages.error(request, "Banni saqlashda xatolik yuz berdi.")
        else:
            from users.models import CustomUser

            all_users = CustomUser.objects.all().order_by("email")
            return render(
                request,
                "dashboard/bans/form.html",
                {"all_users": all_users, "expires_value": 7, "expires_unit": "days"},
            )
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
        from datetime import timedelta

        from django.utils import timezone

        from security.models import BanRecord

        ban = get_object_or_404(BanRecord, pk=pk)

        if request.method == "POST":
            try:
                ban.ban_type = request.POST.get("ban_type", ban.ban_type)
                ban.reason = request.POST.get("reason", ban.reason)
                ban.ip = request.POST.get("ip", ban.ip or "")
                ban.fingerprint = request.POST.get("fingerprint", ban.fingerprint or "")

                # Get time value and unit
                expires_value = request.POST.get("expires_value", "")
                expires_unit = request.POST.get("expires_unit", "days")

                # Update expiry time for temporary bans
                if ban.ban_type == "temporary" and expires_value:
                    try:
                        value = int(expires_value)
                        unit_to_seconds = {
                            "seconds": 1,
                            "minutes": 60,
                            "hours": 3600,
                            "days": 86400,
                            "weeks": 604800,
                            "months": 2592000,
                            "years": 31536000,
                        }

                        seconds = value * unit_to_seconds.get(expires_unit, 86400)
                        ban.expires_at = timezone.now() + timedelta(seconds=seconds)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid time value: {expires_value}")
                else:
                    ban.expires_at = None

                ban.save()
                messages.success(request, "Ban muvaffaqiyatli yangilandi.")
                return redirect("dashboard:ban_list")
            except Exception as save_error:
                logger.error(f"Error updating ban: {str(save_error)}")
                messages.error(request, "Banni yangilashda xatolik.")
        else:
            from users.models import CustomUser

            all_users = CustomUser.objects.all().order_by("email")

            # Calculate current expires value and unit from expires_at
            expires_value = 7
            expires_unit = "days"
            if ban.expires_at:
                delta = ban.expires_at - timezone.now()
                total_seconds = delta.total_seconds()
                if total_seconds > 0:
                    # Try to use the most appropriate unit
                    if total_seconds >= 31536000:  # years
                        expires_value = int(total_seconds / 31536000)
                        expires_unit = "years"
                    elif total_seconds >= 2592000:  # months
                        expires_value = int(total_seconds / 2592000)
                        expires_unit = "months"
                    elif total_seconds >= 604800:  # weeks
                        expires_value = int(total_seconds / 604800)
                        expires_unit = "weeks"
                    elif total_seconds >= 86400:  # days
                        expires_value = int(total_seconds / 86400)
                        expires_unit = "days"
                    elif total_seconds >= 3600:  # hours
                        expires_value = int(total_seconds / 3600)
                        expires_unit = "hours"
                    elif total_seconds >= 60:  # minutes
                        expires_value = int(total_seconds / 60)
                        expires_unit = "minutes"
                    else:  # seconds
                        expires_value = int(total_seconds)
                        expires_unit = "seconds"

            ctx = {"ban": ban, "all_users": all_users, "expires_value": expires_value, "expires_unit": expires_unit}
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

        with transaction.atomic():
            # UndoLog yaratish (24 soat ichida qaytarish imkoniyati uchun)
            from security.models import UndoLog

            try:
                UndoLog.create_for_delete(ban, "ban", deleted_by=request.user)
            except Exception as undo_error:
                logger.warning(f"Failed to create undo log for ban: {str(undo_error)}")

            # AuditLog va log_admin_history transaction.on_commit ichida xavfsiz chaqiriladi
            if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                def _audit_and_history_ban():
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action="Ban deleted",
                            description=f"Ban '{ban_name}' (ID: {ban.id}) deleted by {request.user.email}",
                            ip_address=request.META.get("REMOTE_ADDR"),
                            target_type="ban",
                            target_id=ban.id,
                            meta={"entity_name": ban_name, "entity_type": "ban"},
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to create audit log for ban delete: {str(audit_error)}")
                    try:
                        log_admin_history(
                            request,
                            "admin_delete",
                            {"entity": "ban", "entity_id": ban.id, "name": ban_name},
                        )
                    except Exception as history_error:
                        logger.warning(f"Failed to create history log for ban delete: {str(history_error)}")

                transaction.on_commit(_audit_and_history_ban)

            ban.delete()

        # AJAX response yoki page redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": f"'{ban_name}' o'chirildi",
                    "undo_url": "/dashboard/api/admin/undo-delete/",
                }
            )
        else:
            messages.success(request, f"'{ban_name}' ban muvaffaqiyatli o'chirildi.")
            return redirect("dashboard:ban_list")
    except Exception as e:
        logger.error(f"Error deleting ban: {str(e)}")
        error_msg = "Banni o'chirishda xatolik."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        else:
            messages.error(request, error_msg)
            return redirect("dashboard:ban_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET"])
def ban_view(request, pk):
    """Ban ma'lumotlarini ko'rish."""
    try:
        from django.utils import timezone

        from security.models import BanRecord

        ban = get_object_or_404(BanRecord, pk=pk)
        return render(request, "dashboard/bans/view.html", {"ban": ban, "now": timezone.now()})
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
                import json

                from django.http import JsonResponse

                # Handle both form data and JSON
                if request.content_type == "application/json":
                    data = json.loads(request.body) if request.body else {}
                    user_id = data.get("user_id") or data.get("customer_id")
                    address = data.get("address", "")
                    items = data.get("items", [])

                    if not user_id or not items:
                        return JsonResponse({"status": "error", "message": "user_id and items required"}, status=400)

                    # Validate user
                    try:
                        customer = CustomUser.objects.get(id=user_id)
                    except CustomUser.DoesNotExist:
                        return JsonResponse({"status": "error", "message": "User not found"}, status=404)

                    with transaction.atomic():
                        order = Order.objects.create(user=customer, address=address, total_price=0)

                        total = 0
                        for item in items:
                            product_id = item.get("product_id")
                            quantity = item.get("quantity", 1)

                            try:
                                product = Medicine.objects.select_for_update().get(id=product_id)
                            except Medicine.DoesNotExist:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"status": "error", "message": f"Product {product_id} not found"}, status=400
                                )

                            if quantity > product.stock:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"status": "error", "message": f"Not enough stock for {product.name}"}, status=400
                                )

                            line_price = product.price * quantity
                            OrderItem.objects.create(
                                order=order, product=product, quantity=quantity, price_at_order=product.price
                            )

                            total += line_price
                            product.stock -= quantity
                            product.save()

                        order.total_price = total
                        order.save()

                    return JsonResponse(
                        {"status": "success", "order_id": order.id, "total_price": str(order.total_price)}, status=201
                    )
                else:
                    # Handle form data
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
                users = CustomUser.objects.filter(is_active=True).order_by("email")
                ctx = {"form": form, "users": users}
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
            order_items = order.order_items.select_related("product").all()
            ctx = {
                "order": order,
                "order_items": order_items,
            }
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
    """Order o'chirish - AJAX support bilan."""
    try:
        try:
            order = get_object_or_404(Order, pk=pk)

            try:
                with transaction.atomic():
                    order_id = order.id
                    # UndoLog yaratish (24 soat ichida qaytarish imkoniyati uchun)
                    from security.models import UndoLog

                    try:
                        UndoLog.create_for_delete(order, "order", deleted_by=request.user)
                    except Exception as undo_error:
                        logger.warning(f"Failed to create undo log for order: {str(undo_error)}")
                    order.delete()

                    # AuditLog va log_admin_history transaction.on_commit ichida xavfsiz chaqiriladi
                    if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                        def _audit_and_history_order():
                            try:
                                AuditLog.objects.create(
                                    user=request.user,
                                    action=f"Order deleted",
                                    description=f"Order #{order_id} deleted by {request.user.email}",
                                    ip_address=request.META.get("REMOTE_ADDR"),
                                    target_type="order",
                                    target_id=order_id,
                                    meta={"order_id": order_id},
                                )
                            except Exception as audit_error:
                                logger.warning(f"Failed to create audit log for order delete: {str(audit_error)}")
                            try:
                                log_admin_history(
                                    request,
                                    "admin_delete",
                                    {"entity": "order", "entity_id": order_id},
                                )
                            except Exception as history_error:
                                logger.warning(f"Failed to create history log for order delete: {str(history_error)}")

                        transaction.on_commit(_audit_and_history_order)

                    # AJAX response yoki page redirect
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"Buyurtma #{order_id} o'chirildi",
                                "undo_url": "/dashboard/api/admin/undo-delete/",
                            }
                        )
                    else:
                        messages.success(request, f"Buyurtma #{order_id} muvaffaqiyatli o'chirildi.")
                        return redirect("dashboard:order_list")
            except Exception as delete_error:
                logger.error(f"Error deleting order: {str(delete_error)}")
                error_msg = "Buyurtmani o'chirishda xatolik yuz berdi."

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("dashboard:order_list")

        except Exception as query_error:
            logger.error(f"Database query error in order_delete: {str(query_error)}")
            error_msg = "Buyurtmani yuklashda xatolik yuz berdi."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
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
                    user_id_val = user.id
                    user_display = user.full_name or user.email or user.phone_number
                    # UndoLog yaratish (24 soat ichida qaytarish imkoniyati uchun)
                    from security.models import UndoLog

                    try:
                        UndoLog.create_for_delete(user, "user", deleted_by=request.user)
                    except Exception as undo_error:
                        logger.warning(f"Failed to create undo log for user: {str(undo_error)}")
                    user.delete()

                    # AuditLog va log_admin_history transaction.on_commit ichida xavfsiz chaqiriladi
                    if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                        def _audit_and_history_user():
                            try:
                                AuditLog.objects.create(
                                    user=request.user,
                                    action=f"User deleted",
                                    description=f"User '{user_display}' (ID: {user_id_val}) deleted by {request.user.email}",
                                    ip_address=request.META.get("REMOTE_ADDR"),
                                    target_type="user",
                                    target_id=user_id_val,
                                    meta={"name": user_display},
                                )
                            except Exception as audit_error:
                                logger.warning(f"Failed to create audit log for user delete: {str(audit_error)}")
                            try:
                                log_admin_history(
                                    request,
                                    "admin_delete",
                                    {"entity": "user", "entity_id": user_id_val, "name": user_display},
                                )
                            except Exception as history_error:
                                logger.warning(f"Failed to create history log for user delete: {str(history_error)}")

                        transaction.on_commit(_audit_and_history_user)

                    # AJAX response yoki page redirect
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"'{user_display}' o'chirildi",
                                "undo_url": "/dashboard/api/admin/undo-delete/",
                            }
                        )
                    else:
                        messages.success(
                            request,
                            f"'{user_display}' foydalanuvchi muvaffaqiyatli o'chirildi.",
                        )
                        return redirect("dashboard:user_list")
            except Exception as delete_error:
                logger.error(f"Error deleting user: {str(delete_error)}")
                error_msg = "Foydalanuvchini o'chirishda xatolik yuz berdi."

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("dashboard:user_list")

        except Exception as query_error:
            logger.error(f"Database query error in user_delete: {str(query_error)}")
            error_msg = "Foydalanuvchini yuklashda xatolik yuz berdi."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("dashboard:user_list")

    except Exception as e:
        logger.error(f"Unexpected error in user_delete: {str(e)}")
        error_msg = "Noma'lum xatolik yuz berdi."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        else:
            messages.error(request, error_msg)
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
                    driver_id_val = driver.id
                    driver_name = driver.user.full_name if driver.user else "Noma'lum haydovchi"
                    # UndoLog yaratish (24 soat ichida qaytarish imkoniyati uchun)
                    from security.models import UndoLog

                    try:
                        UndoLog.create_for_delete(driver, "delivery", deleted_by=request.user)
                    except Exception as undo_error:
                        logger.warning(f"Failed to create undo log for delivery: {str(undo_error)}")
                    driver.delete()

                    # AuditLog va log_admin_history transaction.on_commit ichida xavfsiz chaqiriladi
                    if request.user.is_staff and request.user.is_superuser and request.user.role == "admin":

                        def _audit_and_history_driver():
                            try:
                                AuditLog.objects.create(
                                    user=request.user,
                                    action=f"Delivery driver deleted",
                                    description=f"Delivery driver '{driver_name}' (ID: {driver_id_val}) deleted by {request.user.email}",
                                    ip_address=request.META.get("REMOTE_ADDR"),
                                    target_type="delivery",
                                    target_id=driver_id_val,
                                    meta={"name": driver_name},
                                )
                            except Exception as audit_error:
                                logger.warning(f"Failed to create audit log for delivery delete: {str(audit_error)}")
                            try:
                                log_admin_history(
                                    request,
                                    "admin_delete",
                                    {"entity": "delivery", "entity_id": driver_id_val, "name": driver_name},
                                )
                            except Exception as history_error:
                                logger.warning(
                                    f"Failed to create history log for delivery delete: {str(history_error)}"
                                )

                        transaction.on_commit(_audit_and_history_driver)

                    # AJAX response yoki page redirect
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"'{driver_name}' o'chirildi",
                                "undo_url": "/dashboard/api/admin/undo-delete/",
                            }
                        )
                    else:
                        messages.success(
                            request,
                            f"'{driver_name}' yetkazib beruvchi muvaffaqiyatli o'chirildi.",
                        )
                        return redirect("dashboard:delivery_list")
            except Exception as delete_error:
                logger.error(f"Error deleting delivery driver: {str(delete_error)}")
                error_msg = "Yetkazib beruvchini o'chirishda xatolik yuz berdi."

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("dashboard:delivery_list")

        except Exception as query_error:
            logger.error(f"Database query error in delivery_delete: {str(query_error)}")
            error_msg = "Yetkazib beruvchini yuklashda xatolik yuz berdi."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("dashboard:delivery_list")

    except Exception as e:
        logger.error(f"Unexpected error in delivery_delete: {str(e)}")
        error_msg = "Noma'lum xatolik yuz berdi."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        else:
            messages.error(request, error_msg)
            return redirect("dashboard:delivery_list")


@login_required_decorator(login_url="dashboard:login_page")
@user_passes_test(is_admin, login_url="dashboard:not_allowed")
@require_http_methods(["GET", "POST"])
def order_create(request):
    """Order yaratish."""
    try:
        if request.method == "POST":
            try:
                import json

                from django.http import JsonResponse

                data = json.loads(request.body) if request.body else {}

                customer_id = data.get("customer_id")
                address = data.get("address", "")
                notes = data.get("notes", "")
                items = data.get("items", [])

                if not customer_id or not items or len(items) == 0:
                    return JsonResponse({"status": "error", "message": "customer_id and items required"}, status=400)

                from orders.models import Order, OrderItem
                from pharmacy.models import Medicine

                # Validate customer
                try:
                    customer = CustomUser.objects.get(id=customer_id)
                except CustomUser.DoesNotExist:
                    return JsonResponse({"status": "error", "message": "Customer not found"}, status=404)

                with transaction.atomic():
                    order = Order.objects.create(user=customer, address=address, notes=notes, total_price=0)

                    total = 0
                    for item in items:
                        product_id = item.get("product_id")
                        quantity = item.get("quantity", 1)

                        # Validate product
                        try:
                            product = Medicine.objects.select_for_update().get(id=product_id)
                        except Medicine.DoesNotExist:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"status": "error", "message": f"Product {product_id} not found"}, status=400
                            )

                        # Validate stock
                        if quantity > product.stock:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"status": "error", "message": f"Not enough stock for {product.name}"}, status=400
                            )

                        # Create order item
                        line_price = product.price * quantity
                        OrderItem.objects.create(
                            order=order, product=product, quantity=quantity, price_at_order=product.price
                        )

                        total += line_price
                        product.stock -= quantity
                        product.save()

                    order.total_price = total
                    order.save()

                return JsonResponse(
                    {"status": "success", "order_id": order.id, "total_price": str(order.total_price)}, status=201
                )

            except Exception as form_error:
                logger.error(f"Form processing error in order_create: {str(form_error)}")
                return JsonResponse({"status": "error", "message": str(form_error)}, status=400)
        else:
            # GET - Render create page
            try:
                from users.models import CustomUser

                users = CustomUser.objects.filter(is_active=True).order_by("email")
                ctx = {"users": users}
                return render(request, "dashboard/admin/orders_create.html", ctx)
            except Exception as get_error:
                logger.error(f"Error loading form in order_create: {str(get_error)}")
                messages.error(request, "Shaklni yuklashda xatolik yuz berdi.")
                return redirect("dashboard:order_list")
    except Exception as e:
        logger.error(f"Unexpected error in order_create: {str(e)}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect("dashboard:order_list")


# ═══════ SELLER PROFILE VIEW ═══════
@login_required_decorator(login_url="dashboard:login_page")
def seller_profile(request, seller_id):
    """Seller profile page - blog style"""
    from django.db.models import Avg, Count

    from pharmacy.models import Medicine

    seller = get_object_or_404(CustomUser, id=seller_id)

    # Seller products
    products = (
        Medicine.objects.filter(seller=seller, is_active=True)
        .annotate(avg_rating=Avg("average_rating"), review_count=Count("reviews"))
        .order_by("-created_at")
    )

    # Seller stats
    seller_stats = Medicine.objects.filter(seller=seller, is_active=True).aggregate(
        total_products=Count("id"), avg_rating=Avg("average_rating"), total_reviews=Count("reviews")
    )

    context = {
        "seller": seller,
        "products": products,
        "seller_stats": seller_stats,
    }

    return render(request, "dashboard/seller/profile.html", context)


# ═══════ FULL PRODUCT GUIDE VIEW ═══════
@login_required_decorator(login_url="dashboard:login_page")
def product_full_guide(request, product_id):
    """Full product information page"""
    product = get_object_or_404(Medicine, id=product_id)

    context = {
        "product": product,
    }

    return render(request, "dashboard/product/full_guide.html", context)
