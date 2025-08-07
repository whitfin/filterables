from typing import Any

from sqlalchemy import func, select
from sqlmodel import Session

from filterables.filters import Filters
from tests.conftest import Person


def test_filter_between(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters.
    """
    assert _count(session, {"age": {"$gt": 30, "$lt": 40}}) == 3


def test_filter_between_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters within a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$gt": 30, "$lt": 40}}) == 3


def test_filter_between_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$gt": 30, "$lt": 40}}) == 3


def test_filter_equals(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters.
    """
    assert _count(session, {"age": {"$eq": 19}}) == 2


def test_filter_equals_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$eq": 19}}) == 2


def test_filter_equals_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$eq": 19}}) == 2


def test_filter_greater_than(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters.
    """
    assert _count(session, {"age": {"$gt": 30}}) == 19


def test_filter_greater_than_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$gt": 30}}) == 19


def test_filter_greater_than_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$gt": 30}}) == 19


def test_filter_has(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters.
    """
    assert _count(session, {"include": {"$has": True}}) == 11
    assert _count(session, {"include": {"$has": False}}) == 14


def test_filter_has_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.include": {"$has": True}}) == 11
    assert _count(session, {"jsonable.include": {"$has": False}}) == 14


def test_filter_has_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters with a `Nestable`.
    """
    assert _count(session, {"nestable.include": {"$has": True}}) == 11
    assert _count(session, {"nestable.include": {"$has": False}}) == 14


def test_filter_in(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters.
    """
    assert _count(session, {"age": {"$in": [19, 33, 44, 100]}}) == 4


def test_filter_in_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$in": [19, 33, 44, 100]}}) == 4


def test_filter_in_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$in": [19, 33, 44, 100]}}) == 4


def test_filter_less_than(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters.
    """
    assert _count(session, {"age": {"$lt": 30}}) == 6


def test_filter_less_than_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$lt": 30}}) == 6


def test_filter_less_than_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$lt": 30}}) == 6


def test_filter_like(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters.
    """
    assert _count(session, {"email": {"$like": "%yahoo.com"}}) == 11


def test_filter_like_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.email": {"$like": "%yahoo.com"}}) == 11


def test_filter_like_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Nestable`.
    """
    assert _count(session, {"nestable.email": {"$like": "%yahoo.com"}}) == 11


def test_filter_not_equals(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters.
    """
    assert _count(session, {"age": {"$ne": 19}}) == 23


def test_filter_not_equals_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$ne": 19}}) == 23


def test_filter_not_equals_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$ne": 19}}) == 23


def test_filter_not_in(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $nin filters.
    """
    assert _count(session, {"age": {"$nin": [19, 33, 44, 100]}}) == 21


def test_filter_not_in_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $nin filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$nin": [19, 33, 44, 100]}}) == 21


def test_filter_not_in_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $nin filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$nin": [19, 33, 44, 100]}}) == 21


def test_filter_unlike(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $unlike filters.
    """
    assert _count(session, {"email": {"$unlike": "%yahoo.com"}}) == 14


def test_filter_unlike_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $unlike filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.email": {"$unlike": "%yahoo.com"}}) == 14


def test_filter_unlike_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $unlike filters with a `Nestable`.
    """
    assert _count(session, {"nestable.email": {"$unlike": "%yahoo.com"}}) == 14


def _count(session: Session, filters: dict[str, Any]) -> int:
    """
    Count the number of people matching the provided JSON filters.
    """
    value = Filters.model_validate(filters)

    query = select(func.count(Person.id))
    query = value.bind(session, query, Person)

    (count,) = session.exec(query).first()

    return count
