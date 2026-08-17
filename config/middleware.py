from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render


class CustomErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Agar DEBUG rejimi yoqilgan bo'lsa va bu sozlama maxsus
        # o'chirib qo'yilmagan bo'lsa, Django'ning standart xatolik
        # sahifasini ko'rsatamiz.
        if settings.DEBUG and not getattr(settings, "SHOW_CUSTOM_ERROR_PAGES", False):
            return None

        # API so'rovlari uchun JSON formatida javob qaytaramiz
        if request.path.startswith("/api/"):
            return JsonResponse(
                {"error": "Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."},
                status=500,
            )

        # Oddiy sahifalar uchun 500.html shablonini ko'rsatamiz
        return render(request, "500.html", status=500)
