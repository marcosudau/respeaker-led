from __future__ import annotations

import re
from typing import Any


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d+|\d+\.\d*|\.\d+)$")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    text = _strip_quotes(value.strip())
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if _INT_RE.match(text):
        try:
            return int(text)
        except ValueError:
            pass
    if _FLOAT_RE.match(text):
        try:
            return float(text)
        except ValueError:
            pass
    return text


def parse_simple_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml
    except Exception:
        return _parse_simple_yaml_fallback(text)

    payload = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise ValueError("YAML document must contain a top-level mapping")
    return payload


def _parse_simple_yaml_fallback(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    active_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.lstrip()
        if stripped.startswith("- "):
            if active_list_key is None:
                raise ValueError(f"List item without active key in line: {raw_line}")
            current = data.setdefault(active_list_key, [])
            if not isinstance(current, list):
                raise ValueError(f"Key '{active_list_key}' is not a list")
            current.append(_parse_scalar(stripped[2:]))
            continue

        key, separator, raw_value = line.partition(":")
        if not separator:
            raise ValueError(f"Invalid yaml line: {raw_line}")

        key = key.strip()
        value = raw_value.strip()
        if not key:
            raise ValueError(f"Missing key in yaml line: {raw_line}")

        if value == "":
            data[key] = []
            active_list_key = key
            continue

        data[key] = _parse_scalar(value)
        active_list_key = None

    return data
