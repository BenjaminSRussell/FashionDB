"""Validate fashion rules against standardization/schema.json (required + additionalProperties)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.json")


def load_schema(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or SCHEMA_PATH).read_text(encoding="utf-8"))


def _type_ok(value: Any, expected: str | list | None) -> bool:
    if expected is None:
        return True
    if isinstance(expected, list):
        return any(_type_ok(value, t) for t in expected)
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    py = mapping.get(expected)
    if py is None:
        return True
    if expected == "number" and isinstance(value, bool):
        return False
    if expected == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, py)


def validate_against_schema(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Return a list of error strings (empty = valid). Supports a useful subset of draft-07."""
    errors: list[str] = []
    if "type" in schema and not _type_ok(instance, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
        return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum")

    if schema.get("type") == "object" and isinstance(instance, dict):
        required = schema.get("required") or []
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}: additional property {key!r} not allowed")
        for key, subschema in props.items():
            if key in instance:
                errors.extend(validate_against_schema(instance[key], subschema, f"{path}.{key}"))

    if schema.get("type") == "array" and isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array shorter than minItems={schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                errors.extend(validate_against_schema(item, item_schema, f"{path}[{i}]"))

    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errors.append(f"{path}: string shorter than minLength={schema['minLength']}")

    return errors


def validate_rule(rule: dict[str, Any], schema: dict[str, Any] | None = None) -> list[str]:
    return validate_against_schema(rule, schema or load_schema())
