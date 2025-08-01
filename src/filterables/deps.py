from fastapi import Query
from fastapi.exceptions import HTTPException
from pydantic import ValidationError

from filterables.filters import Filters
from filterables.pages import Paginator


def filters(filters: str = Query("{}")) -> Filters:
    """
    FastAPI compatible query parameter Filter parsing.
    """
    try:
        return Filters.model_validate_json(filters)
    except ValidationError:
        raise HTTPException(status_code=400, detail="Unable to validate filter syntax")


# forwards compat
paginate = Paginator
