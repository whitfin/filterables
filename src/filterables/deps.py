from typing import Annotated

from fastapi import Query
from fastapi.exceptions import HTTPException
from pydantic import GetJsonSchemaHandler, GetPydanticSchema, Json, TypeAdapter, ValidationError
from pydantic.json_schema import JsonSchemaValue
from pydantic_core.core_schema import CoreSchema

from filterables.filters import Filters
from filterables.pages import Paginator


def _filters_json_schema(_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
    """
    Describe the query string as JSON-encoded Filters for schema generation.
    """
    return handler(TypeAdapter(Json[Filters]).core_schema)


_FiltersQuery = Annotated[
    str,
    GetPydanticSchema(get_pydantic_json_schema=_filters_json_schema),
    Query(
        description="JSON-encoded mapping of field paths to Filter operators.",
        json_schema_extra={"x-filterables": True},
        openapi_examples={
            "combined_filters": {
                "summary": "Combine equality, an exclusive range, and membership",
                "value": '{"id":{"$in":["2","3"]},"age":{"$gt":18,"$lt":35},"name":{"$eq":"Bob"}}',
            },
        },
    ),
]


def filters(filters: _FiltersQuery = "{}") -> Filters:
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


# forwards compat
paginate = Paginator
