from inspect import isclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, model_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Column, TypeDecorator, text
from sqlmodel import Field as SQLField
from sqlmodel.sql.expression import ColumnElement, SelectOfScalar

T = TypeVar("T")


class Filterable(BaseModel):
    """
    Parent database model class for use with Pydantic and SQLModel.

    Filterables enable automatic filter binding integration with FastAPI.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def has(cls, path: str | Any) -> ColumnElement:
        """
        Create a filter for null values in a query, including JSON types.

        Args:
            path:
                The path within this model tree to check for existence.

        Returns:
            ColumnElement:
                Returns a WHERE clause which can be used within a SELECT query.
        """
        field = cls.path(path) if isinstance(path, str) else path

        return field != text("'null'") if isinstance(field.type, NestedFilterable) else field.isnot(None)

    @classmethod
    def path(cls, path: str) -> Any:
        """
        Retrieve a field reference from a data model, by dot-separated path.

        Args:
            path:
                The path within this model tree to search for.

        Returns:
            Any:
                Returns the value located at the end of a path. Either a root
                SQLModel field or a nested JSON reference.
        """
        paths = path.split(".", 1)
        field = getattr(cls, paths[0])
        return field[paths[1]] if len(paths) > 1 else field

    def drop(self: T, paths: list[str]) -> T:
        """
        Drop a list of excluded fields from a `Filterable`.

        Args:
            paths:
                The list of paths within this model to replace with a `None`
                type. Any invalid or missing paths will simply be ignored.

        Returns:
            T:
                Returns the current (potentially modified) instance to allow
                for easy chaining in transformation pipelines.
        """
        # split paths into segments before processing
        for path in (path.split(".") for path in paths):
            base = self
            length = len(path)

            # skip an invalid base segment
            if not hasattr(base, path[0]):
                continue

            # root field exclusion
            if length == 1:
                setattr(base, path[0], None)

            # nested exclusions
            if length > 1:
                # walk the nest to the leaf
                for nest in path[:-1]:
                    # Jsonable types
                    if hasattr(base, nest):
                        base = getattr(base, nest)

                    # dictionary types
                    elif nest in base:  # type: ignore
                        base = base[nest]  # type: ignore[index]

                # remove value from a dict
                if isinstance(base, dict):
                    del base[path[-1]]

                # or remove prop from a Jsonable
                if isinstance(base, Jsonable):
                    delattr(base, path[-1])

        return self

    @classmethod
    def from_query(cls, query: SelectOfScalar["Filterable"]) -> type["Filterable"]:
        """
        Infer a `Filterable` model from a query, if possible.

        Args:
            query:
                The `Filterable` SELECT query to infer a model type from.

        Returns:
            type["Filterable"]:
                Returns a `Filterable` subclass type, located via the query.

        Raises:
            ValueError:
                This exception is raised if a model cannot be inferred. If this
                happens, the query is likely not a valid `Filterable` selection.
        """
        for column in query.column_descriptions:
            ct = column["type"]
            if isclass(ct) and issubclass(ct, Filterable):
                return ct

        raise ValueError("Unable to determine Filterable query model")

    @model_validator(mode="after")
    def unpack(self) -> "Filterable":
        """
        Pydantic callback to transform nested types to their Pydantic models.
        """
        for field, definition in self.__class__.model_fields.items():
            # skip cases like list[str] (not nested)
            if not isclass(definition.annotation):
                continue

            # skip classes which don't inherit Filterable
            if not issubclass(definition.annotation, Filterable):
                continue

            # read value from the field
            value = getattr(self, field)

            # parse dict fields as models
            if isinstance(value, dict):
                setattr(self, field, definition.annotation(**value))

        return self


# define a type variable for use with Generic
FilterableT = TypeVar("FilterableT", bound=Filterable)


def Nestable(cls: type[Filterable], *args, **kwargs) -> type[Filterable]:
    """
    Create a Field to represent an inner `Filterable` model type.

    Args:
        cls:
            The `Filterable` type for the inner column.

    Returns:
        type[Filterable]:
            Returns a SQLField wrapping of the custom type T.
    """
    from filterables.types import SQLExampleValue

    value = SQLExampleValue(Jsonable())
    extra = kwargs.pop("schema_extra", value)

    return SQLField(
        *args,
        default_factory=cls,
        sa_column=Column(NestedFilterable(cls)),
        schema_extra=extra,
        **kwargs,
    )


class NestedFilterable(TypeDecorator, Generic[FilterableT]):
    """
    Custom decorator class to allow for nested Filterable models.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, model: type[Filterable], *args, **kwargs):
        """
        Initialize this decorator using a Pydantic model type.
        """
        super().__init__(*args, **kwargs)
        self.model = model

    def load_dialect_impl(self, dialect):
        """
        Select the dialect implementation.
        """
        return dialect.type_descriptor(JSONB() if dialect.name == "postgresql" else JSON())

    def process_bind_param(self, value, dialect):
        """
        Convert a nested model type to a dictionary.
        """
        return value.model_dump() if hasattr(value, "model_dump") else value

    def process_result_value(self, value, dialect):
        """
        Convert a dictionary to a nested model type.
        """
        if isinstance(value, dict):
            return self.model(**value) if value else self.model()

        return super().process_result_value(self, value, dialect)


class Jsonable(Filterable, extra="allow"):
    """
    A `Filterable` implementation allowing for arbitrary JSON properties.
    """


__all__ = [
    "Filterable",
    "FilterableT",
    "Jsonable",
    "Nestable",
    "NestedFilterable",
]
