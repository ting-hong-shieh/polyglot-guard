"""Load and validate the repository-local PolyglotGuard configuration."""

from __future__ import annotations

import re
import tomllib
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from polyglotguard.errors import PolyglotGuardError
from polyglotguard.model import ProjectConfig, TranslationConfig

DEFAULT_CONFIG_NAME = "polyglotguard.toml"

_ROOT_KEYS = frozenset({"version", "source", "translations"})
_TRANSLATION_KEYS = frozenset({"path", "baseline", "locale"})
_FULL_OBJECT_ID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})


def load_config(path: Path) -> ProjectConfig:
    """Read *path* as strict v0.1 TOML configuration."""

    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except FileNotFoundError as exc:
        raise PolyglotGuardError(
            "CONFIG_NOT_FOUND",
            f"Configuration file not found: {path}",
            hint=f"Create {DEFAULT_CONFIG_NAME} at the repository root.",
        ) from exc
    except PermissionError as exc:
        raise PolyglotGuardError(
            "CONFIG_UNREADABLE",
            f"Configuration file is not readable: {path}",
        ) from exc
    except UnicodeDecodeError as exc:
        raise PolyglotGuardError(
            "CONFIG_TOML",
            f"Configuration is not valid UTF-8 TOML: {path}",
        ) from exc
    except OSError as exc:
        raise PolyglotGuardError(
            "CONFIG_UNREADABLE",
            f"Configuration file could not be read: {path}: {exc}",
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise PolyglotGuardError(
            "CONFIG_TOML",
            f"Configuration is not valid TOML: {exc}",
        ) from exc

    _reject_unknown_keys(raw, _ROOT_KEYS, "configuration")

    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise PolyglotGuardError(
            "CONFIG_VERSION",
            "Configuration field 'version' must be the integer 1.",
        )

    source = _parse_markdown_path(raw.get("source"), "source")
    translations_raw = raw.get("translations")
    if not isinstance(translations_raw, list) or not translations_raw:
        raise PolyglotGuardError(
            "CONFIG_TRANSLATIONS",
            "Configuration field 'translations' must contain at least one table.",
        )

    translations: list[TranslationConfig] = []
    seen_paths: set[PurePosixPath] = set()
    for index, item in enumerate(translations_raw, start=1):
        context = f"translations[{index}]"
        if not isinstance(item, dict):
            raise PolyglotGuardError(
                "CONFIG_TRANSLATION",
                f"{context} must be a TOML table.",
            )
        _reject_unknown_keys(item, _TRANSLATION_KEYS, context)

        translation_path = _parse_markdown_path(item.get("path"), f"{context}.path")
        if translation_path == source:
            raise PolyglotGuardError(
                "CONFIG_MAPPING",
                f"{context}.path must not be the same as the source path.",
            )
        if translation_path in seen_paths:
            raise PolyglotGuardError(
                "CONFIG_MAPPING",
                f"Translation path is configured more than once: {translation_path}",
            )
        seen_paths.add(translation_path)

        baseline = item.get("baseline")
        if not isinstance(baseline, str) or _FULL_OBJECT_ID.fullmatch(baseline) is None:
            raise PolyglotGuardError(
                "CONFIG_BASELINE",
                f"{context}.baseline must be a full 40- or 64-character Git commit ID.",
                hint="Record a verified immutable commit; branch and tag names are not accepted.",
            )

        locale = item.get("locale")
        if locale is not None and (
            not isinstance(locale, str)
            or not locale
            or locale != locale.strip()
            or any(unicodedata.category(character) in {"Cc", "Cf"} for character in locale)
        ):
            raise PolyglotGuardError(
                "CONFIG_LOCALE",
                (
                    f"{context}.locale must be a non-empty string without outer whitespace "
                    "or control and format characters."
                ),
            )

        translations.append(
            TranslationConfig(
                path=translation_path,
                baseline=baseline.lower(),
                locale=locale,
            )
        )

    return ProjectConfig(source=source, translations=tuple(translations))


def _reject_unknown_keys(table: dict[str, Any], allowed: frozenset[str], context: str) -> None:
    unknown = sorted(set(table) - allowed)
    if not unknown:
        return
    rendered = ", ".join(repr(key) for key in unknown)
    raise PolyglotGuardError(
        "CONFIG_UNKNOWN_FIELD",
        f"Unknown field in {context}: {rendered}",
        hint="Remove the field or check its spelling.",
    )


def _parse_markdown_path(value: object, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PolyglotGuardError(
            "CONFIG_PATH",
            f"Configuration field '{field}' must be a non-empty repository-relative path.",
        )
    if (
        any(unicodedata.category(character) in {"Cc", "Cf"} for character in value)
        or "\\" in value
        or ":" in value
        or value.startswith("/")
    ):
        raise PolyglotGuardError(
            "CONFIG_PATH",
            f"Configuration field '{field}' is not a portable repository-relative path: {value}",
        )

    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PolyglotGuardError(
            "CONFIG_PATH",
            f"Configuration field '{field}' contains an empty, '.' or '..' path component: {value}",
        )

    path = PurePosixPath(value)
    if path.suffix.lower() not in _MARKDOWN_SUFFIXES:
        raise PolyglotGuardError(
            "CONFIG_PATH",
            f"Configuration field '{field}' must identify a .md or .markdown file: {value}",
        )
    return path
