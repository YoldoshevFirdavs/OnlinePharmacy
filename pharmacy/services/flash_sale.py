from datetime import datetime, timedelta

from djoser import permissions
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pharmacy.models.medicine import Medicine
from pharmacy.models.misc import FlashSale, ProductViewHistory
from pharmacy.serializers.misc import FlashSaleSerializer


class FlashSaleListCreateView(generics.ListCreateAPIView):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer
    permission_classes = [permissions.IsStafforReadOnly]


@api_view(["GET"])
def check_flash_sale_status(request, product_id):
    try:
        product = Medicine.objects.get(id=product_id)
    except Medicine.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    user_viewed = ProductViewHistory.objects.filter(user=request.user, product=product).exists()

    upcoming_flash_sale = FlashSale.objects.filter(
        product=product, start_time__lte=datetime.now() + timedelta(hours=24)
    ).first()

    if user_viewed and upcoming_flash_sale:
        discount = upcoming_flash_sale.discount_percentage
        start_time = upcoming_flash_sale.start_time
        end_time = upcoming_flash_sale.end
        return Response(
            {
                "message": f"This prdouct will be on a {discount}% off flash sale !",
                "start_time": start_time,
                "end_time": end_time,
            }
        )
    else:
        return Response({"message": "No upcoming flash sales for this product"})
