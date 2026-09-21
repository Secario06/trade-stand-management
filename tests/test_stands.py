from stands import (
    add_stand,
    find_stand,
    filter_stands_by_area,
)


def test_add_stand():
    stands = {}
    stand_id = add_stand(stands, "Павильон А", 25.0, "Стандарт")
    assert len(stands) == 1
    assert stands[stand_id]["name"] == "Павильон А"


def test_find_stand():
    stands = {}
    add_stand(stands, "Павильон А", 25.0, "Стандарт")
    add_stand(stands, "Премиум Зона", 50.0, "Премиум")
    result = find_stand(stands, "павильон")
    assert len(result) == 1
    assert list(result.values())[0]["name"] == "Павильон А"


def test_filter_stands_by_area():
    stands = {}
    add_stand(stands, "Малый", 10.0, "Стандарт")
    add_stand(stands, "Большой", 100.0, "Премиум")
    filtered = filter_stands_by_area(stands, 50.0)
    assert len(filtered) == 1
    assert list(filtered.values())[0]["name"] == "Большой"
