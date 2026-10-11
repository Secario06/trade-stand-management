from datetime import date

from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape

from homepage.views import page
from models.bookings import get_booking_status, is_stand_available
from models.stands import find_stand_by_id
from tradestands.dataset import load_dataset


def stands(request):
    """Страница /stands/: список стендов из data/stands.json."""
    stands_list, _, _ = load_dataset()

    items = ""
    for stand in stands_list:
        url = reverse("stand_detail", args=[stand.id])
        items += f"""
        <li class="list-group-item d-flex justify-content-between">
            <a href="{url}">{escape(stand.name)}</a>
            <span>
                {escape(stand.stand_type)} · {stand.area} кв.м.
            </span>
        </li>
        """
    if not items:
        items = '<li class="list-group-item">Стендов пока нет.</li>'

    content = f"""
    <h1>Стенды</h1>
    <ul class="list-group">{items}</ul>
    """
    return HttpResponse(page("Торговые стенды – стенды", content))


def stand_detail(request, stand_id):
    """Страница /stands/<id>/: информация о стенде и его доступность."""
    stands_list, _, bookings_list = load_dataset()

    stand = find_stand_by_id(stands_list, stand_id)
    if stand is None:
        content = f"""
        <h1 class="text-danger">Стенд не найден</h1>
        <a href="{reverse("stands")}"
           class="btn btn-outline-secondary">
            ← к списку стендов
        </a>
        """
        return HttpResponse(
            page("Стенд не найден", content),
            status=404,
        )

    # Дата проверки передаётся GET-параметром ?date=ГГГГ-ММ-ДД.
    today = date.today()
    warning = ""
    try:
        check_date = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        check_date = today
        if request.GET.get("date"):
            warning = (
                '<div class="alert alert-warning">'
                "Неверная дата, показана доступность на сегодня."
                "</div>"
            )

    available = is_stand_available(
        bookings_list,
        stand,
        check_date.isoformat(),
    )
    badge = "bg-success" if available else "bg-danger"
    status = "доступен" if available else "занят"

    content = f"""
    {warning}
    <div class="card mb-3">
        <div class="card-body">
            <h5 class="card-title">{escape(stand.name)}</h5>
            <p class="card-text"><strong>ID:</strong> {stand.id}</p>
            <p class="card-text">
                <strong>Тип:</strong> {escape(stand.stand_type)}
            </p>
            <p class="card-text">
                <strong>Площадь:</strong> {stand.area} кв.м.
            </p>
            <p class="card-text">
                Доступность на {check_date.strftime("%d.%m.%Y")}:
                <span class="badge {badge}">{status}</span>
            </p>
            <p class="card-text text-muted">
                {get_booking_status(available)}
            </p>
            <form method="get" class="row g-2 mb-3">
                <div class="col-auto">
                    <input type="date" name="date" class="form-control"
                           value="{check_date.isoformat()}">
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-primary">
                        Проверить дату
                    </button>
                </div>
            </form>
            <a href="{reverse("stands")}"
               class="btn btn-outline-secondary">
                ← к списку стендов
            </a>
        </div>
    </div>
    """
    return HttpResponse(page(stand.name, content), status=200)
