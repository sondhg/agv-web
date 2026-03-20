from django.apps import AppConfig


class Vda5050Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vda5050"

    def ready(self):
        pass
