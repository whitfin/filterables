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


def test_filter_between_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters with invalid types.
    """
    assert _count(session, {"name": {"$gt": 30, "$lt": 40}}) == 0
    assert _count(session, {"active": {"$gt": 30, "$lt": 40}}) == 0


def test_filter_between_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters within a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$gt": 30, "$lt": 40}}) == 3


def test_filter_between_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters within a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.name": {"$gt": 30, "$lt": 40}}) == 0
    assert _count(session, {"jsonable.active": {"$gt": 30, "$lt": 40}}) == 0


def test_filter_between_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$gt": 30, "$lt": 40}}) == 3


def test_filter_between_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt/$lt filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"jsonable.name": {"$gt": 30, "$lt": 40}}) == 0
    assert _count(session, {"jsonable.active": {"$gt": 30, "$lt": 40}}) == 0


def test_filter_equals(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters.
    """

    assert _count(session, {"id": {"$eq": 1}}) == 1
    assert _count(session, {"age": {"$eq": 19}}) == 2
    assert _count(session, {"name": {"$eq": "Alec Bartoletti"}}) == 1
    assert _count(session, {"active": {"$eq": True}}) == 13
    assert _count(session, {"active": {"$eq": False}}) == 12


def test_filter_equals_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with invalid types.
    """
    assert _count(session, {"id": {"$eq": ""}}) == 0
    assert _count(session, {"age": {"$eq": ""}}) == 0
    assert _count(session, {"name": {"$eq": 1}}) == 0
    assert _count(session, {"active": {"$eq": ""}}) == 0  # MySQL doesn't handle this


def test_filter_equals_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.id": {"$eq": 1}}) == 1
    assert _count(session, {"jsonable.age": {"$eq": 19}}) == 2
    assert _count(session, {"jsonable.name": {"$eq": "Alec Bartoletti"}}) == 1
    assert _count(session, {"jsonable.active": {"$eq": True}}) == 13
    assert _count(session, {"jsonable.active": {"$eq": False}}) == 12


def test_filter_equals_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.id": {"$eq": ""}}) == 0
    assert _count(session, {"jsonable.age": {"$eq": ""}}) == 0
    assert _count(session, {"jsonable.name": {"$eq": 1}}) == 0
    assert _count(session, {"jsonable.active": {"$eq": ""}}) == 0


def test_filter_equals_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Nestable`.
    """
    assert _count(session, {"nestable.id": {"$eq": 1}}) == 1
    assert _count(session, {"nestable.age": {"$eq": 19}}) == 2
    assert _count(session, {"nestable.name": {"$eq": "Alec Bartoletti"}}) == 1
    assert _count(session, {"nestable.active": {"$eq": True}}) == 13
    assert _count(session, {"nestable.active": {"$eq": False}}) == 12


def test_filter_equals_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $eq filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.id": {"$eq": ""}}) == 0
    assert _count(session, {"nestable.age": {"$eq": ""}}) == 0
    assert _count(session, {"nestable.name": {"$eq": 1}}) == 0
    assert _count(session, {"nestable.active": {"$eq": ""}}) == 0


def test_filter_greater_than(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters.
    """
    assert _count(session, {"age": {"$gt": 30}}) == 19


def test_filter_greater_than_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with invalid types
    """
    assert _count(session, {"name": {"$gt": 30}}) == 0
    assert _count(session, {"active": {"$gt": 30}}) == 0


def test_filter_greater_than_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$gt": 30}}) == 19


def test_filter_greater_than_jsonable_invald(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.name": {"$gt": 30}}) == 0
    assert _count(session, {"jsonable.active": {"$gt": 30}}) == 0


def test_filter_greater_than_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$gt": 30}}) == 19


def test_filter_greater_than_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $gt filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.name": {"$gt": 30}}) == 0
    assert _count(session, {"nestable.active": {"$gt": 30}}) == 0


def test_filter_has(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters.
    """
    assert _count(session, {"id": {"$has": True}}) == 25
    assert _count(session, {"id": {"$has": False}}) == 0
    assert _count(session, {"none": {"$has": True}}) == 25  # ignored on the top level
    assert _count(session, {"none": {"$has": False}}) == 25
    assert _count(session, {"include": {"$has": True}}) == 11
    assert _count(session, {"include": {"$has": False}}) == 14


def test_filter_has_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.id": {"$has": True}}) == 25
    assert _count(session, {"jsonable.id": {"$has": False}}) == 0
    assert _count(session, {"jsonable.none": {"$has": True}}) == 0
    assert _count(session, {"jsonable.none": {"$has": False}}) == 25
    assert _count(session, {"jsonable.include": {"$has": True}}) == 11
    assert _count(session, {"jsonable.include": {"$has": False}}) == 14


def test_filter_has_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $has filters with a `Nestable`.
    """
    assert _count(session, {"nestable.id": {"$has": True}}) == 25
    assert _count(session, {"nestable.id": {"$has": False}}) == 0
    assert _count(session, {"nestable.none": {"$has": True}}) == 0
    assert _count(session, {"nestable.none": {"$has": False}}) == 25
    assert _count(session, {"nestable.include": {"$has": True}}) == 11
    assert _count(session, {"nestable.include": {"$has": False}}) == 14


def test_filter_in(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters.
    """
    assert _count(session, {"id": {"$in": [10, 20, 30]}}) == 2
    assert _count(session, {"age": {"$in": [19, 33, 44, 100]}}) == 4
    assert _count(session, {"name": {"$in": ["Alec Bartoletti", "Dave Cooper"]}}) == 1
    assert _count(session, {"active": {"$in": [True, False]}}) == 25
    assert _count(session, {"active": {"$in": [True]}}) == 13


def test_filter_in_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with invalid types.
    """
    assert _count(session, {"id": {"$in": [""]}}) == 0
    assert _count(session, {"age": {"$in": [""]}}) == 0
    assert _count(session, {"name": {"$in": [1]}}) == 0
    assert _count(session, {"active": {"$in": [""]}}) == 0


def test_filter_in_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.id": {"$in": [10, 20, 30]}}) == 2
    assert _count(session, {"jsonable.age": {"$in": [19, 33, 44, 100]}}) == 4
    assert _count(session, {"jsonable.name": {"$in": ["Alec Bartoletti", "Dave Cooper"]}}) == 1


def test_filter_in_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.id": {"$in": [""]}}) == 0
    assert _count(session, {"jsonable.age": {"$in": [""]}}) == 0
    assert _count(session, {"jsonable.name": {"$in": [1]}}) == 0
    assert _count(session, {"jsonable.active": {"$in": [""]}}) == 0


def test_filter_in_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Nestable`.
    """
    assert _count(session, {"nestable.id": {"$in": [10, 20, 30]}}) == 2
    assert _count(session, {"nestable.age": {"$in": [19, 33, 44, 100]}}) == 4
    assert _count(session, {"nestable.name": {"$in": ["Alec Bartoletti", "Dave Cooper"]}}) == 1


def test_filter_in_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $in filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.id": {"$in": [""]}}) == 0
    assert _count(session, {"nestable.age": {"$in": [""]}}) == 0
    assert _count(session, {"nestable.name": {"$in": [1]}}) == 0
    assert _count(session, {"nestable.active": {"$in": [""]}}) == 0


def test_filter_less_than(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters.
    """
    assert _count(session, {"age": {"$lt": 30}}) == 6


def test_filter_less_than_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with invalid types.
    """
    assert _count(session, {"name": {"$lt": 30}}) == 0
    assert _count(session, {"active": {"$lt": 30}}) == 0


def test_filter_less_than_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.age": {"$lt": 30}}) == 6


def test_filter_less_than_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.name": {"$lt": 30}}) == 0
    assert _count(session, {"jsonable.active": {"$lt": 30}}) == 0


def test_filter_less_than_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Nestable`.
    """
    assert _count(session, {"nestable.age": {"$lt": 30}}) == 6


def test_filter_less_than_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $lt filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.name": {"$lt": 30}}) == 0
    assert _count(session, {"nestable.active": {"$lt": 30}}) == 0


def test_filter_like(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters.
    """
    assert _count(session, {"email": {"$like": "%yahoo.com"}}) == 11


def test_filter_like_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with invalid types.
    """
    assert _count(session, {"age": {"$like": "19"}}) == 0
    assert _count(session, {"active": {"$like": "true"}}) == 0


def test_filter_like_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.email": {"$like": "%yahoo.com"}}) == 11


def test_filter_like_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.age": {"$like": "19"}}) == 0
    assert _count(session, {"jsonable.active": {"$like": "true"}}) == 0


def test_filter_like_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Nestable`.
    """
    assert _count(session, {"nestable.email": {"$like": "%yahoo.com"}}) == 11


def test_filter_like_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $like filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.age": {"$like": "19"}}) == 0
    assert _count(session, {"nestable.active": {"$like": "true"}}) == 0


def test_filter_not_equals(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters.
    """
    assert _count(session, {"id": {"$ne": 1}}) == 24
    assert _count(session, {"age": {"$ne": 19}}) == 23
    assert _count(session, {"name": {"$ne": "Alec Bartoletti"}}) == 24
    assert _count(session, {"active": {"$ne": True}}) == 12
    assert _count(session, {"active": {"$ne": False}}) == 13


def test_filter_not_equals_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with invalid types.
    """
    assert _count(session, {"id": {"$ne": ""}}) == 25
    assert _count(session, {"age": {"$ne": ""}}) == 25
    assert _count(session, {"name": {"$ne": 1}}) == 25
    assert _count(session, {"active": {"$ne": ""}}) == 25


def test_filter_not_equals_jsonable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Jsonable`.
    """
    assert _count(session, {"jsonable.id": {"$ne": 1}}) == 24
    assert _count(session, {"jsonable.age": {"$ne": 19}}) == 23
    assert _count(session, {"jsonable.name": {"$ne": "Alec Bartoletti"}}) == 24
    assert _count(session, {"jsonable.active": {"$ne": True}}) == 12
    assert _count(session, {"jsonable.active": {"$ne": False}}) == 13


def test_filter_not_equals_jsonable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Jsonable` with invalid types.
    """
    assert _count(session, {"jsonable.id": {"$ne": ""}}) == 25
    assert _count(session, {"jsonable.age": {"$ne": ""}}) == 25
    assert _count(session, {"jsonable.name": {"$ne": 1}}) == 25
    assert _count(session, {"jsonable.active": {"$ne": ""}}) == 25


def test_filter_not_equals_nestable(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Nestable`.
    """
    assert _count(session, {"nestable.id": {"$ne": 1}}) == 24
    assert _count(session, {"nestable.age": {"$ne": 19}}) == 23
    assert _count(session, {"nestable.name": {"$ne": "Alec Bartoletti"}}) == 24
    assert _count(session, {"nestable.active": {"$ne": True}}) == 12
    assert _count(session, {"nestable.active": {"$ne": False}}) == 13


def test_filter_not_equals_nestable_invalid(session: Session, people_25: list[Person]):
    """
    Test parsing and application of $ne filters with a `Nestable` with invalid types.
    """
    assert _count(session, {"nestable.id": {"$ne": 1}}) == 24
    assert _count(session, {"nestable.age": {"$ne": 19}}) == 23
    assert _count(session, {"nestable.name": {"$ne": "Alec Bartoletti"}}) == 24
    assert _count(session, {"nestable.active": {"$ne": True}}) == 12
    assert _count(session, {"nestable.active": {"$ne": False}}) == 13


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
    query = value.bind(session, query)

    (count,) = session.exec(query).first()

    return count
