from typing import List, Optional


class Stand:
    """Торговый стенд для аренды."""

    def __init__(
        self,
        stand_id: int,
        name: str,
        area: float,
        stand_type: str,
    ) -> None:
        """Создать объект торгового стенда."""
        self.id = stand_id
        self.name = name
        self.area = area
        self.stand_type = stand_type

    @staticmethod
    def validate_area(area: float) -> bool:
        """Проверить корректность площади стенда."""
        return area > 0

    @classmethod
    def from_data(cls, data: dict) -> "Stand":
        """Создать объект Stand из словаря JSON."""
        return cls(
            stand_id=data["id"],
            name=data["name"],
            area=data["area"],
            stand_type=data["type"],
        )

    def to_data(self) -> dict:
        """Преобразовать объект в словарь для JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "area": self.area,
            "type": self.stand_type,
        }

    def __str__(self) -> str:
        """Вернуть строковое представление стенда."""
        return (
            f"{self.name} | Тип: {self.stand_type} | "
            f"Площадь: {self.area} кв.м."
        )


def add_stand(
    stands: List[Stand],
    name: str,
    area: float,
    stand_type: str,
) -> Stand:
    """Создать объект Stand и добавить его в коллекцию."""
    stand_id = max([s.id for s in stands], default=0) + 1
    stand = Stand(stand_id, name, area, stand_type)
    stands.append(stand)
    return stand


def find_stand(stands: List[Stand], query: str) -> List[Stand]:
    """Найти стенды по подстроке в названии."""
    query_lower = query.lower()
    return [s for s in stands if query_lower in s.name.lower()]


def find_stand_by_id(
    stands: List[Stand], stand_id: int
) -> Optional[Stand]:
    """Найти стенд по идентификатору."""
    for stand in stands:
        if stand.id == stand_id:
            return stand
    return None


def filter_stands_by_area(
    stands: List[Stand], min_area: float
) -> List[Stand]:
    """Отобрать стенды с площадью не меньше min_area."""
    return [s for s in stands if s.area >= min_area]


def sort_stands_by_area(stands: List[Stand]) -> List[Stand]:
    """Отсортировать стенды по площади."""
    return sorted(stands, key=lambda s: s.area)
