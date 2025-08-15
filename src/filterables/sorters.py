from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from filterables import Filterable


class Direction(str, Enum):
    """
    Small enumerable representing sort direction (ascending or descending).
    """

    ASCENDING = "asc"
    DESCENDING = "desc"


class Sorter(ABC):
    """
    Abstract class for use when parsing sort parameters.

    Subclassing `Sorter` will automatically bind your `Sorter` to the main
    `Paginator` lifecycle, easily allowing for custom sorting to be handled.
    """

    @classmethod
    @abstractmethod
    def priority(cls) -> int:
        """
        Retrieve the priority order for this sorter.

        Returns:
            int:
                A numeric priority value to determine priority between Sorter
                implementations. The closer to 0, the higher the priority.
        """

    @classmethod
    @abstractmethod
    def sort(
        cls, session: Session, query: SelectOfScalar[Filterable], model: type[Filterable], sorting: str
    ) -> SelectOfScalar[Filterable] | None:
        """
        Sort the provided query based on the current sorting implementation.

        Args:
            session:
                The SQLAlchemy Session for access to database state.
            query:
                The base `Filterable` SELECT query to apply sorting to.
            model:
                The `Filterable` type being used for selection.
            sorting:
                The sorting string being parsed and applied to this sort. The
                shape of this parameter is specific to the Sorter in use.

        Returns:
            SelectOfScalar[Filterable] | None:
                Returns a sorted SELECT clause based on the provided query, or
                None if this Sorter cannot sort using the provided sorting value.
        """


class SimpleSorter(Sorter):
    """
    Basic `Sorter` implementation to support `field:direction` syntax.
    """

    @classmethod
    def priority(cls) -> int:
        """
        See Sorter.priority() for documentation.
        """
        return 999

    @classmethod
    def sort(
        cls, session: Session, query: SelectOfScalar[Filterable], model: type[Filterable], sorting: str
    ) -> SelectOfScalar[Filterable] | None:
        """
        See Sorter.sort() for documentation.
        """
        try:
            # allow syntax (field)(:(asc|desc))?
            field, direction = cls.split(model, sorting)
        except AttributeError:  # pragma: no cover
            return None

        # filter out null for the sort field
        query = query.where(model.has(field))
        sort = field.desc() if direction == Direction.DESCENDING else field.asc()

        # sort sort direction
        return query.order_by(sort)

    @classmethod
    def split(cls, model: type[Filterable], value: str) -> tuple[Any, Direction]:
        """
        Retrieve a sorted field reference from a data model, by name.

        Args:
            model:
                The `Filterable` type being used to access the sorting field.
            value:
                The value being parsed and split into a directed sorting, by
                splitting on `":"` and returning a parsed direction segment.

        Returns:
            tuple[Any, Direction]:
                A tuple containing the column from the model being used for the
                sorting, and a `Direction` to signal which direction to sort in.
        """
        chunks = iter(value.split(":", 1))
        location = next(chunks)
        direction = Direction(next(chunks, "asc").lower())

        return model.path(location), direction
