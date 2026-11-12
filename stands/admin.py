from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from bookings.models import Booking
from stands.models import Stand


class StandBookingInline(admin.TabularInline):
    """Бронирования стенда на странице стенда."""

    model = Booking
    fields = ("user", "booking_date", "status")
    # Пустые формы для новых бронирований не показываются.
    extra = 0
    # История бронирований не удаляется через встроенную таблицу.
    can_delete = False
    show_change_link = True
    autocomplete_fields = ("user",)


@admin.register(Stand)
class StandAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "stand_type",
        "area",
        "is_large",
        "active_bookings_count",
        "site_link",
    )
    list_display_links = ("name",)
    # Площадь можно менять прямо в списке (поле не является ссылкой).
    list_editable = ("area",)
    search_fields = ("name",)
    list_filter = ("stand_type", "is_large")
    ordering = ("name",)
    list_per_page = 20

    fields = (
        "id", "name", "stand_type", "area", "image", "is_large", "slug",
    )
    # Идентификатор, slug и вычисляемое поле только для чтения.
    readonly_fields = ("id", "slug", "is_large")

    inlines = (StandBookingInline,)

    # Ссылка «Посмотреть на сайте» использует get_absolute_url().
    view_on_site = True

    def get_queryset(self, request):
        # Число активных бронирований считается одним запросом для всех
        # строк списка (без запроса на каждый стенд).
        return super().get_queryset(request).annotate(
            active_bookings=Count(
                "bookings",
                filter=Q(bookings__status=Booking.Status.ACTIVE),
            ),
        )

    @admin.display(
        description="Активных бронирований",
        ordering="active_bookings",
    )
    def active_bookings_count(self, obj):
        return obj.active_bookings

    @admin.display(description="Страница на сайте")
    def site_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">Открыть</a>',
            obj.get_absolute_url(),
        )
