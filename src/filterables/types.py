from typing import Any, TypeAlias

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import (
    CHAR,
    CLOB,
    DECIMAL,
    JSON,
    REAL,
    TIMESTAMP,
    VARCHAR,
    AutoString,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Float,
    Integer,
    Interval,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)

from filterables.fields import NestableType

# comparable types for use with filtering
Comparable: TypeAlias = bool | float | int | str

# define common groups
AnyBool = set([Boolean])
AnyDate = set([Date, DateTime, Interval, Time, TIMESTAMP])
AnyFloat = set([DECIMAL, Double, Float, Numeric, REAL])
AnyInteger = set([BigInteger, Integer, SmallInteger])
AnyJson = set([JSON, JSONB, NestableType])
AnyNumber = AnyInteger | AnyFloat
AnyString = AnyDate | set([AutoString, CHAR, CLOB, String, Text, VARCHAR])
AnyThing = AnyBool | AnyDate | AnyInteger | AnyFloat | AnyNumber | AnyString


def get_column_type_for_value(value: Comparable) -> set[Any]:
    """
    Fetch the applicable column types for the provided value.

    Args:
        value:
            The value to locate column types for.

    Returns:
        Set[Any]:
            Returns a set of column types associated with the type of the
            provided value.

    Raises:
        ValueError:
            This exception is raised on an invalid type provided. This will not
            happen internally, it only exists to notify invalid usage.
    """
    if isinstance(value, bool):
        return AnyBool

    if isinstance(value, float):
        return AnyFloat

    if isinstance(value, int):
        return AnyInteger

    if isinstance(value, str):
        return AnyString

    raise Exception("Unrecognised value type")


_json_types: dict[str, dict[type, str | list[str]]] = {
    "sqlite": {
        bool: [
            "true",
            "false",
        ],
        float: "real",
        int: "integer",
        str: "text",
    },
    "mysql": {
        bool: "BOOLEAN",
        float: "DOUBLE",
        int: "INTEGER",
        str: "STRING",
    },
    "postgresql": {
        bool: "boolean",
        float: "number",
        int: "number",
        str: "string",
    },
    "mssql": {
        bool: "boolean",
        float: "number",
        int: "number",
        str: "string",
    },
    "oracle": {
        bool: "boolean",
        float: "number",
        int: "number",
        str: "string",
    },
}


def get_json_type_for_value(value: Comparable, dialect: str) -> list[str]:
    """
    Fetch the applicable JSON types for the provided value and dialect.

    Args:
        value:
            The value to locate JSON types for.
        dialect:
            The dialect to use when resolving JSON type names.

    Returns:
        list[str]:
            Returns a list of JSON types associated with the type of the
            provided value.

    Raises:
        ValueError:
            This exception is raised on an invalid type provided. This will not
            happen internally, it only exists to notify invalid usage.
    """
    if (types := _json_types.get(dialect)) and (values := types.get(type(value))):
        return values if isinstance(values, list) else [values]

    raise ValueError("Unrecognised value type")
