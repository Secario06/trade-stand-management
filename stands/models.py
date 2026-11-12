from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Case, Q, Value, When
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode


# Площадь (кв.м), начиная с которой стенд считается большим.
LARGE_STAND_AREA = 40


class Stand(models.Model):
    """Торговый стенд, доступный для аренды."""

    class StandType(models.TextChoices):
        STANDARD = "Стандарт", "Стандарт"
        PREMIUM = "Премиум", "Премиум"
        ISLAND = "Остров", "Остров"

    # Название стенда.
    name = models.CharField(
        max_length=200,
        verbose_name="Название стенда",
    )

    # Площадь в квадратных метрах: положительное число.
    area = models.FloatField(
        validators=[MinValueValidator(0.01)],
        verbose_name="Площадь, кв.м",
        help_text="Площадь стенда в квадратных метрах (больше нуля).",
    )

    # Тип стенда: значение из заранее заданного набора.
    stand_type = models.CharField(
        max_length=50,
        choices=StandType.choices,
        default=StandType.STANDARD,
        verbose_name="Тип стенда",
    )

    # Текстовый идентификатор для адреса страницы. Формируется
    # автоматически из транслитерированного названия и первичного ключа.
    slug = models.SlugField(
        max_length=180,
        unique=True,
        editable=False,
        verbose_name="URL-идентификатор",
    )

    # Вычисляемое поле: значение формирует сама база данных на основе
    # площади и пересчитывается при её изменении. db_persist=True хранит
    # вычисленное значение в таблице. Вручную поле не редактируется.
    is_large = models.GeneratedField(
        expression=Case(
            When(area__gte=LARGE_STAND_AREA, then=Value(True)),
            default=Value(False),
            output_field=models.BooleanField(),
        ),
        output_field=models.BooleanField(),
        db_persist=True,
        verbose_name="Большой стенд",
    )

    def is_available_on(self, booking_date):
        """Проверить, свободен ли стенд на дату.

        Стенд блокируют только активные бронирования: отменённые и
        завершённые его не занимают.
        """
        return not self.bookings.active().for_date(booking_date).exists()

    def make_slug(self):
        """Сформировать slug: транслитерация названия и первичный ключ."""
        base_slug = slugify(unidecode(self.name)) or "stand"
        return f"{base_slug}-{self.pk}"

    def save(self, *args, **kwargs):
        # slug формируется только тогда, когда он ещё не задан,
        # поэтому адрес стенда не меняется при обычных сохранениях.
        if not self.slug:
            if self.pk:
                self.slug = self.make_slug()
            else:
                # У нового объекта ещё нет первичного ключа: сначала
                # сохраняем его, затем дописываем slug с идентификатором.
                super().save(*args, **kwargs)
                self.slug = self.make_slug()
                super().save(update_fields=["slug"])
                return
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Адрес страницы стенда (используют шаблоны и админка)."""
        return reverse("stands:detail", kwargs={"slug": self.slug})

    def __str__(self):
        # Текстовое представление в админке, shell и т.п.
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Стенд"
        verbose_name_plural = "Стенды"
        constraints = [
            # Ограничение на уровне базы данных, как и в схеме ПР7.
            models.CheckConstraint(
                condition=Q(area__gt=0),
                name="stand_area_positive",
            ),
        ]
