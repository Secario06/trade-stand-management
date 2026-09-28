from models import Booking, Stand, User
from models.stands import (
    add_stand,
    find_stand,
    find_stand_by_id,
    filter_stands_by_area,
    sort_stands_by_area,
)
from models.users import (
    add_user,
    find_user_by_id,
)
from models.bookings import (
    cancel_booking,
    create_booking,
    get_booking_status,
    is_stand_available,
)
from storage import (
    load_stands,
    save_stands,
    load_users,
    save_users,
    load_bookings,
    save_bookings,
)
from utils import input_int, input_float, input_date

STANDS_FILE = "data/stands.json"
USERS_FILE = "data/users.json"
BOOKINGS_FILE = "data/bookings.json"


def show_stands(stands: list[Stand]) -> None:
    """Вывести список стендов."""
    if not stands:
        print("Список стендов пуст.")
        return
    print("\n--- Список торговых стендов ---")
    for stand in stands:
        print(f"ID: {stand.id} | {stand}")


def show_users(users: list[User]) -> None:
    """Вывести список пользователей."""
    if not users:
        print("Список пользователей пуст.")
        return
    print("\n--- Список пользователей ---")
    for user in users:
        print(f"ID: {user.id} | {user}")


def show_bookings(bookings: list[Booking]) -> None:
    """Вывести список бронирований."""
    if not bookings:
        print("Список бронирований пуст.")
        return
    print("\n--- Список бронирований ---")
    for booking in bookings:
        print(booking)


def create_new_booking(
    bookings: list[Booking],
    stands: list[Stand],
    users: list[User],
) -> None:
    """Создать новое бронирование через взаимодействие объектов."""
    stand_id = input_int("ID стенда: ")
    stand = find_stand_by_id(stands, stand_id)
    if stand is None:
        print(f"Стенд с ID {stand_id} не найден.")
        return

    user_id = input_int("ID пользователя: ")
    user = find_user_by_id(users, user_id)
    if user is None:
        print(f"Пользователь с ID {user_id} не найден.")
        return

    booking_date = input_date("Дата (ДД.ММ.ГГГГ): ")
    result = create_booking(bookings, stand, booking_date, user)
    if result is None:
        print("Ошибка: стенд уже занят на эту дату.")
    else:
        print(f"Бронирование создано (ID: {result.id}).")


def main() -> None:
    """Точка запуска приложения."""
    stands = load_stands(STANDS_FILE)
    users = load_users(USERS_FILE)
    bookings = load_bookings(BOOKINGS_FILE, stands, users)

    while True:
        print("\n=== Система управления торговыми стендами ===")
        print("1. Показать все стенды")
        print("2. Добавить стенд")
        print("3. Найти стенд по названию")
        print("4. Фильтр стендов по площади")
        print("5. Показать пользователей")
        print("6. Добавить пользователя")
        print("7. Проверить доступность стенда")
        print("8. Забронировать стенд")
        print("9. Отменить бронирование")
        print("10. Показать бронирования")
        print("0. Выход")

        choice = input_int("Выберите действие: ")

        if choice == 1:
            show_stands(stands)
        elif choice == 2:
            name = input("Название стенда: ")
            area = input_float("Площадь (кв.м.): ")
            s_type = input("Тип (Стандарт/Премиум/Остров): ")
            new_stand = add_stand(stands, name, area, s_type)
            save_stands(STANDS_FILE, stands)
            print(f"Стенд добавлен с ID {new_stand.id}.")
        elif choice == 3:
            query = input("Часть названия: ")
            results = find_stand(stands, query)
            if results:
                for stand in results:
                    print(f"ID: {stand.id} | {stand}")
            else:
                print("Ничего не найдено.")
        elif choice == 4:
            min_area = input_float("Минимальная площадь: ")
            filtered = filter_stands_by_area(stands, min_area)
            sorted_filtered = sort_stands_by_area(filtered)
            if sorted_filtered:
                for stand in sorted_filtered:
                    print(f"ID: {stand.id} | {stand}")
            else:
                print("Нет стендов с такой площадью.")
        elif choice == 5:
            show_users(users)
        elif choice == 6:
            name = input("Имя: ")
            email = input("Email: ")
            new_user = add_user(users, name, email)
            save_users(USERS_FILE, users)
            print(f"Пользователь добавлен с ID {new_user.id}.")
        elif choice == 7:
            stand_id = input_int("ID стенда: ")
            stand = find_stand_by_id(stands, stand_id)
            if stand is None:
                print("Стенд не найден.")
                continue
            date_str = input_date("Дата (ДД.ММ.ГГГГ): ")
            available = is_stand_available(bookings, stand, date_str)
            print(get_booking_status(available))
        elif choice == 8:
            create_new_booking(bookings, stands, users)
            save_bookings(BOOKINGS_FILE, bookings)
        elif choice == 9:
            booking_id = input_int("ID бронирования: ")
            if cancel_booking(bookings, booking_id):
                save_bookings(BOOKINGS_FILE, bookings)
                print("Бронирование отменено.")
            else:
                print("Бронирование не найдено.")
        elif choice == 10:
            show_bookings(bookings)
        elif choice == 0:
            print("Выход.")
            break
        else:
            print("Неверный пункт меню.")


if __name__ == "__main__":
    main()
