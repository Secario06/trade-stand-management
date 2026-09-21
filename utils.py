from datetime import datetime


def input_int(prompt: str) -> int:
    """Запрашивает у пользователя целое число с повторением при ошибке."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Ошибка: введите целое число.")


def input_float(prompt: str) -> float:
    """Запрашивает у пользователя число с плавающей точкой."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Ошибка: введите число (например, 25.5).")


def input_date(prompt: str) -> str:
    """Запрашивает дату в формате ДД.ММ.ГГГГ и возвращает строку ISO."""
    while True:
        date_str = input(prompt)
        try:
            # Проверка корректности формата
            parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            print("Ошибка: неверный формат даты. Используйте ДД.ММ.ГГГГ.")
