from django.apps import AppConfig
from django.db.backends.signals import connection_created


class StandsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stands'
    verbose_name = "Торговые стенды"

    def ready(self):
        # Поиск icontains должен работать с кириллицей в SQLite.
        from tradestands.sqlite_unicode import register_like

        connection_created.connect(register_like)
