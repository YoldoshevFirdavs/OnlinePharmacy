from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    name = "pharmacy"

    def ready(self):
        import pharmacy.signals
