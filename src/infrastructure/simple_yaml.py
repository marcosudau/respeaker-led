from __future__ import annotations


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_scalar(value: str):
    value = _strip_quotes(value.strip())
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    return value


def parse_simple_yaml(text: str) -> dict:
    data: dict[str, object] = {}
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
