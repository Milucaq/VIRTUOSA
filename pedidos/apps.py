from django.apps import AppConfig


class PedidosConfig(AppConfig):
    name = 'pedidos'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from . import signals  # noqa: F401
