"""Strict key=value overrides, deliberately a small subset of Hydra syntax."""
from __future__ import annotations

import dataclasses
import json
import types
from typing import Literal, Union, get_args, get_origin, get_type_hints


def convert(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        for choice in args:
            try:
                return convert(value, choice)
            except ValueError:
                pass
        raise ValueError(f"{value!r} does not match {annotation}")
    if origin is Literal:
        if any(type(value) is type(choice) and value == choice for choice in args):
            return value
    elif dataclasses.is_dataclass(annotation) and isinstance(value, dict):
        fields = get_type_hints(annotation)
        if set(value) - fields.keys():
            raise ValueError(f"Unknown fields: {set(value) - fields.keys()}")
        return annotation(**{key: convert(item, fields[key]) for key, item in value.items()})
    elif origin is list and isinstance(value, list):
        return [convert(item, args[0]) for item in value]
    elif origin is dict and isinstance(value, dict):
        return {convert(k, args[0]): convert(v, args[1]) for k, v in value.items()}
    elif annotation is float and type(value) in (int, float):
        return float(value)
    elif annotation in (str, int, bool, float, type(None)) and type(value) is annotation:
        return value
    raise ValueError(f"Expected {annotation}, got {value!r}")


def configuration(config_type, overrides: list[str]):
    values = dataclasses.asdict(config_type())
    seen = set()
    for override in overrides:
        key, separator, raw = override.partition("=")
        if not separator or not key or key in seen:
            raise ValueError(f"Expected unique field=value override: {override!r}")
        seen.add(key)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        current = values
        parts = key.split(".")
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                raise ValueError(f"Unknown configuration field: {key}")
            current = current[part]
        if parts[-1] not in current:
            raise ValueError(f"Unknown configuration field: {key}")
        current[parts[-1]] = value
    return convert(values, config_type)
