from datetime import date

from django.shortcuts import render

from models.bookings import get_booking_status, is_stand_available
from models.stands import find_stand_by_id
from tradestands.dataset import load_dataset


def stands(request):
    """Страница /stands/: список стендов из data/stands.json."""
    stands_list, _, _ = load_dataset()

    context = {
        "stands": stands_list,
    }

    return render(request, "stands/stand_list.html", context)


def stand_detail(request, stand_id):
    """Страница /stands/<id>/: информация о стенде и его доступность."""
    stands_list, _, bookings_list = load_dataset()
    stand = find_stand_by_id(stands_list, stand_id)

    context = {
        "stand": stand,
    }

    if stand is not None:
        # Дата проверки передаётся GET-параметром ?date=ГГГГ-ММ-ДД.
        requested = request.GET.get("date", "")
        try:
            check_date = date.fromisoformat(requested)
            invalid_date = False
        except ValueError:
            check_date = date.today()
            invalid_date = bool(requested)

        available = is_stand_available(
            bookings_list,
            stand,
            check_date.isoformat(),
        )
        context.update(
            {
                "check_date": check_date,
                "invalid_date": invalid_date,
                "available": available,
                "availability_text": get_booking_status(available),
            }
        )

    return render(
        request,
        "stands/stand_detail.html",
        context,
        status=404 if stand is None else 200,
    )
