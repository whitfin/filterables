from abc import ABC, abstractmethod
from typing import Any, Union

from pydantic import Field, RootModel
from sqlalchemy import not_
from sqlmodel import REAL, cast, func
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Annotated

from filterables import Filterable


class Filter(Filterable, ABC, extra="forbid"):
    """
    Abstract base model for all filter leaf Filters.
    """

    @abstractmethod
    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query  # pragma: no cover


class FilterBetween(Filter):
    """
    Filter to compare a value against upper/lower bounds ($lt/$gt).
    """

    lower: int | float = Field(alias="$gt")
    upper: int | float = Field(alias="$lt")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(cast(field, REAL) > self.lower).where(cast(field, REAL) < self.upper)


class FilterEquals(Filter):
    """
    Filter to compare against a single value ($eq).
    """

    value: Any = Field(alias="$eq")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(field == self.value)


class FilterGreaterThan(Filter):
    """
    Filter to compare against a minimum value ($lt).
    """

    value: int | float = Field(alias="$gt")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(cast(field, REAL) > self.value)


class FilterHas(Filter):
    """
    Filter to check existence of a field ($has).
    """

    value: bool = Field(alias="$has")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(field != None) if self.value else query.where(field == None)  # noqa: E711


class FilterIn(Filter):
    """
    Filter to compare against a list of values ($in).
    """

    value: list[Any] = Field(alias="$in")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(field.in_(list(self.value)))


class FilterLike(Filter):
    """
    Filter to compare against a pattern ($like).
    """

    value: str = Field(alias="$like")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(field.ilike(self.value))


class FilterLessThan(Filter):
    """
    Filter to compare against a maximum value ($lt).
    """

    value: int | float = Field(alias="$lt")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(cast(field, REAL) < self.value)


class FilterNotEquals(Filter):
    """
    Filter to compare against not being a single value ($ne).
    """

    value: Any = Field(alias="$ne")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(field != self.value)


class FilterNotIn(Filter):
    """
    Filter to compare against not being in a list of values ($nin).
    """

    value: list[Any] = Field(alias="$nin")

    def attach(self, query: SelectOfScalar[Filterable], field: Any) -> SelectOfScalar[Filterable]:
        """
        Attach a filter to a resource query.
        """
        return query.where(not_(field.in_(list(self.value))))


# the typing here looks scary, but it's just {"x.y.z" => Filter} defined using the Filter impls
class Filters(RootModel[dict[str, Annotated[Union[tuple(Filter.__subclasses__())], "discriminator"]]]):  # type: ignore
    """
    Bindable implementation to control model filtering.
    """

    def apply(
        self, query: SelectOfScalar[Filterable], model: type[Filterable] | None = None
    ) -> SelectOfScalar[Filterable]:
        """
        Apply filters to the provided query.

        The model type will be inferred, but you can provide it as an optional
        argument if you hit issues with the automatic detection.
        """
        # infer query model if not provided by user
        model = model or Filterable.from_query(query)

        for key, value in self.root.items():
            try:
                # locate base model field
                split = key.split(".")
                field = model.path(split[0])
            except AttributeError:  # pragma: no cover
                continue

            # find JSON nest
            if len(split) > 1:
                field = func.json_extract(field, '$."' + '"."'.join(split[1:]) + '"')

            # attach the query Filters
            query = value.attach(query, field)

        # write filters to self for later refs
        setattr(query, "_filterables", self)

        return query
