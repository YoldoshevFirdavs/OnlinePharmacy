"""Seller profile views"""

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from pharmacy.models import Medicine
from users.models import CustomUser


def seller_profile(request, seller_id):
    """Seller profile page - blog style"""
    seller = get_object_or_404(CustomUser, id=seller_id, is_seller=True)

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
