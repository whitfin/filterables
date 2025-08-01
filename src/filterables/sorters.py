from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from filterables import Filterable


class Direction(str, Enum):
    """
    Small Enum representing sort direction (ascending or descending).
    """

    ASCENDING = "asc"
    DESCENDING = "desc"


class Sorter(ABC):
    """
    Abstract class for use when parsing sort parameters.
    """

    @classmethod
    @abstractmethod
    def apply(
        cls, value: str, model: type[Filterable], query: SelectOfScalar[Filterable], session: Session
    ) -> SelectOfScalar[Filterable] | None:
        """
        Apply this sorter to the current query.
        """

    @classmethod
    @abstractmethod
    def priority(cls) -> int:
        """
        Retrieve the priority order for this sorter.
        """


class SimpleSorter(Sorter):
    """
    Basic sorting class to support `field:direction` syntax.
    """

    @classmethod
    def apply(
        cls, value: str, model: type[Filterable], query: SelectOfScalar[Filterable], session: Session
    ) -> SelectOfScalar[Filterable] | None:
        """
        Apply this sorter to the current query.
        """
        try:
            # allow syntax (field)(:(asc|desc))?
            field, direction = cls.split(model, value)
        except AttributeError:  # pragma: no cover
            return None

        # filter out null for the sort field
        query = query.where(model.has(field))
        apply = field.desc() if direction == Direction.DESCENDING else field.asc()

        # apply sort direction
        return query.order_by(apply)

    @classmethod
    def priority(cls) -> int:
        """
        Retrieve the priority order for this sorter.
        """
        return 999

    @classmethod
    def split(cls, model: type[Filterable], value: str) -> tuple[Any, Direction]:
        """
        Retrieve a sorted field reference from a data model by name.
        """
        chunks = iter(value.split(":", 1))
        location = next(chunks)
        direction = Direction(next(chunks, "asc").lower())

        return model.path(location), direction
