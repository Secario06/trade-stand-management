from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, render

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

PAGE_SIZE = 5


def booking_list(request):
    """Страница /bookings/: список бронирований.

    Поддерживает фильтры (date, stand, user, type, q, show=all),
    сортировку (sort) и постраничный вывод (page).
    """
    booking_date = request.GET.get("date", "").strip()
    stand_id = request.GET.get("stand", "").strip()
    user_id = request.GET.get("user", "").strip()
    stand_type = request.GET.get("type", "").strip()
    search = request.GET.get("q", "").strip()
    show_all = request.GET.get("show") == "all"
    sort = request.GET.get("sort", "date")
    error = None

    bookings_data = Booking.objects.all()

    # По умолчанию отменённые бронирования исключаются.
    if not show_all:
        bookings_data = bookings_data.exclude(is_cancelled=True)

    # Фильтр по дате с проверкой формата.
    if booking_date:
        try:
            selected_date = datetime.strptime(
                booking_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            error = "Укажите корректную дату."
        else:
            bookings_data = bookings_data.filter(
                booking_date=selected_date
            )

    # Фильтры по внешним ключам (идентификаторы проверяются).
    if stand_id.isdigit():
        bookings_data = bookings_data.filter(stand_id=int(stand_id))
    if user_id.isdigit():
        bookings_data = bookings_data.filter(user_id=int(user_id))

    # Фильтр по полю связанной модели (тип стенда).
    if stand_type in Stand.StandType.values:
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

    # Выбор поля сортировки из заранее заданного соответствия.
    if sort not in SORT_FIELDS:
        sort = "date"
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
            "is_cancelled",
            "stand_name",
            "area",
            "user_name",
        )
        .order_by(SORT_FIELDS[sort], "id")
    )

    # Постраничный вывод применяется после фильтров и сортировки.
    paginator = Paginator(bookings_data, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "bookings": page_obj,
        "page_obj": page_obj,
        "total": paginator.count,
        "booking_date": booking_date,
        "selected_stand": stand_id,
        "selected_user": user_id,
        "selected_type": stand_type,
        "search": search,
        "show_all": show_all,
        "sort": sort,
        "stands": Stand.objects.order_by("name"),
        "users": User.objects.order_by("name"),
        "stand_types": Stand.StandType.choices,
        "error": error,
    }
    return render(request, "bookings/booking_list.html", context)


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
    # Условие подсчёта: только активные бронирования.
    active = Q(bookings__is_cancelled=False)

    # Сводные показатели по стендам (aggregate).
    totals = Stand.objects.aggregate(
        stands_count=Count("pk"),
        min_area=Min("area"),
        max_area=Max("area"),
        avg_area=Avg("area"),
        total_area=Sum("area"),
    )
    totals["active_bookings"] = Booking.objects.filter(
        is_cancelled=False
    ).count()

    # Активные бронирования каждого стенда. Запрос строится от Stand,
    # поэтому стенды без бронирований остаются в результате (счётчик 0).
    by_stand = Stand.objects.annotate(
        bookings_count=Count("bookings", filter=active),
    ).order_by("-bookings_count", "name")

    # То же по арендаторам.
    by_user = User.objects.annotate(
        bookings_count=Count("bookings", filter=active),
    ).order_by("-bookings_count", "name")

    # Группировка по типу стенда.
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
        "by_type": by_type,
        "popular": popular,
        "latest": latest,
    }
    return render(request, "bookings/statistics.html", context)
