from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.forms import BookingFilterForm, BookingForm
from bookings.models import Booking
from stands.models import Stand
from users.models import User

# Допустимые значения параметра sort и соответствующие поля модели.
# Произвольный ввод пользователя в order_by() не передаётся.
SORT_FIELDS = {
    "date": "booking_date",
    "stand": "stand__name",
    "user": "user__name",
}

# Допустимые значения параметра status: методы менеджера Booking.objects.
STATUS_FILTERS = {
    "active": "active",
    "cancelled": "cancelled",
    "completed": "completed",
}

PAGE_SIZE = 5

# Сообщения об ошибках, общие для создания и редактирования.
STAND_BUSY_ERROR = "Выбранный стенд уже забронирован на эту дату."


def booking_list(request):
    """Страница /bookings/: список бронирований.

    Параметры фильтрации (status, date, stand, user, type, q) и
    сортировки (sort) проверяет форма BookingFilterForm, постраничный
    вывод (page) обрабатывает Paginator.
    """
    # Форме передаются GET-параметры; без параметров форма не связана.
    form = BookingFilterForm(request.GET or None)
    form_valid = form.is_bound and form.is_valid()

    # Значения по умолчанию: при ошибке в форме фильтры не применяются.
    status = "active"
    booking_date = None
    stand_id = None
    user_id = None
    stand_type = ""
    search = ""
    sort = "date"

    # Проверенные значения доступны только после успешного is_valid().
    if form_valid:
        data = form.cleaned_data
        status = data.get("status") or "active"
        booking_date = data.get("date")
        selected_stand = data.get("stand")
        selected_user = data.get("user")
        stand_id = selected_stand.pk if selected_stand else None
        user_id = selected_user.pk if selected_user else None
        stand_type = data.get("type") or ""
        search = data.get("q") or ""
        sort = data.get("sort") or "date"

    # Исходная выборка строится через пользовательский QuerySet.
    if status == "all":
        bookings_data = Booking.objects.all()
    else:
        bookings_data = getattr(Booking.objects, STATUS_FILTERS[status])()

    if booking_date:
        bookings_data = bookings_data.for_date(booking_date)
    if stand_id:
        bookings_data = bookings_data.filter(stand_id=stand_id)
    if user_id:
        bookings_data = bookings_data.filter(user_id=user_id)

    # Фильтр по полю связанной модели (тип стенда).
    if stand_type:
        bookings_data = bookings_data.filter(
            stand__stand_type=stand_type
        )

    # Поиск по нескольким полям связанных моделей.
    if search:
        bookings_data = bookings_data.filter(
            Q(stand__name__icontains=search)
            | Q(user__name__icontains=search)
            | Q(user__email__icontains=search)
        )

    bookings_data = (
        bookings_data
        .annotate(
            stand_name=F("stand__name"),
            area=F("stand__area"),
            user_name=F("user__name"),
        )
        .values(
            "id",
            "booking_date",
            "status",
            "stand_name",
            "area",
            "user_name",
        )
        .order_by(SORT_FIELDS[sort], "id")
    )

    # Постраничный вывод применяется после фильтров и сортировки.
    paginator = Paginator(bookings_data, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Общее сообщение, если параметры фильтрации не прошли проверку.
    if form.is_bound and not form_valid:
        error = "Проверьте введённые значения фильтров."
    else:
        error = None

    context = {
        "bookings": page_obj,
        "page_obj": page_obj,
        "total": paginator.count,
        "form": form,
        "booking_date": booking_date,
        "selected_status": status,
        "sort": sort,
        "error": error,
    }
    return render(request, "bookings/booking_list.html", context)


def _stand_is_busy(form, booking=None):
    """Проверить, занят ли стенд другим активным бронированием.

    Учитываются только активные бронирования: отменённые и завершённые
    стенд не блокируют. При редактировании само бронирование
    исключается из проверки.
    """
    is_booked = Booking.objects.active().filter(
        stand=form.cleaned_data["stand"],
        booking_date=form.cleaned_data["booking_date"],
    )
    if booking is not None:
        is_booked = is_booked.exclude(pk=booking.pk)
    return is_booked.exists()


def _save_booking_form(form, booking=None):
    """Сохранить форму бронирования, если стенд свободен.

    Возвращает сохранённое бронирование или None; при конфликте
    в форму добавляется общая ошибка.
    """
    if _stand_is_busy(form, booking):
        form.add_error(None, STAND_BUSY_ERROR)
        return None
    try:
        # Ограничение базы данных страхует от одновременных запросов.
        with transaction.atomic():
            return form.save()
    except IntegrityError:
        form.add_error(None, STAND_BUSY_ERROR)
        return None


def booking_create(request):
    """Страница /bookings/create/: создание бронирования."""
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = _save_booking_form(form)
            if booking:
                messages.success(
                    request, f"Бронирование №{booking.pk} создано."
                )
                return redirect("bookings:bookings")
    else:
        # По умолчанию подставляется сегодняшняя дата.
        form = BookingForm(
            initial={"booking_date": timezone.localdate()}
        )
    return render(request, "bookings/booking_form.html", {"form": form})


def booking_update(request, booking_id):
    """Страница /bookings/<id>/edit/: редактирование бронирования."""
    # Изменять можно только активные бронирования; для остальных 404.
    booking = get_object_or_404(Booking.objects.active(), pk=booking_id)
    if request.method == "POST":
        # instance связывает форму с существующей записью.
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            if _save_booking_form(form, booking):
                messages.success(
                    request, f"Бронирование №{booking.pk} изменено."
                )
                return redirect("bookings:bookings")
    else:
        form = BookingForm(instance=booking)
    context = {"form": form, "booking": booking}
    return render(request, "bookings/booking_form.html", context)


@require_POST
def booking_cancel(request, booking_id):
    """Отмена бронирования: запись остаётся, меняется только статус."""
    booking = get_object_or_404(Booking.objects.active(), pk=booking_id)
    booking.cancel()
    messages.success(request, f"Бронирование №{booking.pk} отменено.")
    return redirect("bookings:bookings")


def booking_detail(request, booking_id):
    """Страница /bookings/<id>/: информация о бронировании."""
    # Стенд и арендатор загружаются тем же запросом (JOIN).
    booking = get_object_or_404(
        Booking.objects.select_related("stand", "user"),
        pk=booking_id,
    )
    return render(
        request,
        "bookings/booking_detail.html",
        {"booking": booking},
    )


def statistics(request):
    """Страница /bookings/statistics/: статистика бронирований."""
    status = Booking.Status

    # Общие показатели по статусам (aggregate с условиями Q).
    totals = Booking.objects.aggregate(
        total_bookings=Count("id"),
        active_bookings=Count("id", filter=Q(status=status.ACTIVE)),
        cancelled_bookings=Count("id", filter=Q(status=status.CANCELLED)),
        completed_bookings=Count("id", filter=Q(status=status.COMPLETED)),
    )

    # Сводные показатели по площади стендов.
    totals.update(
        Stand.objects.aggregate(
            stands_count=Count("pk"),
            min_area=Min("area"),
            max_area=Max("area"),
            avg_area=Avg("area"),
            total_area=Sum("area"),
        )
    )

    # Условие подсчёта: только активные бронирования.
    active = Q(bookings__status=status.ACTIVE)

    # Активные бронирования каждого стенда. Запрос строится от Stand,
    # поэтому стенды без бронирований остаются в результате (счётчик 0).
    by_stand = Stand.objects.annotate(
        bookings_count=Count("bookings", filter=active),
    ).order_by("-bookings_count", "name")

    # То же по арендаторам.
    by_user = User.objects.annotate(
        bookings_count=Count("bookings", filter=active),
    ).order_by("-bookings_count", "name")

    # Группировка бронирований по статусу.
    counts_by_status = dict(
        Booking.objects
        .values_list("status")
        .annotate(bookings_count=Count("pk"))
        .order_by("status")
    )
    by_status = [
        {"label": label, "count": counts_by_status.get(value, 0)}
        for value, label in status.choices
    ]

    # Группировка стендов по типу.
    by_type = (
        Stand.objects
        .values("stand_type")
        .annotate(
            stands_count=Count("pk"),
            avg_area=Avg("area"),
        )
        .order_by("stand_type")
    )

    # Фильтрация по результату агрегации (аналог HAVING).
    popular = by_stand.filter(bookings_count__gt=1)

    # Три последних бронирования (срез QuerySet).
    latest = Booking.objects.select_related(
        "stand", "user"
    ).order_by("-pk")[:3]

    context = {
        "totals": totals,
        "by_stand": by_stand,
        "by_user": by_user,
        "by_status": by_status,
        "by_type": by_type,
        "popular": popular,
        "latest": latest,
    }
    return render(request, "bookings/statistics.html", context)
