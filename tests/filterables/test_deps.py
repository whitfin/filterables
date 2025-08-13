import json

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from filterables.deps import filters, paginate
from filterables.filters import Filters
from filterables.pages import Paginator


@pytest.fixture
def app() -> TestClient:
    """
    Generate a test app for FastAPI serialization.
    """
    app = FastAPI()

    @app.get("/filters")
    def get_filters(filters: Filters = Depends(filters), paginator: Paginator = Depends(paginate)) -> Filters:
        return filters

    @app.get("/paginator")
    def get_paginator(paginator: Paginator = Depends(paginate)) -> Paginator:
        return paginator

    return TestClient(app)


def test_filters_parsing(app: TestClient):
    """
    Test filters being parsed by the FastAPI handler.
    """
    filters = {
        "field1": {"$gt": 5},
        "field2": {"$eq": "hello"},
    }

    response = app.get("/filters", params={"filters": json.dumps(filters)})

    assert response.status_code == 200
    assert response.json() == filters


def test_filters_parsing_invalid(app: TestClient):
    """
    Test invalid filters being parsed by the FastAPI handler.
    """
    response = app.get("/filters", params={"filters": json.dumps({"field1": {}})})

    assert response.status_code == 422


def test_paginator_parsing(app: TestClient):
    """
    Test paginators being parsed by the FastAPI handler.
    """
    response = app.get(
        "/paginator",
        params={
            "sort": "value",
            "limit": 69,
            "offset": 96,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "limit": 69,
        "offset": 96,
        "sorting": ["value"],
        "excludes": [],
    }


def test_paginator_parsing_invalid(app: TestClient):
    """
    Test invalid paginators being parsed by the FastAPI handler.
    """
    response = app.get("/paginator", params={"limit": "invalid"})

    assert response.status_code == 422
