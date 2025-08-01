from inspect import isclass
from typing import Any, TypeVar

from pydantic import BaseModel, model_validator
from sqlmodel import text
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
        """
        field = cls.path(path) if isinstance(path, str) else path

        return field != text("'null'") if isinstance(field.type, NestableType) else field.isnot(None)

    @classmethod
    def path(cls, path: str) -> Any:
        """
        Retrieve a field reference from a data model by dot-separated path.
        """
        paths = path.split(".", 1)
        field = getattr(cls, paths[0])
        return field[paths[1]] if len(paths) > 1 else field

    def drop(self: T, paths: list[str]) -> T:
        """
        Drop a list of excluded fields from a Filterable.
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

    @model_validator(mode="after")
    def unpack(self) -> "Filterable":
        """
        Transform nested types to their corresponding models.
        """
        for field, definition in self.model_fields.items():
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

    @classmethod
    def from_query(cls, query: SelectOfScalar["Filterable"]) -> type["Filterable"]:
        """
        Infer a Filterable model type from a query, if available.
        """
        for column in query.column_descriptions:
            ct = column["type"]
            if isclass(ct) and issubclass(ct, Filterable):
                return ct

        raise Exception("Unable to determine Filterable query model")


# define a type variable for use with Generic
FilterableT = TypeVar("FilterableT", bound=Filterable)

from filterables.fields import Jsonable  # noqa
from filterables.fields import NestableType  # noqa
