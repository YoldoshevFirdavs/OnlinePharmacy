from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponseForbidden

from users.models import CustomUser, Deliverer
from pharmacy.models import Category, Medicine
from orders.models import Order
from .forms import CategoryForm, MedicineForm, UserForm, AccountSettingsForm, DelivererOrderStatusForm

# Custom login_required decorator
def login_required_decorator(function=None, redirect_field_name='next', login_url=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated,
        redirect_field_name=redirect_field_name,
        login_url=login_url
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

# --- Helper functions for role checks ---
def is_admin(user):
    return user.is_authenticated and user.is_staff

def is_deliverer(user):
    return user.is_authenticated and hasattr(user, 'deliverer_profile')

def is_admin_or_deliverer(user):
    return is_admin(user) or is_deliverer(user)

# --- Login/Logout Views ---

def login_page(request):
    if not request.user.is_authenticated:
        return redirect('/auth/') # Agar foydalanuvchi auth qilinmagan bo'lsa, /auth/ ga yo'naltirish

    # Agar foydalanuvchi auth qilingan bo'lsa, admin login sahifasini ko'rsatish
    if is_admin(request.user):
        # Admin allaqachon login bo'lgan bo'lsa, main_dashboard ga yo'naltirish
        return redirect('dashboard:main_dashboard')
    elif is_deliverer(request.user):
        # Deliverer allaqachon login bo'lgan bo'lsa, deliverer_dashboard ga yo'naltirish
        return redirect('dashboard:deliverer_dashboard')
    else:
        # Auth qilingan, lekin admin yoki deliverer emas
        messages.error(request, "Sizda admin yoki yetkazib beruvchi huquqlari yo'q.")
        logout(request)
        return redirect('/auth/') # Yoki boshqa tegishli sahifaga

    # Bu qismga kod yetib kelmasligi kerak, chunki yuqoridagi shartlar barcha holatlarni qamrab oladi.
    # Lekin agar qandaydir sabab bilan yetib kelsa, xatolikni oldini olish uchun.
    # Bu yerda POST requestni ham handle qilish kerak bo'ladi, agar form orqali login bo'lsa.
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.full_name or user.username}!")
            if is_admin(user):
                return redirect('dashboard:main_dashboard')
            elif is_deliverer(user):
                return redirect('dashboard:deliverer_dashboard')
            else:
                messages.error(request, "Sizda admin yoki yetkazib beruvchi huquqlari yo'q.")
                logout(request)
                return redirect('/auth/')
        else:
            messages.error(request, "Noto'g'ri login yoki parol.")
    
    ctx = {}
    return render(request, 'dashboard/login.html', ctx) # admin_login.html o'rniga login.html

@login_required_decorator(login_url='dashboard:login_page')
def logout_page(request):
    logout(request)
    messages.info(request, "Tizimdan chiqdingiz.")
    return redirect('dashboard:login_page')

# --- Admin Dashboard Views ---

@login_required(login_url='/auth/') # login_required decoratoridan foydalanish
def main_dashboard(request):
    if not is_admin(request.user):
        return redirect('dashboard:not_allowed')

    ctx = {
        'total_categories': Category.objects.count(),
        'total_medicines': Medicine.objects.count(),
        'total_customers': CustomUser.objects.filter(is_staff=False, deliverer_profile__isnull=True).count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='Pending').count(),
        'delivered_orders': Order.objects.filter(status='Delivered').count(),
    }
    return render(request, 'dashboard/index.html', ctx) # dashboard/base.html o'rniga dashboard/index.html

# Category CRUD
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def category_list(request):
    categories = Category.objects.all()
    ctx = {'categories': categories}
    return render(request, 'dashboard/category_list.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategoriya muvaffaqiyatli yaratildi.")
            return redirect('dashboard:category_list')
        else:
            messages.error(request, "Kategoriya yaratishda xato yuz berdi.")
    else:
        form = CategoryForm()
    ctx = {'form': form}
    return render(request, 'dashboard/category_form.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategoriya muvaffaqiyatli yangilandi.")
            return redirect('dashboard:category_list')
        else:
            messages.error(request, "Kategoriya yangilashda xato yuz berdi.")
    else:
        form = CategoryForm(instance=category)
    ctx = {'form': form, 'category': category}
    return render(request, 'dashboard/category_form.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Kategoriya muvaffaqiyatli o'chirildi.")
        return redirect('dashboard:category_list')
    ctx = {'category': category}
    return render(request, 'dashboard/category_confirm_delete.html', ctx)

# Medicine CRUD (Product CRUD o'rniga)
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def medicine_list(request):
    medicines = Medicine.objects.all()
    ctx = {'medicines': medicines}
    return render(request, 'dashboard/medicine_list.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Dori muvaffaqiyatli yaratildi.")
            return redirect('dashboard:medicine_list')
        else:
            messages.error(request, "Dori yaratishda xato yuz berdi.")
    else:
        form = MedicineForm()
    ctx = {'form': form}
    return render(request, 'dashboard/medicine_form.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, "Dori muvaffaqiyatli yangilandi.")
            return redirect('dashboard:medicine_list')
        else:
            messages.error(request, "Dori yangilashda xato yuz berdi.")
    else:
        form = MedicineForm(instance=medicine)
    ctx = {'form': form, 'medicine': medicine}
    return render(request, 'dashboard/medicine_form.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        medicine.delete()
        messages.success(request, "Dori muvaffaqiyatli o'chirildi.")
        return redirect('dashboard:medicine_list')
    ctx = {'medicine': medicine}
    return render(request, 'dashboard/medicine_confirm_delete.html', ctx)

# User CRUD
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def user_list(request):
    users = CustomUser.objects.all().order_by('id')
    ctx = {'users': users}
    return render(request, 'dashboard/user_list.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Foydalanuvchi muvaffaqiyatli yaratildi.")
            return redirect('dashboard:user_list')
        else:
            messages.error(request, "Foydalanuvchi yaratishda xato yuz berdi.")
    else:
        form = UserForm()
    ctx = {'form': form}
    return render(request, 'dashboard/user_form.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Foydalanuvchi muvaffaqiyatli yangilandi.")
            return redirect('dashboard:user_list')
        else:
            messages.error(request, "Foydalanuvchi yangilashda xato yuz berdi.")
    else:
        form = UserForm(instance=user)
    ctx = {'form': form, 'user': user}
    return render(request, 'dashboard/user_form.html', ctx)

# Order List (Admin)
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    ctx = {'orders': orders}
    return render(request, 'dashboard/order_list.html', ctx)

# Audit Log (Admin)
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def audit_log_list(request):
    # Audit log modelini yaratish kerak bo'ladi. Hozircha bo'sh ro'yxat
    audit_logs = [] # AuditLog.objects.all().order_by('-timestamp')
    ctx = {'audit_logs': audit_logs}
    return render(request, 'dashboard/audit_log_list.html', ctx)

# Account Settings (Admin & Deliverer)
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin_or_deliverer, login_url='dashboard:not_allowed')
def account_settings(request):
    user = request.user
    if request.method == 'POST':
        form = AccountSettingsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            new_password1 = form.cleaned_data.get('new_password1')
            if new_password1:
                user.set_password(new_password1)
            user.save()
            messages.success(request, "Hisob sozlamalari muvaffaqiyatli yangilandi.")
            return redirect('dashboard:account_settings')
        else:
            messages.error(request, "Hisob sozlamalarini yangilashda xato yuz berdi.")
    else:
        form = AccountSettingsForm(instance=user)
    
    ctx = {'form': form}
    return render(request, 'dashboard/account_settings.html', ctx)

# Dashboard Customize (Admin)
@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_admin, login_url='dashboard:not_allowed')
def dashboard_customize(request):
    # Bu yerda sidebar ranglari, iconlar, nomlar kabi sozlamalar bo'lishi mumkin
    # Hozircha oddiy template render qilinadi
    ctx = {}
    return render(request, 'dashboard/dashboard_customize.html', ctx)

# --- Deliverer Dashboard Views ---

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_deliverer, login_url='dashboard:not_allowed')
def deliverer_dashboard(request):
    deliverer_profile = request.user.deliverer_profile
    orders = Order.objects.filter(driver=deliverer_profile).order_by('-created_at')
    ctx = {
        'deliverer_profile': deliverer_profile,
        'orders': orders,
        'pending_orders': orders.filter(status='Assigned').count(),
        'accepted_orders': orders.filter(status='Accepted').count(),
        'delivered_orders': orders.filter(status='Delivered').count(),
    }
    return render(request, 'dashboard/deliverer_dashboard.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_deliverer, login_url='dashboard:not_allowed')
def deliverer_order_list(request):
    deliverer_profile = request.user.deliverer_profile
    orders = Order.objects.filter(driver=deliverer_profile).order_by('-created_at')
    ctx = {'orders': orders}
    return render(request, 'dashboard/deliverer_order_list.html', ctx)

@login_required_decorator(login_url='dashboard:login_page')
@user_passes_test(is_deliverer, login_url='dashboard:not_allowed')
def deliverer_order_update(request, pk):
    order = get_object_or_404(Order, pk=pk, driver=request.user.deliverer_profile)
    if request.method == 'POST':
        form = DelivererOrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Buyurtma {order.id} statusi muvaffaqiyatli yangilandi.")
            return redirect('dashboard:deliverer_order_list')
        else:
            messages.error(request, "Buyurtma statusini yangilashda xato yuz berdi.")
    else:
        form = DelivererOrderStatusForm(instance=order)
    ctx = {'form': form, 'order': order}
    return render(request, 'dashboard/deliverer_order_update.html', ctx)

# --- Not Allowed Page ---
def not_allowed(request):
    from_page = request.GET.get('from', 'noma\'lum sahifa')
    ctx = {'from_page': from_page}
    return render(request, 'dashboard/not_allowed.html', ctx)