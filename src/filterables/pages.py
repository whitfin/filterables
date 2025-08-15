from typing import Any, Generic, Iterator, Type, TypeVar

from fastapi import Query
from fastapi.params import Query as QueryParam
from pydantic import Field, field_serializer
from sqlalchemy import inspect
from sqlmodel import Session, func
from sqlmodel.sql.expression import SelectOfScalar, Sequence

from filterables import Filterable, FilterableT, Jsonable
from filterables.filters import Filters
from filterables.sorters import Sorter
from filterables.types import PydanticExampleField

T = TypeVar("T")


class Pagination(Filterable, Generic[FilterableT]):
    """
    A class representing the result of a Paginator run.
    """

    count: int
    params: "Paginator"
    filters: Filters = Field(examples=[Jsonable()])
    results: list[Filterable]

    @field_serializer("filters")
    def serialize_filters(self, filters: Filters):
        """
        Aliased model serializer for `Filters`.
        """
        return {key: value.model_dump(by_alias=True) for key, value in filters.root.items()}

    @field_serializer("results")
    def serialize_results(self, results: list[Filterable]):
        """
        Recursive model serializer for results.
        """
        return [result.model_dump(by_alias=True) for result in results]


class Paginator(Filterable):
    """
    A class used to paginate queries based on pagination rules.
    """

    limit: int = PydanticExampleField(25)
    offset: int = PydanticExampleField(0)
    sorting: list[str] = PydanticExampleField(["id"])
    excludes: list[str] = PydanticExampleField([])

    def __init__(
        self,
        limit: int = Query(25, ge=0),
        offset: int = Query(0, ge=0),
        sorting: list[str] = Query(["_pk"], alias="sort"),
        excludes: list[str] = Query([], alias="exclude"),
        **kwargs,
    ):
        """
        Initialize a pagination via pagination parameters.

        This constructor supports both manual construction as well as integrating
        with FastAPI as a dependency in order to parse query parameters from routes.

        Args:
            limit:
                The maximum amount of objects to return in each page.
            offset:
                The leading number of objects to skip before reading back values.
            sorting:
                A list of sorting values to apply across multiple fields. The
                format of this value depends on the `Sorter` implementations
                available inside this runtime.
            excludes:
                A list of fields to exclude from the paginated response.
        """
        super().__init__(
            limit=_query_parameter(limit),
            offset=_query_parameter(offset),
            sorting=[_strip_whitespace(sort) for sort in _query_parameter(sorting)],
            excludes=_query_parameter(excludes),
            **kwargs,
        )

    def exec(
        self, session: Session, query: SelectOfScalar[Filterable], filters: Filters | None = None
    ) -> Pagination[Filterable]:
        """
        Execute a `Paginator` using a query o generate a `Pagination`.

        Args:
            session:
                A SQLAlchemy `Session` used to communicate with the backing
                database for results.
            query:
                The `Filterable` SELECT query to be paginated by this instance.
            filters:
                An optional set of `Filters` to apply to the query before
                running pagination. This can be `None` to execute as is.

        Returns:
            Pagination[Filterable]:
                Returns a `Pagination` of results containing results of the
                same type defined in the query SELECT clauses.
        """
        query = filters.bind(session, query) if filters else query
        model = Filterable.from_query(query)
        sorts = sorted(Sorter.__subclasses__(), key=lambda sorter: sorter.priority())

        # fetch model metadata
        meta = inspect(model)
        pkey = meta.primary_key[0].name

        # append every sort field
        for sorting in self.sorting:
            # handle primary sort
            if sorting == "_pk":
                sorting = pkey

            # find our sorting
            for sorter in sorts:
                if (value := sorter.sort(session, query, model, sorting)) is not None:
                    query = value
                    break

        # apply the page limit, the page offset, and the column ordering
        model_exec = query.limit(self.limit).offset(self.offset)
        model_rows = session.exec(model_exec).all() if self.limit > 0 else []

        # create a count of the priamry key based on the resource query
        meta_trim = model_exec.with_only_columns(func.count(getattr(model, pkey)))
        meta_exec = meta_trim.offset(0).limit(1).order_by(None)
        meta_rows = session.exec(meta_exec).first()  # type: ignore[call-overload]

        # execute and summarize
        return Pagination(
            count=next(_map_rows([meta_rows], int)),
            params=self,
            filters=getattr(query, "_filterables", Filters({})),  # type: ignore[arg-type]
            results=[model.remove(self.excludes) for model in _map_rows(model_rows, model)],
        )


def _map_rows(rows: Sequence[Any], type: Type[T]) -> Iterator[T]:
    """
    Map a row back into the required type, either as itself or found in a column.
    """
    return (next(col for col in row if isinstance(col, type)) if not isinstance(row, type) else row for row in rows)


def _query_parameter(value: Any) -> Any:
    """
    Parse a query parameter value, falling to default when missing.
    """
    return None if value is None else value.get_default() if isinstance(value, QueryParam) else value


def _strip_whitespace(value: str) -> str:
    """
    Remove all whitespace from a string input.
    """
    return "".join(char for char in value if not char.isspace())
