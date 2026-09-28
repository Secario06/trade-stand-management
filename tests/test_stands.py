from models import Stand
from models.stands import (
    add_stand,
    find_stand,
    find_stand_by_id,
    filter_stands_by_area,
    sort_stands_by_area,
)


def test_stand_creation():
    stand = Stand(1, "Павильон А", 25.0, "Стандарт")
    assert stand.id == 1
    assert stand.name == "Павильон А"
    assert stand.area == 25.0
    assert stand.stand_type == "Стандарт"


def test_stand_str():
    stand = Stand(1, "Павильон А", 25.0, "Стандарт")
    text = str(stand)
    assert "Павильон А" in text
    assert "25.0" in text


def test_validate_area():
    assert Stand.validate_area(25.0)
    assert not Stand.validate_area(0)


def test_stand_from_data():
    data = {
        "id": 1,
        "name": "Павильон А",
        "area": 25.0,
        "type": "Стандарт",
    }
    stand = Stand.from_data(data)
    assert stand.id == 1
    assert stand.name == "Павильон А"


def test_add_stand():
    stands = []
    new_stand = add_stand(stands, "Павильон А", 25.0, "Стандарт")
    assert len(stands) == 1
    assert new_stand.id == 1


def test_find_stand():
    stands = []
    add_stand(stands, "Павильон А", 25.0, "Стандарт")
    add_stand(stands, "Премиум Зона", 50.0, "Премиум")
    result = find_stand(stands, "павильон")
    assert len(result) == 1
    assert result[0].name == "Павильон А"


def test_filter_stands_by_area():
    stands = []
    add_stand(stands, "Малый", 10.0, "Стандарт")
    add_stand(stands, "Большой", 100.0, "Премиум")
    filtered = filter_stands_by_area(stands, 50.0)
    assert len(filtered) == 1
    assert filtered[0].name == "Большой"


def test_sort_stands_by_area():
    stands = []
    add_stand(stands, "Большой", 100.0, "Премиум")
    add_stand(stands, "Малый", 10.0, "Стандарт")
    add_stand(stands, "Средний", 50.0, "Стандарт")
    sorted_stands = sort_stands_by_area(stands)
    areas = [s.area for s in sorted_stands]
    assert areas == [10.0, 50.0, 100.0]


def test_find_stand_by_id():
    stands = []
    add_stand(stands, "Павильон А", 25.0, "Стандарт")
    found = find_stand_by_id(stands, 1)
    assert found is not None
    assert found.name == "Павильон А"
    assert find_stand_by_id(stands, 999) is None
