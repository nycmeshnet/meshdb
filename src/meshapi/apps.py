from django.apps import AppConfig


class MeshapiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "meshapi"

    def ready(self) -> None:
        # Implicitly connect signal handlers decorated with @receiver.
        from meshapi.util import events  # noqa: F401
