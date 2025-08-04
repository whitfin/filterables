from functools import lru_cache
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine, text

from filterables import Filterable
from filterables.fields import Jsonable, Nestable


class PersonMetadata(Filterable):
    """
    Basic nestable class for test purposes.
    """

    email: str
    latitude: float
    longitude: float
    registered: bool


class Person(Filterable, SQLModel, table=True):
    """
    Basic filterable class for test purposes.
    """

    id: str = Field(default=None, primary_key=True)
    age: int
    name: str
    loose: PersonMetadata = Nestable(Jsonable)
    strong: PersonMetadata = Nestable(PersonMetadata)


@lru_cache
def engine() -> Engine:
    """
    Connect to a local SQLite engine for test purposes.
    """
    from sqlmodel.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )

    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys = ON"))
        connection.execute(text("PRAGMA journal_mode = WAL"))
        connection.commit()

    return engine


@pytest.fixture
def session() -> Session:
    """
    Fixture to yield a clean database session.
    """
    with Session(engine()) as session:
        yield session


@pytest.fixture(autouse=True)
def clean(session: Session):
    """
    Fixture to ensure a clean database state prior to each test.
    """
    session.exec(text(f"DELETE FROM {Person.__table__.name}"))
    session.commit()


@pytest.fixture
def people_1(session: Session) -> list[Person]:
    """
    Fixture to bootstrap a session with a `Person` record.
    """
    yield populated(session, Person, "tests/resources/people-1")


@pytest.fixture
def people_25(session: Session) -> list[Person]:
    """
    Fixture to bootstrap a session with 25 `Person` records.
    """
    yield populated(session, Person, "tests/resources/people-25")


@pytest.fixture
def people_100(session: Session) -> list[Person]:
    """
    Fixture to bootstrap a session with 100 `Person` records.
    """
    yield populated(session, Person, "tests/resources/people-100")


@pytest.fixture
def person_1(people_1: list[Person]) -> Person:
    """
    Fixture to bootstrap a session with a `Person` record.
    """
    yield people_1[0]


def populated(session: Session, model: type[Filterable], source: str):
    """
    Populate a dataset from a JSONL source location.
    """
    results = []

    for entry in (Path(source) / "dataset.jsonl").read_text().splitlines():
        entry = model.model_validate_json(entry)

        session.add(entry)
        session.commit()
        session.refresh(entry)

        results.append(entry)

    return results


# bind all the tests models to db
SQLModel.metadata.create_all(engine())
