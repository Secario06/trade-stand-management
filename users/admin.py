from django.contrib import admin
from django.db.models import Count

from bookings.models import Booking
from users.models import User


class UserBookingInline(admin.TabularInline):
    """Бронирования арендатора на странице арендатора."""

    model = Booking
    fields = ("stand", "booking_date", "status")
    extra = 0
    can_delete = False
    show_change_link = True
    autocomplete_fields = ("stand",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "bookings_total")
    list_display_links = ("name",)
    search_fields = ("name", "email")
    ordering = ("name",)
    list_per_page = 20
    readonly_fields = ("id",)
    inlines = (UserBookingInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            bookings_count=Count("bookings"),
        )

    @admin.display(description="Бронирований", ordering="bookings_count")
    def bookings_total(self, obj):
        return obj.bookings_count
