import math
from datetime import date

from django.db.models import Q
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from bookings.models import Booking
from models.bookings import get_booking_status
from stands.forms import StandForm
from stands.models import Stand


def _parse_date(value):
    """Разобрать дату ГГГГ-ММ-ДД; при ошибке вернуть None."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# Допустимые поля сортировки списка стендов. Произвольные значения
# из URL в order_by() не передаются.
SORT_FIELDS = {
    "name": "name",
    "area": "area",
}


def stands(request):
    """Страница /stands/: список стендов с поиском, фильтром и сортировкой."""
    query = request.GET.get("q", "").strip()
    raw_area = request.GET.get("min_area", "").strip()
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("direction", "asc")

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
        # Поиск по части названия без учёта регистра; числовой запрос
        # дополнительно сравнивается с площадью стенда.
        condition = Q(name__icontains=query)
        if query.replace(",", ".").replace(".", "", 1).isdigit():
            condition |= Q(area=float(query.replace(",", ".")))
        stands_list = stands_list.filter(condition)
    if min_area is not None:
        # Площадь не меньше заданной.
        stands_list = stands_list.filter(area__gte=min_area)

    # Поле сортировки выбирается из словаря, направление – из двух
    # допустимых значений; pk делает порядок стабильным.
    if sort not in SORT_FIELDS:
        sort = "name"
    if direction not in ("asc", "desc"):
        direction = "asc"
    sort_field = SORT_FIELDS[sort]
    if direction == "desc":
        sort_field = f"-{sort_field}"
    stands_list = stands_list.order_by(sort_field, "pk")

    context = {
        "stands": stands_list,
        "query": query,
        "min_area": raw_area,
        "sort": sort,
        "direction": direction,
        "error": error,
    }
    return render(request, "stands/stand_list.html", context)


def stand_detail(request, slug):
    """Страница /stands/<slug>/: информация о стенде и его доступность."""
    # Поиск по slug; если стенда нет, Django вернёт ответ 404.
    stand = get_object_or_404(Stand, slug=slug)

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
        booked_stand_ids = (
            Booking.objects
            .active()
            .for_date(check_date)
            .values_list("stand_id", flat=True)
        )

        # Исключаем занятые стенды; отменённые и завершённые
        # бронирования стенд не блокируют.
        free_stands = Stand.objects.exclude(
            pk__in=booked_stand_ids,
        ).order_by("name")

    context = {
        "stands": free_stands,
        "check_date": check_date,
        "invalid_date": check_date is None and bool(requested),
    }
    return render(request, "stands/available.html", context)


def stand_create(request):
    """Страница /stands/create/: создание стенда с изображением."""
    if request.method == "POST":
        # Кроме полей формы передаются загруженные файлы (request.FILES).
        form = StandForm(request.POST, request.FILES)
        if form.is_valid():
            stand = form.save()
            messages.success(request, f"Стенд «{stand.name}» создан.")
            return redirect(stand)
    else:
        form = StandForm()
    return render(request, "stands/stand_form.html", {"form": form})


def stand_update(request, slug):
    """Страница /stands/<slug>/edit/: редактирование стенда."""
    stand = get_object_or_404(Stand, slug=slug)
    if request.method == "POST":
        form = StandForm(request.POST, request.FILES, instance=stand)
        if form.is_valid():
            stand = form.save()
            messages.success(request, f"Стенд «{stand.name}» изменён.")
            return redirect(stand)
    else:
        form = StandForm(instance=stand)
    context = {"form": form, "stand": stand}
    return render(request, "stands/stand_form.html", context)
