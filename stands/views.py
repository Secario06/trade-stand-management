import math
from datetime import date

from django.shortcuts import get_object_or_404, render

from bookings.models import Booking
from models.bookings import get_booking_status
from stands.models import Stand


def _parse_date(value):
    """Разобрать дату ГГГГ-ММ-ДД; при ошибке вернуть None."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def stands(request):
    """Страница /stands/: список стендов с поиском и фильтром по площади."""
    query = request.GET.get("q", "").strip()
    raw_area = request.GET.get("min_area", "").strip()

    min_area = None
    error = ""
    if raw_area:
        try:
            min_area = float(raw_area.replace(",", "."))
        except ValueError:
            min_area = math.nan
        if not math.isfinite(min_area):
            min_area = None
            error = "Минимальная площадь должна быть числом."

    stands_list = Stand.objects.all()
    if query:
        # Поиск по части названия без учёта регистра.
        stands_list = stands_list.filter(name__icontains=query)
    if min_area is not None:
        # Площадь не меньше заданной.
        stands_list = stands_list.filter(area__gte=min_area)
    stands_list = stands_list.order_by("name")

    context = {
        "stands": stands_list,
        "query": query,
        "min_area": raw_area,
        "error": error,
    }
    return render(request, "stands/stand_list.html", context)


def stand_detail(request, stand_id):
    """Страница /stands/<id>/: информация о стенде и его доступность."""
    # Если стенда нет, Django вернёт ответ 404.
    stand = get_object_or_404(Stand, pk=stand_id)

    # Дата проверки передаётся GET-параметром ?date=ГГГГ-ММ-ДД.
    requested = request.GET.get("date", "")
    check_date = _parse_date(requested)
    invalid_date = check_date is None and bool(requested)
    if check_date is None:
        check_date = date.today()

    available = stand.is_available_on(check_date)

    # История бронирований стенда через обратную связь;
    # select_related загружает арендаторов тем же запросом.
    history = stand.bookings.select_related("user")

    context = {
        "stand": stand,
        "check_date": check_date,
        "invalid_date": invalid_date,
        "available": available,
        "availability_text": get_booking_status(available),
        "history": history,
    }
    return render(request, "stands/stand_detail.html", context)


def available_stands(request):
    """Страница /stands/available/: стенды, свободные на выбранную дату."""
    requested = request.GET.get("date", "")
    check_date = _parse_date(requested)

    free_stands = []
    if check_date is not None:
        # Идентификаторы стендов с активной бронью на эту дату.
        booked_stand_ids = Booking.objects.filter(
            booking_date=check_date,
            is_cancelled=False,
        ).values_list("stand_id", flat=True)

        # Исключаем занятые стенды; отменённые брони не блокируют.
        free_stands = Stand.objects.exclude(
            pk__in=booked_stand_ids,
        ).order_by("name")

    context = {
        "stands": free_stands,
        "check_date": check_date,
        "invalid_date": check_date is None and bool(requested),
    }
    return render(request, "stands/available.html", context)
