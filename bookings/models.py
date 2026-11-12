from django.db import models
from django.db.models import Q

from stands.models import Stand
from users.models import User


class BookingQuerySet(models.QuerySet):
    """Набор запросов для работы с бронированиями."""

    def active(self):
        """Возвращает только активные бронирования."""
        return self.filter(status=self.model.Status.ACTIVE)

    def cancelled(self):
        """Возвращает только отменённые бронирования."""
        return self.filter(status=self.model.Status.CANCELLED)

    def completed(self):
        """Возвращает только завершённые бронирования."""
        return self.filter(status=self.model.Status.COMPLETED)

    def for_date(self, selected_date):
        """Возвращает бронирования на указанную дату."""
        return self.filter(booking_date=selected_date)


class BookingManager(models.Manager.from_queryset(BookingQuerySet)):
    """Менеджер модели Booking с дополнительными методами."""


class Booking(models.Model):
    """Бронирование торгового стенда арендатором на дату."""

    class Status(models.TextChoices):
        # Бронирование действует.
        ACTIVE = "active", "Активно"
        # Бронирование отменено.
        CANCELLED = "cancelled", "Отменено"
        # Бронирование завершено.
        COMPLETED = "completed", "Завершено"

    # Стенд, для которого оформлено бронирование.
    # PROTECT запрещает удалять стенд, на который есть ссылки:
    # история бронирований сохраняется.
    stand = models.ForeignKey(
        Stand,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Стенд",
    )

    # Арендатор, оформивший бронирование.
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Арендатор",
    )

    # Дата бронирования: DateField хранит дату, а не строку.
    booking_date = models.DateField(
        verbose_name="Дата бронирования",
    )

    # Состояние бронирования. По умолчанию бронирование активно.
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Статус бронирования",
    )

    objects = BookingManager()

    def cancel(self):
        """Отменить бронирование и сохранить изменение."""
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])

    def complete(self):
        """Отметить бронирование завершённым и сохранить изменение."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status"])

    def is_active(self):
        """Проверить, активно ли бронирование."""
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.stand} — {self.booking_date} ({self.user})"

    class Meta:
        # Сначала по дате, затем по идентификатору.
        ordering = ["booking_date", "pk"]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        constraints = [
            # Правило предметной области (ПР3, ПР7): на одну дату
            # у стенда не может быть двух активных бронирований.
            # Отменённые и завершённые бронирования правило не затрагивают.
            models.UniqueConstraint(
                fields=["stand", "booking_date"],
                condition=Q(status="active"),
                name="unique_active_booking_per_stand_date",
                violation_error_message=(
                    "На эту дату у стенда уже есть активное бронирование."
                ),
            ),
        ]
