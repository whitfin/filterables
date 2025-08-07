from abc import ABC
from typing import Any, Union

from pydantic import Field, RootModel
from sqlmodel import REAL, Session, cast, func, text
from sqlmodel.sql.expression import ColumnElement, SelectOfScalar
from typing_extensions import Annotated

from filterables import Filterable


class Filter(Filterable, ABC, extra="forbid"):
    """
    Abstract base model for all filter leaf Filters.
    """

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return []


class FilterBetween(Filter):
    """
    Filter to compare a value against upper/lower bounds ($lt/$gt).
    """

    lower: int | float = Field(alias="$gt")
    upper: int | float = Field(alias="$lt")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [cast(field, REAL) > self.lower, cast(field, REAL) < self.upper]


class FilterEquals(Filter):
    """
    Filter to compare against a single value ($eq).
    """

    value: Any = Field(alias="$eq")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [field == self.value]


class FilterGreaterThan(Filter):
    """
    Filter to compare against a minimum value ($lt).
    """

    value: int | float = Field(alias="$gt")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [cast(field, REAL) > self.value]


class FilterHas(Filter):
    """
    Filter to check existence of a field ($has).
    """

    value: bool = Field(alias="$has")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [field != None if self.value else field == None]  # noqa: E711


class FilterIn(Filter):
    """
    Filter to compare against a list of values ($in).
    """

    value: list[Any] = Field(alias="$in")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [field.in_(list(self.value))]


class FilterLike(Filter):
    """
    Filter to compare against a pattern ($like).
    """

    value: str = Field(alias="$like")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [field.ilike(self.value)]


class FilterLessThan(Filter):
    """
    Filter to compare against a maximum value ($lt).
    """

    value: int | float = Field(alias="$lt")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [cast(field, REAL) < self.value]


class FilterNotEquals(Filter):
    """
    Filter to compare against not being a single value ($ne).
    """

    value: Any = Field(alias="$ne")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [field != self.value]


class FilterNotIn(Filter):
    """
    Filter to compare against not being in a list of values ($nin).
    """

    value: list[Any] = Field(alias="$nin")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [~field.in_(list(self.value))]


class FilterUnlike(Filter):
    """
    Filter to compare against a pattern ($unlike).
    """

    value: str = Field(alias="$unlike")

    def bind(self, field: Any) -> list[ColumnElement[bool]]:
        """
        Bind a filter to a resource query.
        """
        return [~field.ilike(self.value)]


# the typing here looks scary, but it's just {"x.y.z" => Filter} defined using the Filter impls
class Filters(RootModel[dict[str, Annotated[Union[tuple(Filter.__subclasses__())], "discriminator"]]]):  # type: ignore
    """
    Bindable implementation to control model filtering.
    """

    def bind(
        self, session: Session, query: SelectOfScalar[Filterable], model: type[Filterable] | None = None
    ) -> SelectOfScalar[Filterable]:
        """
        Bind filters to a provided query.

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
                dialect = session.bind.dialect.name  # type: ignore[union-attr]

                # support the Postgres way of nesting values
                if dialect == "postgresql":
                    field = text(split[0] + "#>>'{\"" + '","'.join(split[1:]) + "\"}'")

                # handle users of json_value and json_extract...
                else:
                    named = "JSON_VALUE" if dialect in ["mssql", "oracle"] else "json_extract"
                    field = getattr(func, named)(field, '$."' + '"."'.join(split[1:]) + '"')

            # bind the filtered clauses
            for clause in value.bind(field):
                query = query.where(clause)

        # write filters to self for later refs
        setattr(query, "_filterables", self)

        return query
