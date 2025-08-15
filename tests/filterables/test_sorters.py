import pytest
from sqlmodel import Session, select

from filterables.sorters import SimpleSorter
from tests.conftest import Person


def test_simple_sorter_priority():
    """
    Test the priority of simple sorting is low.
    """
    assert SimpleSorter.priority() == 999


def test_simple_sorter_ascending(session: Session):
    """
    Test that simple sorting can be oredered ascending.
    """
    query = select(Person)
    query = SimpleSorter.sort(session, query, Person, "id:asc")

    assert str(query).endswith("ORDER BY person.id ASC")


def test_simple_sorter_descending(session: Session):
    """
    Test that simple sorting can be oredered descending.
    """
    query = select(Person)
    query = SimpleSorter.sort(session, query, Person, "id:desc")

    assert str(query).endswith("ORDER BY person.id DESC")


def test_simple_sorter_default_direction(session: Session):
    """
    Test that simple sorting direction defaults to ASC.
    """
    query = select(Person)
    query = SimpleSorter.sort(session, query, Person, "id")

    assert str(query).endswith("ORDER BY person.id ASC")


def test_simple_sorter_invalid_field(session: Session):
    """
    Test simple sorting with an invalid field skips the sorting.
    """
    assert SimpleSorter.sort(session, select(Person), Person, ":desc") is None


def test_simple_sorter_invalid_direction(session: Session):
    """
    Test simple sorting with an invalid direction causes an error.
    """
    with pytest.raises(ValueError, match="'id' is not a valid Direction"):
        query = select(Person)
        query = SimpleSorter.sort(session, query, Person, "id:id")
