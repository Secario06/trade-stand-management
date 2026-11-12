from django.contrib import admin

from stands.models import Stand


@admin.register(Stand)
class StandAdmin(admin.ModelAdmin):
    list_display = ("name", "stand_type", "area")
    list_filter = ("stand_type",)
    search_fields = ("name",)
