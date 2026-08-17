from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SalaryViewSet, create_salary

router = DefaultRouter()
router.register(r"salaries", SalaryViewSet, basename="salary")

urlpatterns = [
    path("salaries/create/", create_salary, name="admin-salary-create"),
]

urlpatterns += router.urls
