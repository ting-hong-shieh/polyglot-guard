"""Errors that can be shown to a PolyglotGuard user."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    """A stable internal error description for terminal rendering."""

    code: str
    message: str
    hint: str | None = None


class PolyglotGuardError(Exception):
    """Base class for expected configuration, repository, and parsing failures."""

    def __init__(self, code: str, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.detail = ErrorDetail(code=code, message=message, hint=hint)
