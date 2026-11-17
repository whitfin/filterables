import json
from copy import deepcopy

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import create_model

from filterables.deps import filters, paginate
from filterables.filters import Filters
from filterables.openapi import with_filter_docs
from filterables.pages import Paginator


def test_filters_openapi():
    """
    Test the unconfigured string parameter describes its JSON content.
    """
    app = FastAPI()

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(filters)):
        return parsed

    schema = app.openapi()
    (parameter,) = schema["paths"]["/filters"]["get"]["parameters"]

    assert parameter["name"] == "filters"
    assert parameter["in"] == "query"
    assert parameter["required"] is False
    assert parameter["schema"]["type"] == "string"
    assert parameter["schema"]["default"] == "{}"
    assert parameter["schema"]["contentMediaType"] == "application/json"
    assert parameter["examples"] == {
        "combined_filters": {
            "summary": "Combine equality, an exclusive range, and membership",
            "value": '{"name":{"$eq":"Bob"},"age":{"$gt":18,"$lt":35},"id":{"$in":["2","3"]}}',
        },
    }

    reference = parameter["schema"]["contentSchema"]["$ref"]
    assert schema["components"]["schemas"][reference.rsplit("/", 1)[1]]["type"] == "object"


def test_filters_openapi_wrapper_leaves_app_unchanged():
    """
    Test creating the wrapper leaves the app's generator and schema cache untouched.
    """
    app = FastAPI()
    original_openapi = app.openapi

    with_filter_docs(original_openapi)

    assert app.openapi == original_openapi
    assert app.openapi_schema is None


@pytest.mark.parametrize("response_model", [None, Filters])
def test_filters_openapi_content(response_model):
    """
    Test the app hook links JSON parameter content to Filters and preserves other schemas.
    """
    app = FastAPI()

    @app.get("/filters", response_model=response_model)
    def get_filters(parsed: Filters = Depends(filters), paginator: Paginator = Depends(paginate)):
        return parsed

    original = deepcopy(app.openapi())
    app.openapi = with_filter_docs(app.openapi)
    schema = app.openapi()

    parameters = schema["paths"]["/filters"]["get"]["parameters"]
    parameter = next(parameter for parameter in parameters if parameter["name"] == "filters")

    assert parameter["in"] == "query"
    assert parameter["required"] is False
    assert parameter["description"] == "JSON-encoded mapping of field paths to Filter operators."
    assert "schema" not in parameter
    assert "examples" not in parameter
    assert parameter["content"] == {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/Filters",
                "default": {},
                "example": {"name": {"$eq": "Bob"}, "age": {"$gt": 18, "$lt": 35}, "id": {"$in": ["2", "3"]}},
            },
            "examples": {
                "combined_filters": {
                    "summary": "Combine equality, an exclusive range, and membership",
                    "value": {"name": {"$eq": "Bob"}, "age": {"$gt": 18, "$lt": 35}, "id": {"$in": ["2", "3"]}},
                },
            },
        }
    }
    expected = Filters.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = expected.pop("$defs")

    assert schema["components"]["schemas"]["Filters"] == expected
    for name, definition in definitions.items():
        assert schema["components"]["schemas"][name] == definition
    assert schema["components"] == original["components"]
    assert [parameter for parameter in parameters if parameter["name"] != "filters"] == [
        parameter for parameter in original["paths"]["/filters"]["get"]["parameters"] if parameter["name"] != "filters"
    ]
    assert app.openapi() is schema


@pytest.mark.parametrize("model_name", ["Filters", "FilterEquals"])
def test_filters_openapi_preserves_colliding_schemas(model_name):
    """
    Test filter references resolve correctly alongside unrelated models with the same names.
    """
    app = FastAPI()
    other_model = create_model(model_name, saved=(str, ...))

    @app.get("/other", response_model=other_model)
    def get_other():
        return {"saved": "example"}

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(filters)) -> Filters:
        return parsed

    original = deepcopy(app.openapi())
    app.openapi = with_filter_docs(app.openapi)
    schema = app.openapi()

    assert schema["components"] == original["components"]
    assert schema["paths"]["/other"] == original["paths"]["/other"]

    (parameter,) = schema["paths"]["/filters"]["get"]["parameters"]

    schemas = schema["components"]["schemas"]
    expected = Filters.model_json_schema()["$defs"]
    reference = parameter["content"]["application/json"]["schema"]["$ref"]

    for operator in schemas[reference.rsplit("/", 1)[1]]["additionalProperties"]["anyOf"]:
        definition = schemas[operator["$ref"].rsplit("/", 1)[1]]
        assert definition == expected[definition["title"]]


def test_filters_openapi_preserves_custom_generator():
    """
    Test configuration wraps an application's existing OpenAPI customizations.
    """
    app = FastAPI()

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(filters)):
        return parsed

    original_openapi = app.openapi

    def custom_openapi():
        schema = original_openapi()
        schema["info"]["x-custom"] = "preserved"
        return schema

    app.openapi = custom_openapi
    app.openapi = with_filter_docs(app.openapi)

    schema = app.openapi()
    assert schema["info"]["x-custom"] == "preserved"

    (parameter,) = schema["paths"]["/filters"]["get"]["parameters"]
    assert "application/json" in parameter["content"]


def test_filters_openapi_regeneration():
    """
    Test configuration before route registration and subsequent schema regeneration.
    """
    app = FastAPI()
    app.openapi = with_filter_docs(app.openapi)

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(filters)):
        return parsed

    original = deepcopy(app.openapi())
    app.openapi_schema = None

    assert app.openapi() == original


def test_filters_openapi_example_request():
    """
    Test documentation requested first provides a usable filter example.
    """
    app = FastAPI()

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(filters)) -> Filters:
        return parsed

    app.openapi = with_filter_docs(app.openapi)

    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    parameters = schema["paths"]["/filters"]["get"]["parameters"]
    parameter = next(parameter for parameter in parameters if parameter["name"] == "filters")

    content = parameter["content"]["application/json"]
    example = content["schema"]["example"]
    assert example == {"name": {"$eq": "Bob"}, "age": {"$gt": 18, "$lt": 35}, "id": {"$in": ["2", "3"]}}
    assert content["examples"]["combined_filters"]["value"] == example

    response = client.get("/filters", params={"filters": json.dumps(example)})
    assert response.status_code == 200
    assert response.json() == example


def test_filters_openapi_ignores_unrelated_parameters():
    """
    Test the app hook leaves unrelated filters parameters and components unchanged.
    """
    app = FastAPI()

    @app.get("/other")
    def get_other(filters: str = "{}"):
        return filters

    original = deepcopy(app.openapi())
    app.openapi = with_filter_docs(app.openapi)

    assert app.openapi() == original
