from django.shortcuts import render

from db.database import open_connection


def bookings(request):
    """Страница /bookings/: бронирования из SQLite (по умолчанию активные).

    Параметр ?show=all добавляет отменённые бронирования.
    """
    show_all = request.GET.get("show") == "all"

    with open_connection() as conn:
        bookings_data = conn.execute(
            """
            SELECT
                bookings.id,
                bookings.booking_date,
                bookings.is_cancelled,
                stands.name AS stand_name,
                stands.area,
                users.name AS user_name
            FROM bookings
            JOIN stands
                ON bookings.stand_id = stands.id
            JOIN users
                ON bookings.user_id = users.id
            WHERE (? = 1 OR bookings.is_cancelled = 0)
            ORDER BY bookings.booking_date, bookings.id;
            """,
            [int(show_all)],
        ).fetchall()

    context = {
        "bookings": bookings_data,
        "show_all": show_all,
    }
    return render(request, "bookings/booking_list.html", context)


def booking_detail(request, booking_id):
    """Страница /bookings/<id>/: информация о бронировании."""
    with open_connection() as conn:
        booking = conn.execute(
            """
            SELECT
                bookings.id,
                bookings.booking_date,
                bookings.is_cancelled,
                stands.id AS stand_id,
                stands.name AS stand_name,
                users.name AS user_name,
                users.email AS user_email
            FROM bookings
            JOIN stands
                ON bookings.stand_id = stands.id
            JOIN users
                ON bookings.user_id = users.id
            WHERE bookings.id = ?;
            """,
            [booking_id],
        ).fetchone()

    context = {"booking": booking}
    return render(
        request,
        "bookings/booking_detail.html",
        context,
        status=404 if booking is None else 200,
    )


def statistics(request):
    """Страница /bookings/statistics/: статистика бронирований."""
    with open_connection() as conn:
        totals = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM bookings
                 WHERE is_cancelled = 0) AS active_bookings,
                COUNT(*) AS stands_count,
                MIN(area) AS min_area,
                MAX(area) AS max_area,
                AVG(area) AS avg_area,
                SUM(area) AS total_area
            FROM stands;
            """
        ).fetchone()

        by_stand = conn.execute(
            """
            SELECT
                stands.name AS stand_name,
                COUNT(bookings.id) AS bookings_count
            FROM stands
            LEFT JOIN bookings
                ON stands.id = bookings.stand_id
               AND bookings.is_cancelled = 0
            GROUP BY stands.id, stands.name
            ORDER BY bookings_count DESC, stands.name;
            """
        ).fetchall()

        by_user = conn.execute(
            """
            SELECT
                users.name AS user_name,
                COUNT(bookings.id) AS bookings_count
            FROM users
            LEFT JOIN bookings
                ON users.id = bookings.user_id
               AND bookings.is_cancelled = 0
            GROUP BY users.id, users.name
            ORDER BY bookings_count DESC, users.name;
            """
        ).fetchall()

        by_type = conn.execute(
            """
            SELECT
                stand_type,
                COUNT(*) AS stands_count,
                AVG(area) AS avg_area
            FROM stands
            GROUP BY stand_type
            ORDER BY stand_type;
            """
        ).fetchall()

        popular = conn.execute(
            """
            SELECT
                stands.name AS stand_name,
                COUNT(bookings.id) AS bookings_count
            FROM stands
            JOIN bookings
                ON stands.id = bookings.stand_id
            WHERE bookings.is_cancelled = 0
            GROUP BY stands.id, stands.name
            HAVING COUNT(bookings.id) > ?
            ORDER BY bookings_count DESC, stands.name;
            """,
            [1],
        ).fetchall()

        latest = conn.execute(
            """
            SELECT
                bookings.id,
                bookings.booking_date,
                stands.name AS stand_name,
                users.name AS user_name
            FROM bookings
            JOIN stands
                ON bookings.stand_id = stands.id
            JOIN users
                ON bookings.user_id = users.id
            ORDER BY bookings.id DESC
            LIMIT ?;
            """,
            [3],
        ).fetchall()

    context = {
        "totals": totals,
        "by_stand": by_stand,
        "by_user": by_user,
        "by_type": by_type,
        "popular": popular,
        "latest": latest,
    }
    return render(request, "bookings/statistics.html", context)
