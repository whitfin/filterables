from fastapi import Query
from fastapi.exceptions import HTTPException
from pydantic import ValidationError

from filterables.filters import Filters
from filterables.pages import Paginator


def filters(filters: str = Query("{}")) -> Filters:
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
