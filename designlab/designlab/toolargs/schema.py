"""A small JSON Schema validator: the subset the two tools use.

Supported: type (object, string, integer, number, boolean, array),
properties, required, additionalProperties false, enum, pattern
(full match), minimum and maximum. Errors are returned as data, one per
problem, each naming the field, so the repair loop can hand them back.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_TYPES = {
    "object": dict, "string": str, "boolean": bool, "array": list,
}


@dataclass(frozen=True)
class SchemaError:
    field: str
    problem: str

    def as_dict(self) -> dict:
        return {"field": self.field, "problem": self.problem}


def _type_ok(value, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and \
            not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def validate(value, schema: dict, path: str = "$") -> list[SchemaError]:
    errs: list[SchemaError] = []
    t = schema.get("type")
    if t and not _type_ok(value, t):
        return [SchemaError(path, f"expected {t}")]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(SchemaError(path, "not one of the allowed values"))
    if "pattern" in schema and isinstance(value, str):
        if not re.fullmatch(schema["pattern"].strip("^$"), value):
            errs.append(SchemaError(path, "does not match the format"))
    if "minimum" in schema and _type_ok(value, "number"):
        if value < schema["minimum"]:
            errs.append(SchemaError(path, "below the minimum"))
    if "maximum" in schema and _type_ok(value, "number"):
        if value > schema["maximum"]:
            errs.append(SchemaError(path, "above the maximum"))
    if t == "object":
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errs.append(SchemaError(f"{path}.{name}", "missing"))
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in props:
                    errs.append(SchemaError(f"{path}.{name}",
                                            "not in the schema"))
        for name, sub in props.items():
            if name in value:
                errs.extend(validate(value[name], sub, f"{path}.{name}"))
    return errs
