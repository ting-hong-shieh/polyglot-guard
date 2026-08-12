"""Make untrusted text safe and unambiguous in terminal reports."""

from __future__ import annotations

import json
import unicodedata


def escape_terminal_text(value: str) -> str:
    """Escape control and Unicode format characters without flattening readable text."""

    parts: list[str] = []
    for character in value:
        if unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            parts.append(json.dumps(character, ensure_ascii=True)[1:-1])
        else:
            parts.append(character)
    return "".join(parts)


def quote_terminal_text(value: str) -> str:
    """Return a JSON-style quoted label with terminal controls escaped."""

    return escape_terminal_text(json.dumps(value, ensure_ascii=False))
