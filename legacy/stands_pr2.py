def add_stand(stands: dict, name: str, area: float, stand_type: str) -> int:
    """Добавляет стенд в словарь и возвращает его ID."""
    stand_id = max(stands.keys(), default=0) + 1
    stands[stand_id] = {
        "name": name,
        "area": area,
        "type": stand_type
    }
    return stand_id


def find_stand(stands: dict, query: str) -> dict:
    """Ищет стенды по подстроке в названии."""
    query_lower = query.lower()
    found = {}
    for s_id, s_data in stands.items():
        if query_lower in s_data["name"].lower():
            found[s_id] = s_data
    return found


def filter_stands_by_area(stands: dict, min_area: float) -> dict:
    """Генератор: отбирает стенды с площадью не меньше min_area."""
    return {
        s_id: s_data
        for s_id, s_data in stands.items()
        if s_data["area"] >= min_area
    }


def sort_stands_by_area(stands: dict) -> dict:
    """Сортирует стенды по площади с использованием lambda-функции."""
    sorted_items = sorted(
        stands.items(),
        key=lambda item: item[1]["area"]
    )
    return dict(sorted_items)


def get_stand_description(stand_data: dict) -> str:
    """Возвращает краткое описание стенда (сохранено из ПР1)."""
    return (f"Тип: {stand_data['type']} | "
            f"Площадь: {stand_data['area']} кв.м.")
