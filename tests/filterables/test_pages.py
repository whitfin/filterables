# from sqlalchemy import select
# from src.data import get_database_session
# from src.models.core.fields import Freeform
# from src.models.core.pnames import Paginator, run_paginator
# from src.models.schema.recipe import Recipe
# from src.models.schema.report import Report
# from src.models.schema.revision import Revision
from sqlmodel import Session, select

from filterables.pages import Paginator
from tests.conftest import Person


def test_run_paginator_with_defaults(session: Session, people_25: list[Person]):
    """
    Test running a default paginator.
    """
    query = select(Person)

    paginator = Paginator()
    pagination = paginator.exec(session, query)

    assert pagination.count == len(people_25)
    assert pagination.params == paginator
    assert pagination.results == sorted(people_25, key=lambda person: person.id)


def test_run_paginator_with_limit_zero(session: Session, people_25: list[Person]):
    """
    Test running a paginator with limit 0.
    """
    query = select(Person)

    paginator = Paginator(limit=0)
    pagination = paginator.exec(session, query)

    assert pagination.count == len(people_25)
    assert pagination.params == paginator
    assert pagination.results == []


def test_run_paginator_with_single_sort(session: Session, people_25: list[Person]):
    """
    Test running a sorted paginator.
    """
    query = select(Person)

    paginator = Paginator(sorting=["name"])
    pagination = paginator.exec(session, query)

    assert pagination.count == len(people_25)
    assert pagination.params == paginator
    assert pagination.results == sorted(people_25, key=lambda person: person.name)


def test_run_paginator_with_single_sort_and_direction(session: Session, people_25: list[Person]):
    """
    Test running a directional paginator.
    """
    query = select(Person)

    paginator = Paginator(sorting=["name:desc"])
    pagination = paginator.exec(session, query)

    assert pagination.count == len(people_25)
    assert pagination.params == paginator
    assert pagination.results == sorted(people_25, key=lambda person: person.name, reverse=True)


def test_run_paginator_with_multi_sort_and_direction(session: Session, people_25: list[Person]):
    """
    Test running a multi-directional paginator.
    """
    query = select(Person)

    paginator = Paginator(sorting=["name:desc", "age:desc"])
    pagination = paginator.exec(session, query)

    assert pagination.count == len(people_25)
    assert pagination.params == paginator
    assert pagination.results == sorted(people_25, key=lambda person: (person.name, person.age), reverse=True)


def test_run_paginator_with_excluded_root_fields(session: Session, people_1: list[Person]):
    """
    Test running a paginator with root fields being excluded.
    """
    query = select(Person)

    paginator = Paginator(limit=1)
    pagination = paginator.exec(session, query)

    assert pagination.count == 1
    assert pagination.params == paginator
    assert pagination.results[0].name == "Violette Hermann"

    paginator = Paginator(limit=1, excludes=["name"])
    pagination = paginator.exec(session, query)

    assert pagination.count == 1
    assert pagination.params == paginator
    assert pagination.results[0].name is None


def test_run_paginator_with_exluded_nested_fields(session: Session, people_1: list[Person]):
    """
    Test running a paginator with nested and custom fields being excluded.
    """
    query = select(Person)

    paginator = Paginator(limit=1)
    pagination = paginator.exec(session, query)

    assert pagination.count == 1
    assert pagination.params == paginator
    assert pagination.results[0].jsonable.name == "Violette Hermann"
    assert pagination.results[0].nestable.name == "Violette Hermann"

    paginator = Paginator(limit=1, excludes=["jsonable.name", "nestable.name"])
    pagination = paginator.exec(session, query)

    assert pagination.count == 1
    assert pagination.params == paginator
    assert getattr(pagination.results[0].jsonable, "name", None) is None
    assert getattr(pagination.results[0].nestable, "name", None) is None
