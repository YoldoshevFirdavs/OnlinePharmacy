import logging

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from users.models import DeliveryDriver

from .models import Salary
from .serializers import AdminSalaryCreateSerializer, SalarySerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def create_salary(request):
    """
    Endpoint for creating a salary for a driver.
    This would typically be triggered by an admin or an automated process.
    """
    serializer = AdminSalaryCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    driver_id = serializer.validated_data["driver_id"]
    amount = serializer.validated_data["amount"]
    period_start = serializer.validated_data.get("period_start")
    period_end = serializer.validated_data.get("period_end")

    try:
        driver_profile = DeliveryDriver.objects.get(id=driver_id)
    except DeliveryDriver.DoesNotExist:
        return Response({"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)

    salary = Salary.objects.create(
        driver=driver_profile,
        amount=amount,
        status="Pending",
        period_start=period_start,
        period_end=period_end,
    )

    serializer = SalarySerializer(salary)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class SalaryViewSet(viewsets.ModelViewSet):
    queryset = Salary.objects.all()
    serializer_class = SalarySerializer
    permission_classes = [IsAdminUser]
