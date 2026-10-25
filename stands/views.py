import math
from datetime import date

from django.shortcuts import render

from db.database import open_connection
from models.bookings import get_booking_status


def _parse_date(value):
    """Разобрать дату ГГГГ-ММ-ДД; при ошибке вернуть None."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def stands(request):
    """Страница /stands/: список стендов из SQLite с поиском и фильтром."""
    query = request.GET.get("q", "").strip()
    raw_area = request.GET.get("min_area", "").strip()

    min_area = 0.0
    error = ""
    if raw_area:
        try:
            min_area = float(raw_area.replace(",", "."))
        except ValueError:
            min_area = math.nan
        if not math.isfinite(min_area):
            min_area = 0.0
            error = "Минимальная площадь должна быть числом."

    with open_connection() as conn:
        stands_list = conn.execute(
            """
            SELECT
                id,
                name,
                area,
                stand_type
            FROM stands
            WHERE lower(name) LIKE lower(?)
              AND area >= ?
            ORDER BY name;
            """,
            ["%" + query + "%", min_area],
        ).fetchall()

    context = {
        "stands": stands_list,
        "query": query,
        "min_area": raw_area,
        "error": error,
    }
    return render(request, "stands/stand_list.html", context)


def stand_detail(request, stand_id):
    """Страница /stands/<id>/: информация о стенде и его доступность."""
    with open_connection() as conn:
        stand = conn.execute(
            """
            SELECT
                id,
                name,
                area,
                stand_type
            FROM stands
            WHERE id = ?;
            """,
            [stand_id],
        ).fetchone()

        context = {"stand": stand}
        if stand is not None:
            # Дата проверки передаётся GET-параметром ?date=ГГГГ-ММ-ДД.
            requested = request.GET.get("date", "")
            check_date = _parse_date(requested)
            invalid_date = check_date is None and bool(requested)
            if check_date is None:
                check_date = date.today()

            busy = conn.execute(
                """
                SELECT
                    COUNT(*) AS busy
                FROM bookings
                WHERE stand_id = ?
                  AND booking_date = ?
                  AND is_cancelled = 0;
                """,
                [stand_id, check_date.isoformat()],
            ).fetchone()["busy"]

            history = conn.execute(
                """
                SELECT
                    bookings.id,
                    bookings.booking_date,
                    bookings.is_cancelled,
                    users.name AS user_name
                FROM bookings
                JOIN users
                    ON bookings.user_id = users.id
                WHERE bookings.stand_id = ?
                ORDER BY bookings.booking_date;
                """,
                [stand_id],
            ).fetchall()

            available = busy == 0
            context.update(
                {
                    "check_date": check_date,
                    "invalid_date": invalid_date,
                    "available": available,
                    "availability_text": get_booking_status(available),
                    "history": history,
                }
            )

    return render(
        request,
        "stands/stand_detail.html",
        context,
        status=404 if stand is None else 200,
    )


def available_stands(request):
    """Страница /stands/available/: стенды, свободные на выбранную дату."""
    requested = request.GET.get("date", "")
    check_date = _parse_date(requested)

    free_stands = []
    if check_date is not None:
        with open_connection() as conn:
            free_stands = conn.execute(
                """
                SELECT
                    stands.id,
                    stands.name,
                    stands.area,
                    stands.stand_type
                FROM stands
                WHERE stands.id NOT IN (
                    SELECT bookings.stand_id
                    FROM bookings
                    WHERE bookings.booking_date = ?
                      AND bookings.is_cancelled = 0
                )
                ORDER BY stands.name;
                """,
                [check_date.isoformat()],
            ).fetchall()

    context = {
        "stands": free_stands,
        "check_date": check_date,
        "invalid_date": check_date is None and bool(requested),
    }
    return render(request, "stands/available.html", context)
