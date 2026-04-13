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


def _strip_comments(value: str) -> str:
    result: list[str] = []
    in_single = False
    in_double = False
    for char in value:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result).rstrip()


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
    prepared: list[tuple[int, str, str]] = []
    for raw_line in text.splitlines():
        line = _strip_comments(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        prepared.append((indent, line.lstrip(), raw_line))

    if not prepared:
        return {}
    if prepared[0][0] != 0:
        raise ValueError("YAML document must start at indentation level 0")

    def _next_block_kind(start_index: int, parent_indent: int) -> str | None:
        if start_index >= len(prepared):
            return None
        next_indent, next_text, _ = prepared[start_index]
        if next_indent <= parent_indent:
            return None
        return "list" if next_text.startswith("- ") else "mapping"

    def _parse_mapping(start_index: int, indent: int) -> tuple[dict[str, Any], int]:
        data: dict[str, Any] = {}
        index = start_index
        while index < len(prepared):
            current_indent, current_text, raw_line = prepared[index]
            if current_indent < indent:
                break
            if current_indent != indent or current_text.startswith("- "):
                raise ValueError(f"Invalid mapping entry in line: {raw_line}")

            key, separator, raw_value = current_text.partition(":")
            if not separator:
                raise ValueError(f"Invalid yaml line: {raw_line}")
            key = key.strip()
            value = raw_value.strip()
            if not key:
                raise ValueError(f"Missing key in yaml line: {raw_line}")

            index += 1
            if value:
                data[key] = _parse_scalar(value)
                continue

            block_kind = _next_block_kind(index, indent)
            if block_kind is None:
                data[key] = {}
                continue
            if block_kind == "list":
                data[key], index = _parse_list(index, indent + 2)
                continue
            data[key], index = _parse_mapping(index, indent + 2)
        return data, index

    def _parse_list(start_index: int, indent: int) -> tuple[list[Any], int]:
        items: list[Any] = []
        index = start_index
        while index < len(prepared):
            current_indent, current_text, raw_line = prepared[index]
            if current_indent < indent:
                break
            if current_indent != indent or not current_text.startswith("- "):
                raise ValueError(f"Invalid list entry in line: {raw_line}")

            item_value = current_text[2:].strip()
            index += 1
            if item_value:
                items.append(_parse_scalar(item_value))
                continue

            block_kind = _next_block_kind(index, indent)
            if block_kind is None:
                items.append(None)
                continue
            if block_kind == "list":
                nested_items, index = _parse_list(index, indent + 2)
                items.append(nested_items)
                continue
            nested_mapping, index = _parse_mapping(index, indent + 2)
            items.append(nested_mapping)
        return items, index

    parsed, next_index = _parse_mapping(0, 0)
    if next_index != len(prepared):
        _, _, raw_line = prepared[next_index]
        raise ValueError(f"Unexpected yaml content starting at line: {raw_line}")
    return parsed
