import pytest

from filterables.types import get_json_type_for_value


def test_json_type_for_value_sqlite():
    assert get_json_type_for_value("sqlite", True) == ["true", "false"]
    assert get_json_type_for_value("sqlite", 1.0) == ["real"]
    assert get_json_type_for_value("sqlite", 1) == ["integer"]
    assert get_json_type_for_value("sqlite", "") == ["text"]


def test_json_type_for_value_mariadb():
    assert get_json_type_for_value("mariadb", True) == ["BOOLEAN"]
    assert get_json_type_for_value("mariadb", 1.0) == ["DOUBLE"]
    assert get_json_type_for_value("mariadb", 1) == ["INTEGER"]
    assert get_json_type_for_value("mariadb", "") == ["STRING"]


def test_json_type_for_value_mssql():
    assert get_json_type_for_value("mssql", True) == ["boolean"]
    assert get_json_type_for_value("mssql", 1.0) == ["number"]
    assert get_json_type_for_value("mssql", 1) == ["number"]
    assert get_json_type_for_value("mssql", "") == ["string"]


def test_json_type_for_value_mysql():
    assert get_json_type_for_value("mysql", True) == ["BOOLEAN"]
    assert get_json_type_for_value("mysql", 1.0) == ["DOUBLE"]
    assert get_json_type_for_value("mysql", 1) == ["INTEGER"]
    assert get_json_type_for_value("mysql", "") == ["STRING"]


def test_json_type_for_value_postgresql():
    assert get_json_type_for_value("postgresql", True) == ["boolean"]
    assert get_json_type_for_value("postgresql", 1.0) == ["number"]
    assert get_json_type_for_value("postgresql", 1) == ["number"]
    assert get_json_type_for_value("postgresql", "") == ["string"]


def test_json_type_for_value_bad_dialect():
    with pytest.raises(ValueError):
        get_json_type_for_value(None, True)


def test_json_type_for_value_bad_type():
    with pytest.raises(ValueError):
        get_json_type_for_value("sqlite", None)
