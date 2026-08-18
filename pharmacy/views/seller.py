from django.shortcuts import render, get_object_or_404
from users.models import Seller
from pharmacy.models import Medicine


def seller_detail(request, seller_id):
    """Blog-style seller page with products and reviews"""
    seller = get_object_or_404(Seller, id=seller_id, is_verified=True)
    
    # Get seller's products
    products = Medicine.objects.filter(
        seller_id=seller_id,
        is_active=True,
        stock__gt=0
    ).order_by('-updated_at')[:12]
    
    # Get seller's product reviews (from products)
    reviews_count = sum(p.reviews_count for p in seller.seller.all())
    avg_rating = seller.rating
    
    context = {
        'seller': seller,
        'products': products,
        'reviews_count': reviews_count,
    }
    
    return render(request, 'seller_detail.html', context)
