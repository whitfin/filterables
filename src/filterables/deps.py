from copy import deepcopy
from typing import Annotated, Callable

from fastapi import Query
from fastapi.exceptions import HTTPException
from fastapi.params import Query as QueryParam
from pydantic import GetJsonSchemaHandler, GetPydanticSchema, Json, TypeAdapter, ValidationError
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import PydanticUndefined
from pydantic_core.core_schema import CoreSchema

from filterables.filters import Filters
from filterables.pages import Paginator


def _filters_json_schema(schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
    """
    Describe the query string as JSON-encoded Filters for schema generation.
    """
    return {**handler(schema), **handler(TypeAdapter(Json[Filters]).core_schema)}


_FiltersQuery = Annotated[str, GetPydanticSchema(get_pydantic_json_schema=_filters_json_schema)]

_FiltersDefault = Query(
    description="JSON-encoded mapping of field paths to Filter operators.",
    json_schema_extra={"x-filterables": True},
    openapi_examples={
        "combined_filters": {
            "summary": "Filter for equality, an exclusive range, and membership.",
            "value": {
                "id": {"$in": ["2", "3"]},
                "age": {"$gt": 18, "$lt": 35},
                "name": {"$eq": "Bob"},
            },
        },
    },
)


def filters(filters: Annotated[_FiltersQuery, _FiltersDefault] = "{}") -> Filters:
    """
    FastAPI compatible query parameter `Filters` parsing.

    Args:
        filters:
            The `Filters` representation as a JSON encoded string, provided
            either directly or as part of the FastAPI Query binding.

    Returns:
        Filters:
            A decoded set of `Filters` derived from the JSON string.

    Raises:
        HTTPException:
            If the provided representation is invalid, this exception
            will be raised alongside a 422 error code to stop the request.
    """
    try:
        return Filters.model_validate_json(filters)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Unable to validate filter syntax")


def filters_dependency(query: QueryParam) -> Callable[[str], Filters]:
    """
    Create a Filters dependency with consumer-provided Query options.
    """
    query = deepcopy(query)
    query.alias = query.alias or "filters"

    # ensure that an empty filter set is provided at all times
    if query.default is PydanticUndefined and query.default_factory is None:
        query.default = "{}"

    # add default description
    if query.description is None:
        query.description = _FiltersDefault.description

    # provide our example documentation if none is provided
    if query.openapi_examples is None and query.examples is None:
        query.openapi_examples = deepcopy(_FiltersDefault.openapi_examples)

    # overwrite our values
    default = query.default
    query.default = PydanticUndefined
    query.json_schema_extra = {**(query.json_schema_extra or {}), "x-filterables": True}

    def _filters(value: Annotated[_FiltersQuery, query] = default) -> Filters:
        return filters(value)

    return _filters


# forwards compat
paginate = Paginator
