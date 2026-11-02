"""A reader for the small YAML subset that map.yaml uses.

Supported: comments, nested mappings by indentation, lists of scalars
or mappings ("- key: value"), flow lists ("[a, b]"), flow mappings
of scalars ("{a: 1, b: x}") and quoted or
plain scalars. Integers become int; everything else stays a string,
dates included, so a date is never silently turned into something else.
Anything outside the subset raises YamlishError with the line number.
"""
from __future__ import annotations


class YamlishError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (not out or out[-1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def scalar(text: str):
    text = text.strip()
    if text == "":
        return ""
    if text[0] in "\"'" and text[-1] == text[0] and len(text) >= 2:
        return text[1:-1]
    if text.startswith("{") and text.endswith("}"):
        out = {}
        for part in text[1:-1].split(","):
            if not part.strip():
                continue
            key, sep, val = part.partition(":")
            if not sep:
                raise YamlishError(f"flow mapping needs 'k: v': {part}")
            out[key.strip()] = scalar(val)
        return out
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [scalar(x) for x in inner.split(",")] if inner else []
    if text.lstrip("-").isdigit():
        return int(text)
    if text in ("null", "~"):
        return None
    if text in ("true", "false"):
        return text == "true"
    return text


def _split_key(text: str, lineno: int):
    if ":" not in text:
        raise YamlishError(f"line {lineno}: expected 'key: value'")
    if text[0] in "\"'":
        raise YamlishError(f"line {lineno}: quoted keys not supported")
    key, _, rest = text.partition(":")
    if rest and not rest.startswith(" "):
        raise YamlishError(f"line {lineno}: need a space after ':'")
    return key.strip(), rest.strip()


def loads(text: str):
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlishError(f"line {n}: tabs in indentation")
        line = _strip_comment(raw)
        if line.strip():
            lines.append((len(line) - len(line.lstrip()), line.strip(), n))
    value, pos = _block(lines, 0, 0)
    if pos != len(lines):
        raise YamlishError(f"line {lines[pos][2]}: unexpected indent")
    return value


def _block(lines, pos, indent):
    if pos >= len(lines):
        return None, pos
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        return _list(lines, pos, indent)
    return _map(lines, pos, indent)


def _map(lines, pos, indent, first=None):
    out = {}
    while pos < len(lines):
        ind, text, n = lines[pos]
        if first is not None:
            ind, text, n = first
            first = None
        elif ind < indent:
            break
        elif ind > indent:
            raise YamlishError(f"line {n}: unexpected indent")
        elif text.startswith("- "):
            break
        key, rest = _split_key(text, n)
        if key in out:
            raise YamlishError(f"line {n}: duplicate key '{key}'")
        pos += 1
        if rest:
            out[key] = scalar(rest)
        elif pos < len(lines) and lines[pos][0] > ind:
            out[key], pos = _block(lines, pos, lines[pos][0])
        elif (pos < len(lines) and lines[pos][0] == ind
              and lines[pos][1].startswith("- ")):
            out[key], pos = _list(lines, pos, ind)
        else:
            out[key] = None
    return out, pos


def _list(lines, pos, indent):
    out = []
    while pos < len(lines):
        ind, text, n = lines[pos]
        if ind != indent or not text.startswith("-"):
            if ind > indent:
                raise YamlishError(f"line {n}: unexpected indent")
            break
        body = text[1:].strip()
        child = indent + 2
        if not body:
            pos += 1
            item, pos = _block(lines, pos, lines[pos][0])
        elif ":" in body and body[0] not in "\"'[":
            item, pos = _map(lines, pos, child, first=(child, body, n))
        else:
            item, pos = scalar(body), pos + 1
        out.append(item)
    return out, pos
