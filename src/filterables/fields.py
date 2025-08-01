from typing import Generic, TypeVar

from pydantic import Field as PydanticField
from sqlmodel import JSON, Column, TypeDecorator
from sqlmodel import Field as SQLField

from filterables import Filterable, FilterableT

T = TypeVar("T")


def Nestable(cls: type[Filterable], *args, **kwargs):
    """
    Create a Field to represent an inner Filterable model type.
    """
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
    Filterable class allowing for arbitrary JSON properties.
    """


def PydanticExampleField(value: T) -> T:
    """
    Create a Pydantic Field with an example value.
    """
    return PydanticField(examples=PydanticExampleValue(value))


def PydanticExampleValue(value: T) -> list[T]:
    """
    Create a Pydantic example value.
    """
    return [value]


def SQLExampleField(value: T, **kwargs) -> T:
    """
    Create a SQL Field with an example value.
    """
    return SQLField(schema_extra=SQLExampleValue(value), **kwargs)


def SQLExampleValue(value: T) -> dict[str, list[T]]:
    """
    Create a SQL example value.
    """
    return {"examples": [value]}
