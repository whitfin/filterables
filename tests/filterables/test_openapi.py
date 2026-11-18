import json
from copy import deepcopy

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import create_model

from filterables.deps import filters, filters_dependency, paginate
from filterables.filters import Filters
from filterables.openapi import with_filter_docs
from filterables.pages import Paginator


@pytest.mark.parametrize("dependency", [filters, filters_dependency(Query())])
def test_filters_openapi(dependency):
    """
    Test the unconfigured string parameter describes its JSON content.
    """
    app = FastAPI()

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(dependency)):
        return parsed

    schema = app.openapi()
    (parameter,) = schema["paths"]["/filters"]["get"]["parameters"]

    assert parameter["name"] == "filters"
    assert parameter["in"] == "query"
    assert parameter["required"] is False
    assert parameter["schema"]["type"] == "string"
    assert parameter["schema"]["default"] == "{}"
    assert parameter["schema"]["contentMediaType"] == "application/json"
    assert set(parameter["examples"]) == {"combined_filters"}

    example = parameter["examples"]["combined_filters"]
    assert example["summary"] == "Filter for equality, an exclusive range, and membership."
    assert example["value"] == {
        "name": {"$eq": "Bob"},
        "age": {"$gt": 18, "$lt": 35},
        "id": {"$in": ["2", "3"]},
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
                "description": "JSON-encoded mapping of field paths to Filter operators.",
                "title": "Filters",
                "default": {},
                "example": {"name": {"$eq": "Bob"}, "age": {"$gt": 18, "$lt": 35}, "id": {"$in": ["2", "3"]}},
            },
            "examples": {
                "combined_filters": {
                    "summary": "Filter for equality, an exclusive range, and membership.",
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


def test_filters_dependency_openapi_options():
    """
    Test consumer metadata and examples override defaults and survive conversion.
    """
    app = FastAPI()
    dependency = filters_dependency(
        Query(
            description="Filter people by age.",
            title="People filters",
            deprecated=True,
            openapi_examples={"adults": {"summary": "Older than eighteen", "value": {"age": {"$gt": 18}}}},
            json_schema_extra={"x-supported-fields": ["age"], "x-filterables": False},
        )
    )

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(dependency)):
        return parsed

    app.openapi = with_filter_docs(app.openapi)
    (parameter,) = app.openapi()["paths"]["/filters"]["get"]["parameters"]

    assert parameter["description"] == "Filter people by age."
    assert parameter["deprecated"] is True

    content = parameter["content"]["application/json"]
    assert content["schema"]["$ref"] == "#/components/schemas/Filters"
    assert content["schema"]["title"] == "People filters"
    assert content["schema"]["x-supported-fields"] == ["age"]
    assert "x-filterables" not in content["schema"]
    assert content["schema"]["example"] == {"age": {"$gt": 18}}
    assert content["examples"] == {"adults": {"summary": "Older than eighteen", "value": {"age": {"$gt": 18}}}}


def test_filters_dependency_openapi_string_constraints():
    """
    Test string constraints describe the encoded query value only.
    """
    app = FastAPI()
    dependency = filters_dependency(Query(min_length=2, max_length=128, pattern=r"^\{"))

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(dependency)):
        return parsed

    (parameter,) = app.openapi()["paths"]["/filters"]["get"]["parameters"]
    constraints = {"minLength": 2, "maxLength": 128, "pattern": r"^\{"}
    assert {key: parameter["schema"].get(key) for key in constraints} == constraints

    app.openapi = with_filter_docs(app.openapi)
    (parameter,) = app.openapi()["paths"]["/filters"]["get"]["parameters"]
    assert constraints.keys().isdisjoint(parameter["content"]["application/json"]["schema"])


def test_filters_dependency_schema_examples():
    """
    Test Query schema examples replace the built-in named example.
    """
    app = FastAPI()
    dependency = filters_dependency(Query(examples=[{"age": {"$gt": 18}}]))

    @app.get("/filters")
    def get_filters(parsed: Filters = Depends(dependency)):
        return parsed

    app.openapi = with_filter_docs(app.openapi)
    (parameter,) = app.openapi()["paths"]["/filters"]["get"]["parameters"]
    content = parameter["content"]["application/json"]

    assert content["examples"] == {}
    assert content["schema"]["examples"] == [{"age": {"$gt": 18}}]
    assert content["schema"]["example"] == {"age": {"$gt": 18}}


def test_filters_dependency_preserves_supplied_query():
    """
    Test reusing a Query does not change its metadata or examples.
    """
    app = FastAPI()
    query = Query(
        openapi_examples={"adults": {"value": {"age": {"$gt": 18}}}},
        json_schema_extra={"x-supported-fields": ["age"]},
    )
    first_dependency = filters_dependency(query)
    second_dependency = filters_dependency(query)

    @app.get("/first")
    def first(parsed: Filters = Depends(first_dependency)):
        return parsed

    @app.get("/second")
    def second(parsed: Filters = Depends(second_dependency)):
        return parsed

    app.openapi = with_filter_docs(app.openapi)
    original = deepcopy(app.openapi())
    app.openapi_schema = None

    assert app.openapi() == original
    assert query.alias is None
    assert query.description is None
    assert query.openapi_examples == {"adults": {"value": {"age": {"$gt": 18}}}}
    assert query.json_schema_extra == {"x-supported-fields": ["age"]}


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
