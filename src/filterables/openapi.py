import json
from collections.abc import Callable, Mapping
from typing import Any


def with_filter_docs(openapi: Callable[[], dict[str, Any]]) -> Callable[[], dict[str, Any]]:
    """
    Show JSON filter parameters using their schema in OpenAPI documentation.
    """

    def _openapi() -> dict[str, Any]:
        schema = openapi()

        for path in schema.get("paths", {}).values():
            for operation in path.values():
                if not isinstance(operation, dict):
                    continue

                for parameter in operation.get("parameters", []):
                    definition = parameter.get("schema", {})
                    if not definition.get("x-filterables"):
                        continue

                    content = dict(definition)
                    examples = parameter.pop("examples", {})

                    _build_content(content, definition)
                    _decode_examples(content, examples)

                    parameter["content"] = {
                        "application/json": {
                            "schema": content,
                            "examples": examples,
                        },
                    }

                    del parameter["schema"]

        return schema

    return _openapi


def _build_content(content: dict[str, Any], definition: Mapping[str, Any]) -> None:
    """
    Update the content schema in place to describe the decoded JSON value.
    """
    removed = (
        "type",
        "contentMediaType",
        "contentSchema",
        "x-filterables",
        "default",
        "minLength",
        "maxLength",
        "pattern",
    )

    for key in removed:
        content.pop(key, None)

    content.update(definition["contentSchema"])

    if "default" in definition:
        content["default"] = json.loads(definition["default"])


def _decode_examples(content: dict[str, Any], examples: Mapping[str, dict[str, Any]]) -> None:
    """
    Decode examples in place and supply a fallback example for Swagger UI.
    """
    if existing := content.get("examples"):
        content["examples"] = [json.loads(example) for example in existing]
        content.setdefault("example", content["examples"][0])

    for example in examples.values():
        if "value" in example:
            example["value"] = json.loads(example["value"])
            content.setdefault("example", example["value"])
