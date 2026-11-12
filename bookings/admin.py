from django.contrib import admin, messages

from bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Столбцы списка: связанные объекты отображаются через __str__().
    list_display = (
        "id",
        "stand",
        "user",
        "stand_area",
        "booking_date",
        "status",
    )
    list_display_links = ("id",)

    # Поиск по полям связанных моделей (двойное подчёркивание).
    search_fields = ("stand__name", "user__name", "user__email")
    list_filter = ("booking_date", "status", "stand")
    ordering = ("-booking_date",)
    list_per_page = 20
    date_hierarchy = "booking_date"

    # Идентификатор показывается, но не редактируется.
    readonly_fields = ("id",)

    # Стенд и арендатор загружаются JOIN-ом, без запроса на каждую строку.
    list_select_related = ("stand", "user")

    # Поиск по мере ввода (у StandAdmin и UserAdmin есть search_fields).
    autocomplete_fields = ("stand", "user")

    actions = ("cancel_bookings", "complete_bookings", "restore_bookings")

    @admin.display(description="Площадь, кв.м", ordering="stand__area")
    def stand_area(self, obj):
        return obj.stand.area

    @admin.action(description="Отменить выбранные бронирования")
    def cancel_bookings(self, request, queryset):
        count = 0
        for booking in queryset.exclude(status=Booking.Status.CANCELLED):
            booking.cancel()
            count += 1
        self.message_user(
            request, f"Отменено бронирований: {count}.", messages.SUCCESS
        )

    @admin.action(description="Отметить завершёнными")
    def complete_bookings(self, request, queryset):
        count = 0
        for booking in queryset.exclude(status=Booking.Status.COMPLETED):
            booking.complete()
            count += 1
        self.message_user(
            request, f"Завершено бронирований: {count}.", messages.SUCCESS
        )

    @admin.action(description="Вернуть в активные")
    def restore_bookings(self, request, queryset):
        restored = 0
        conflicts = 0
        for booking in queryset.exclude(status=Booking.Status.ACTIVE):
            # Правило предметной области: на дату не более одного
            # активного бронирования стенда.
            if booking.stand.is_available_on(booking.booking_date):
                booking.status = Booking.Status.ACTIVE
                booking.save(update_fields=["status"])
                restored += 1
            else:
                conflicts += 1
        self.message_user(
            request, f"Возвращено бронирований: {restored}.", messages.SUCCESS
        )
        if conflicts:
            self.message_user(
                request,
                f"Не возвращено из-за занятой даты: {conflicts}.",
                messages.WARNING,
            )
