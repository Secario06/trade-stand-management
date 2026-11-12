from django import forms
from django.utils import timezone

from bookings.models import Booking
from stands.models import Stand
from users.models import User

# Допустимые варианты фильтра по статусу и сортировки списка.
STATUS_CHOICES = [
    ("active", "Активные"),
    ("cancelled", "Отменённые"),
    ("completed", "Завершённые"),
    ("all", "Все"),
]
SORT_CHOICES = [
    ("date", "Дате"),
    ("stand", "Стенду"),
    ("user", "Арендатору"),
]


class BookingFilterForm(forms.Form):
    """Форма фильтрации списка бронирований (GET-параметры).

    Обычная форма forms.Form: она ничего не сохраняет, а только проверяет
    параметры запроса и отдаёт представлению проверенные значения.
    """

    # Поиск по названию стенда, имени и email арендатора.
    q = forms.CharField(
        required=False,
        max_length=100,
        label="Поиск",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Стенд, арендатор, email",
            }
        ),
    )

    # Дата бронирования: DateField проверяет формат значения.
    date = forms.DateField(
        required=False,
        label="Дата бронирования",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control"},
            format="%Y-%m-%d",
        ),
    )

    # ModelChoiceField проверяет, что выбранный объект существует.
    stand = forms.ModelChoiceField(
        queryset=Stand.objects.order_by("name"),
        required=False,
        label="Стенд",
        empty_label="Все стенды",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.order_by("name"),
        required=False,
        label="Арендатор",
        empty_label="Все арендаторы",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Тип стенда: допустимы только значения перечисления.
    type = forms.ChoiceField(
        required=False,
        label="Тип стенда",
        choices=[("", "Любой тип"), *Stand.StandType.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # По умолчанию показываются активные бронирования.
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=STATUS_CHOICES,
        initial="active",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # Сортировка: произвольное значение из адресной строки отклоняется.
    sort = forms.ChoiceField(
        required=False,
        label="Сортировать по",
        choices=SORT_CHOICES,
        initial="date",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class BookingForm(forms.ModelForm):
    """Форма создания и редактирования бронирования (ModelForm).

    Статус в форму не входит: новое бронирование активно по умолчанию,
    а отмена выполняется отдельной операцией.
    """

    class Meta:
        model = Booking
        fields = ["stand", "user", "booking_date"]
        labels = {
            "stand": "Стенд",
            "user": "Арендатор",
            "booking_date": "Дата бронирования",
        }
        help_texts = {
            "stand": "Выберите стенд для бронирования.",
            "user": "Арендатор, на которого оформляется бронирование.",
            "booking_date": "Укажите дату аренды стенда.",
        }
        widgets = {
            "stand": forms.Select(attrs={"class": "form-select"}),
            "user": forms.Select(attrs={"class": "form-select"}),
            # Формат ГГГГ-ММ-ДД нужен, чтобы браузер показал текущее
            # значение в элементе выбора даты при редактировании.
            "booking_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
        }

    def clean_booking_date(self):
        """Запретить бронирование на прошедшую дату."""
        booking_date = self.cleaned_data["booking_date"]
        # Если дата существующего бронирования не менялась, проверка
        # не применяется: записи «задним числом» можно сохранять заново.
        unchanged = (
            self.instance.pk
            and self.instance.booking_date == booking_date
        )
        if booking_date < timezone.localdate() and not unchanged:
            raise forms.ValidationError(
                "Нельзя создать бронирование на прошедшую дату."
            )
        return booking_date
