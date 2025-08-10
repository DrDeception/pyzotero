from pyzotero.lab_id import extract_lab_id, set_lab_id


def test_extract_and_set_lab_id():
    item = {"data": {"extra": ""}}
    assert extract_lab_id(item) is None
    set_lab_id(item, "000000123")
    assert extract_lab_id(item) == "000000123"
    set_lab_id(item, "000000124")
    assert extract_lab_id(item) == "000000124"
