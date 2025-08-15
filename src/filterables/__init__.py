from inspect import isclass
from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Column, TypeDecorator
from sqlmodel import Field as SQLField
from sqlmodel.sql.expression import SelectOfScalar

T = TypeVar("T")


class Filterable(BaseModel):
    """
    Parent database model class for use with Pydantic and SQLModel.

    Filterables enable automatic filter binding integration with FastAPI.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def remove(self: T, paths: list[str]) -> T:
        """
        Remove a list of fields from a `Filterable`.

        Strongly typed root fields will be set to `None`, whereas nested fields
        inside either a dictionary or `Nestable` will be dropped completely.

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
                elif isinstance(base, Jsonable):
                    delattr(base, path[-1])

                # or set to None
                else:
                    setattr(base, path[-1], None)

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

            ce = column["entity"]
            if isclass(ce) and issubclass(ce, Filterable):
                return ce

        raise ValueError("Unable to determine Filterable query model")

    @model_validator(mode="after")
    def handle_validation(self) -> "Filterable":
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
        sa_column=Column(NestableType(cls)),
        schema_extra=extra,
        **kwargs,
    )


class NestableType(TypeDecorator, Generic[FilterableT]):
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
    "NestableType",
]
