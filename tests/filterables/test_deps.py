import json

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient

from filterables.deps import filters, filters_dependency, paginate
from filterables.filters import Filters
from filterables.pages import Paginator


@pytest.fixture
def app() -> TestClient:
    """
    Generate a test app for FastAPI serialization.
    """
    app = FastAPI()
    custom = filters_dependency(Query(alias="where", max_length=128))

    @app.get("/filters")
    def get_filters(filters: Filters = Depends(filters), paginator: Paginator = Depends(paginate)) -> Filters:
        return filters

    @app.get("/custom-filters")
    def get_custom_filters(parsed: Filters = Depends(custom)) -> Filters:
        return parsed

    @app.get("/paginator")
    def get_paginator(paginator: Paginator = Depends(paginate)) -> Paginator:
        return paginator

    return TestClient(app)


@pytest.mark.parametrize("path, parameter", [("/filters", "filters"), ("/custom-filters", "where")])
def test_filters_parsing(app: TestClient, path, parameter):
    """
    Test filters being parsed by the FastAPI handler.
    """
    filters = {
        "field1": {"$gt": 5},
        "field2": {"$eq": "hello"},
    }

    response = app.get(path, params={parameter: json.dumps(filters)})

    assert response.status_code == 200
    assert response.json() == filters


@pytest.mark.parametrize(
    "path, parameter, value",
    [
        ("/filters", "filters", "not-json"),
        ("/filters", "filters", '{"field1":{}}'),
        ("/custom-filters", "where", "not-json"),
        ("/custom-filters", "where", '{"field1":{}}'),
    ],
)
def test_filters_parsing_invalid(app: TestClient, path, parameter, value):
    """
    Test invalid filters being parsed by the FastAPI handler.
    """
    response = app.get(path, params={parameter: value})

    assert response.status_code == 422
    assert response.json() == {"detail": "Unable to validate filter syntax"}


@pytest.mark.parametrize("path", ["/filters", "/custom-filters"])
def test_filters_parsing_default(app: TestClient, path):
    """
    Test missing filters default to an empty set.
    """
    response = app.get(path)

    assert response.status_code == 200
    assert response.json() == {}


def test_filters_dependency_query_validation(app: TestClient):
    """
    Test consumer Query constraints still apply before parsing the JSON.
    """
    response = app.get("/custom-filters", params={"where": " " * 129})
    assert response.status_code == 422

    (error,) = response.json()["detail"]
    assert error["loc"] == ["query", "where"]
    assert error["type"] == "string_too_long"


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
