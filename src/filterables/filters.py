from __future__ import annotations

from abc import ABC
from typing import Annotated, Callable, Union

from pydantic import Field, RootModel
from sqlalchemy import select, try_cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Boolean, Float, Integer, Session, Text, case, func, literal, text
from sqlmodel.sql.expression import BinaryExpression, ColumnElement, SelectOfScalar, and_

from filterables import Filterable
from filterables.types import AnyJson, Comparable, get_column_type_for_value, get_json_type_for_value

# basic typing to save us writing this over and over
_Elem = ColumnElement | BinaryExpression
_Caster = Callable[[ColumnElement | Comparable], ColumnElement | Comparable]
_Condition = Callable[[ColumnElement, _Caster], ColumnElement]


class Filter(Filterable, ABC, extra="forbid"):
    """
    Abstract base model for all `Fiterable` filter implementations.
    """

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        Create a WHERE clause based on the `Filter` state.

        Args:
            column:
                The base SQLAlchemy column element that contains the nested data
                structure to be accessed.

            children:
                List of field names or keys that define the path to the target
                nested field (e.g., ['user', 'profile', 'age']).

            dialect:
                SQL dialect identifier that determines which casting functions
                and type conversion methods are available. Common values include
                'postgresql', 'mysql', 'sqlite'.

        Returns:
            ColumnElement | BinaryExpression:
                Returns a SQL type to be used as part of a WHERE clause within
                a `Filterable` SELECt query.
        """
        return literal(True)


class FilterBetween(Filter):
    """
    A `Filter` implementation to compare a value against upper/lower bounds ($lt/$gt).
    """

    lower: int | float = Field(alias="$gt")
    upper: int | float = Field(alias="$lt")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(
            column,
            children,
            dialect,
            self.lower,
            lambda value, cast: and_(value > cast(self.lower), value < cast(self.upper)),
        )


class FilterEquals(Filter):
    """
    A `Filter` implementation to compare against a single value ($eq).
    """

    value: str | int | float | bool = Field(alias="$eq")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(column, children, dialect, self.value, lambda value, cast: value == cast(self.value))


class FilterGreaterThan(Filter):
    """
    A `Filter` implementation to compare against a minimum value ($lt).
    """

    value: int | float = Field(alias="$gt")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(column, children, dialect, self.value, lambda value, cast: value > cast(self.value))


class FilterHas(Filter):
    """
    Filter to check existence of a field ($has).
    """

    value: bool = Field(alias="$has")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        path = get_child_ref(column, children, dialect)
        value = get_value_field(column, children, dialect)
        check: _Elem = ~value.is_(None)

        if children:
            if dialect == "sqlite":
                match = func.json_type(column, path) != "null"

            elif dialect == "postgresql":
                match = func.jsonb_typeof(value) != "null"

            elif dialect in ["mariadb", "mysql"]:
                match = func.json_type(value) != "NULL"

            else:
                match = value != "null"

            check = and_(check, match)

        return check if self.value else ~check


class FilterIn(Filter):
    """
    A `Filter` implementation to compare against a list of values ($in).
    """

    value: list[str] | list[int] | list[float] | list[bool] = Field(alias="$in")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(
            column,
            children,
            dialect,
            self.value[0],
            lambda value, cast: value.in_([cast(value) for value in self.value]),
        )


class FilterLike(Filter):
    """
    A `Filter` implementation to compare against a pattern ($like).
    """

    value: str = Field(alias="$like")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(column, children, dialect, self.value, lambda value, cast: value.like(cast(self.value)))


class FilterLessThan(Filter):
    """
    A `Filter` implementation to compare against a maximum value ($lt).
    """

    value: int | float = Field(alias="$lt")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return create_chain(column, children, dialect, self.value, lambda value, cast: value < cast(self.value))


class FilterNotEquals(Filter):
    """
    A `Filter` implementation to compare against not being a single value ($ne).
    """

    value: str | int | float | bool = Field(alias="$ne")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return ~FilterEquals.model_validate({"$eq": self.value}).create(column, children, dialect)


class FilterNotIn(Filter):
    """
    A `Filter` implementation to compare against not being in a list of values ($nin).
    """

    value: list[str] | list[int] | list[float] | list[bool] = Field(alias="$nin")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return ~FilterIn.model_validate({"$in": self.value}).create(column, children, dialect)


class FilterUnlike(Filter):
    """
    A `Filter` implementation to compare against a pattern ($unlike).
    """

    value: str = Field(alias="$unlike")

    def create(self, column: ColumnElement, children: list[str], dialect: str) -> _Elem:
        """
        See Filter.create() for documentation.
        """
        return ~FilterLike.model_validate({"$like": self.value}).create(column, children, dialect)


# the typing here looks scary, but it's just {"x.y.z" => Filter} defined using the Filter impls
class Filters(RootModel[dict[str, Annotated[Union[tuple(Filter.__subclasses__())], "discriminator"]]]):  # type: ignore
    """
    Grouped `Filter` implementations within a single container.

    This class enables parsing a JSON document directly into a set of `Filters`
    against their target field name in the form `{"x.y.z": Filter}`.
    """

    def bind(
        self, session: Session, query: SelectOfScalar[Filterable], model: type[Filterable] | None = None
    ) -> SelectOfScalar[Filterable]:
        """
        Check if a column has a compatible type with a comparable value.

        If the `comparable` value is not compatible with the column type, this
        function will return false.

        Args:
            session:
                A SQLAlchemy session, used to infer dialect and connection info.

            query:
                A SQLAlchemy SELECT query for a `Filterable` type, to bind this
                set of filters to.

            model:
                An optional `Filterable` to define the model type used inside
                the query SELECT. This will typically be inferred, but can be
                provided in case of issues with automatic detection.

        Returns:
            SelectOfScalar[Filterable]:
                Returns a copy of the provided query with all filters from this
                set bound (appended) to the WHERE clause. The original query is
                not directly modified by this function.
        """
        # infer query model if not provided by user
        model = model or Filterable.from_query(query)
        dialect = session.bind.dialect.name  # type: ignore[union-attr]

        for key, filter in self.root.items():
            try:
                chunks = key.split(".")
                column = getattr(model, chunks[0])
            except AttributeError:  # pragma: no cover
                continue

            # generated the filtered clauses for our field + dialect
            bound = filter.create(column, chunks[1:], dialect)
            query = query.where(bound)

        # write filters to self for later refs
        query._filterables = self  # type: ignore[attr-defined]

        return query


def create_chain(
    column: ColumnElement, children: list[str], dialect: str, comparable: Comparable, condition: _Condition
) -> ColumnElement:
    """
    Create a guarded column expression for nested data access.

    Builds a sequence of column operations that traverse nested data structures,
    applying the specified condition and comparison logic. Useful for accessing
    nested JSON fields transparently and handling database typing.

    This function is simply shorthand for calling various other utility functions
    in this module, and should only be called as part of a `Filter` implementation
    to ensure consistency with other library internals.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        dialect:
            SQL dialect identifier that determines which casting functions
            and type conversion methods are available. Common values include
            'postgresql', 'mysql', 'sqlite'.

        comparable:
            Sample value used for type inference. This value will be analyzed
            to determine the appropriate target type for casting operations.

        condition:
            A callable to define the logical operations being applied to the
            underlying value within the SQL expression.

    Returns:
        ColumnElement[bool]:
            A boolean column expression representing the chained condition that
            can be used in WHERE clauses within SQL queries.

    Example:
        Demonstration of doing a basic numeric comparison for a negative number:

        >>> lower_than = 0
        >>> clause = create_chain(
        ...     column,
        ...     children,
        ...     dialect,
        ...     lower_than,
        ...     lambda value, cast: value < cast(lower_than)
        ... )

        In this case the lambda callable is fed a SQL value, along with a casting
        function. This casting function should be used to cast comparison values
        to necessary types. If no casting is needed, this function will no-op.
    """
    # short circuit everything if we're not a valid type
    if not is_column_type(column, children, comparable):
        return literal(False)

    # generate the value and typing required to access the value
    value, typing = get_value_types(column, children, dialect, comparable)

    # generate the casting function and condition for the guard
    casting = create_caster(column, children, dialect, comparable)
    updated = condition(casting(value), casting)  # type: ignore
    guarded = create_guard(typing, updated, dialect)

    # guard the call
    return guarded


def create_caster(column: ColumnElement, children: list[str], dialect: str, comparable: Comparable) -> _Caster:
    """
    Create a casting function for data access, based on a comparable value.

    Generates a specialized casting function that can convert values to the
    appropriate type for the target nested field. The caster understands the
    database dialect's type system and uses the comparable value to infer the
    correct target type. If no casting is necessary, this will do nothing.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        dialect:
            SQL dialect identifier that determines which casting functions
            and type conversion methods are available. Common values include
            'postgresql', 'mysql', 'sqlite'.

        comparable:
            Sample value used for type inference. This value will be analyzed
            to determine the appropriate target type for casting operations.

    Returns:
        Callable[[ColumnElement[bool]], ColumnElement[bool]]:
            A callable type casting function, used to convert values to the
            appropriate type for the target value. This fucntion handles any
            dialect-specific type conversion and null value handling.
    """
    # only mssql types, with JSON nests
    if dialect == "mssql" and children:
        # force bool to JSON text (not 0 or 1)
        if isinstance(comparable, bool):
            return lambda value: literal("true" if value else "false") if isinstance(value, bool) else value

        # cast all numeric comparables to floats
        if isinstance(comparable, (int, float)):
            return lambda value: try_cast(value, Float)

        # JSON_VALUE already unquotes strings, so no cast is required
        return lambda value: value

    # only postgres types...
    if dialect == "postgresql":
        # cast comparables to a boolean
        if isinstance(comparable, bool):
            return lambda value: func.cast(value, Boolean)  # type: ignore

        # cast comparables to a float
        if isinstance(comparable, float):
            return lambda value: func.cast(value, Float)  # type: ignore

        # cast comparables to an integer
        if isinstance(comparable, int):
            return lambda value: func.cast(value, Integer)  # type: ignore

        # cast comparables to text,trim JSON quotes
        if isinstance(comparable, str):
            return lambda value: func.trim(func.cast(value, Text), '"')  # type: ignore

        # cast nests to JSON types
        if isinstance(column.type, tuple(AnyJson)):
            return lambda value: func.cast(value, JSON if isinstance(column.type, JSON) else JSONB)  # type: ignore

    # just in case, identity
    return lambda value: value


def create_guard(typing: ColumnElement | None, condition: ColumnElement, dialect: str) -> ColumnElement:
    """
    Create a guarded conditional expression for safe evaluation.

    Wraps a condition with optional type checking to prevent errors within strongly
    typed backends. The guard ensures the condition evaluates to FALSE if the types
    do not match, avoiding type conflicts within strongly typed backends.

    Args:
        typing:
            An optional typing clause produced by `get_value_types`, used to ensure
            nested typing within expressions. If no typing is provided, the condition
            clause will be returned as is.

        condition:
            A callable to define the logical operations being applied to the
            underlying value within the SQL expression.

    Returns:
        ColumnElement:
            A guarded filter clause, to be used within a SQL SELECT statement with
            ensured type safety based on the provided typing.
    """
    if typing is None:
        return condition

    if dialect == "mssql":
        return and_(typing, condition)

    return case((typing, condition), else_=text("FALSE"))


def get_child_ref(column: ColumnElement, children: list[str], dialect: str) -> list[str] | str:
    """
    Retrieve a dialect specific path reference to a provided child location.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        dialect:
            SQL dialect identifier that determines which casting functions
            and type conversion methods are available. Common values include
            'postgresql', 'mysql', 'sqlite'.

    Returns:
        str | list[str]:
            A dialect specific child path reference based on the provided
            list of children. The typing here should be considered as `Any`
            in case of new dialects being added/supported.
    """
    if dialect == "postgresql":
        return children

    if not children:
        return "$"

    return '$."' + '"."'.join(children) + '"'


def get_value_field(column: ColumnElement, children: list[str], dialect: str) -> ColumnElement:
    """
    Retrieve a reference to a dialect specific SQL value.

    This function can resolve to either a column directly, or an unpacked value
    within a JSON column based on the list of children provided.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        dialect:
            SQL dialect identifier that determines which casting functions
            and type conversion methods are available. Common values include
            'postgresql', 'mysql', 'sqlite'.

    Returns:
        ColumnElement:
            A SQL column (or nested field) reference based on the provided
            list of children, which can be used to access values in a table.
    """
    if not children:
        return column

    # resolve the child path for the dialect
    path = get_child_ref(column, children, dialect)

    # handle PostgreSQL types
    if dialect == "postgresql":
        prefix = "json" if isinstance(column, JSON) else "jsonb"
        return getattr(func, f"{prefix}_extract_path")(column, *path)

    # handle Microsoft/Oracle flavour
    if dialect in ["mssql", "oracle"]:
        return func.JSON_VALUE(column, path)

    # fallback to SQLite/MySQL flavours
    return func.json_extract(column, path)


def get_value_types(
    column: ColumnElement, children: list[str], dialect: str, comparable: Comparable
) -> tuple[ColumnElement, ColumnElement | None]:
    """
    Retrieve a reference to a SQL value, and guarded types for nested fields.

    Returned typing can be used alongside `create_guard` to provide type-safe
    access to nested fields for strongly typed backends. The returned value
    can differ to that returned by `get_value_field` due to context within the
    provided `comparable` value.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        dialect:
            SQL dialect identifier that determines which casting functions
            and type conversion methods are available. Common values include
            'postgresql', 'mysql', 'sqlite'.

        comparable:
            Sample value used for type inference. This value will be analyzed
            to determine the appropriate target type for casting operations.

    Returns:
        tuple[ColumnElement, ColumnElement | None]:
            A tuple containing:
                - A value reference (with optional nesting), which may or may
                  not differ to that returned by `get_value_field` due to having
                  additional context of a `comparable` value.
                - A typing clause which provides type safe access for strongly
                  typed backends. For use with `create_guard`.
    """
    # generate the caster for potentially nested values (can no op)
    value = get_value_field(column, children, dialect)
    typing = None

    # nesting
    if children:
        # handle SQLite type check
        if dialect == "sqlite":
            path = get_child_ref(column, children, dialect)
            typed = func.json_type(column, path)

        # handle PostgreSQL JSON/B check
        elif dialect == "postgresql":
            jsonb = "json" if isinstance(column, JSON) else "jsonb"
            typed = getattr(func, f"{jsonb}_typeof")(value)

        # handle the MySQL family
        elif dialect in ["mysql", "mariadb"]:
            # handle MySQL typing
            typed = func.JSON_TYPE(value)

            # handle MySQL unquotes for JSON content
            if isinstance(comparable, str):
                value = func.json_unquote(value)

        # handle the MSSQL family
        elif dialect == "mssql":
            # render the types from an OPENJSON subquery
            path = get_child_ref(column, children[:-1], dialect)
            types = func.OPENJSON(column, path).table_valued("key", "value", "type")

            # map OPENJSON types to their string representations
            names = case(
                (types.c.type == 1, "string"),
                (types.c.type == 2, "number"),
                (types.c.type == 3, "boolean"),
                (types.c.type == 4, "array"),
                (types.c.type == 5, "object"),
                else_="null",
            )

            # determine the type of the requested final child, or default to _ in case
            field = select(names).where(types.c.key == children[-1]).scalar_subquery()
            typed = func.isnull(field, "_")

        else:
            # skip anything else
            return value, typing

        # generate a clause to verify the field has the correct type
        typing = typed.in_(get_json_type_for_value(dialect, comparable))

    # return both params
    return value, typing


def is_column_type(column: ColumnElement, children: list[str], comparable: Comparable) -> bool:
    """
    Check if a column has a compatible type with a comparable value.

    If the `comparable` value is not compatible with the column type, this
    function will return false.

    Args:
        column:
            The base SQLAlchemy column element that contains the nested data
            structure to be accessed.

        children:
            List of field names or keys that define the path to the target
            nested field (e.g., ['user', 'profile', 'age']).

        comparable:
            Sample value used for type inference. This value will be analyzed
            to determine the appropriate target type for casting operations.

    Returns:
        bool:
            Returns true if the provided column is compatible with the provided
            comparable value, false otherwise.
    """
    return isinstance(column.type, tuple(get_column_type_for_value(comparable))) or len(children) > 0
