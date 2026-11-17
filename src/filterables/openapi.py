import json
from typing import Any, Callable


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

                    content = definition["contentSchema"].copy()
                    examples = parameter.pop("examples", {})

                    if "default" in definition:
                        content["default"] = json.loads(definition["default"])

                    for example in examples.values():
                        if "value" in example:
                            example["value"] = json.loads(example["value"])
                            content.setdefault("example", example["value"])

                    parameter["content"] = {
                        "application/json": {
                            "schema": content,
                            "examples": examples,
                        },
                    }

                    del parameter["schema"]

        return schema

    return _openapi
