from models import User
from models.users import add_user, find_user, find_user_by_id


def test_user_creation():
    user = User(1, "Иван Петров", "ivan@example.com")
    assert user.id == 1
    assert user.name == "Иван Петров"
    assert user.email == "ivan@example.com"


def test_user_str():
    user = User(1, "Иван Петров", "ivan@example.com")
    text = str(user)
    assert "Иван Петров" in text
    assert "ivan@example.com" in text


def test_user_from_data():
    data = {
        "id": 1,
        "name": "Иван Петров",
        "email": "ivan@example.com",
    }
    user = User.from_data(data)
    assert user.id == 1
    assert user.name == "Иван Петров"


def test_add_user():
    users = []
    user = add_user(users, "Анна", "anna@example.com")
    assert len(users) == 1
    assert user.id == 1


def test_find_user():
    users = []
    add_user(users, "Иван Петров", "ivan@example.com")
    add_user(users, "Анна Смирнова", "anna@example.com")
    result = find_user(users, "иван")
    assert len(result) == 1
    assert result[0].name == "Иван Петров"


def test_find_user_by_id():
    users = []
    add_user(users, "Иван", "ivan@example.com")
    assert find_user_by_id(users, 1) is not None
    assert find_user_by_id(users, 999) is None
