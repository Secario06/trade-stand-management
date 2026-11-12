from django.contrib import admin

from bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("pk", "stand", "user", "booking_date", "is_cancelled")
    list_filter = ("is_cancelled", "stand")
    list_select_related = ("stand", "user")
