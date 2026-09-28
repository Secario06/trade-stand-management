from typing import List, Optional


class User:
    """Арендатор торгового стенда."""

    def __init__(
        self,
        user_id: int,
        name: str,
        email: str,
    ) -> None:
        """Создать объект пользователя."""
        self.id = user_id
        self.name = name
        self.email = email

    @classmethod
    def from_data(cls, data: dict) -> "User":
        """Создать пользователя из набора данных JSON."""
        return cls(
            user_id=data["id"],
            name=data["name"],
            email=data["email"],
        )

    def to_data(self) -> dict:
        """Преобразовать объект в словарь для JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
        }

    def __str__(self) -> str:
        """Вернуть строковое представление пользователя."""
        return f"{self.name} ({self.email})"


def add_user(
    users: List[User],
    name: str,
    email: str,
) -> User:
    """Создать объект User и добавить его в коллекцию."""
    user_id = max([u.id for u in users], default=0) + 1
    user = User(user_id, name, email)
    users.append(user)
    return user


def find_user(users: List[User], query: str) -> List[User]:
    """Найти пользователей по имени или email."""
    query_lower = query.lower()
    result = []
    for user in users:
        if (
            query_lower in user.name.lower()
            or query_lower in user.email.lower()
        ):
            result.append(user)
    return result


def find_user_by_id(
    users: List[User], user_id: int
) -> Optional[User]:
    """Найти пользователя по идентификатору."""
    for user in users:
        if user.id == user_id:
            return user
    return None
