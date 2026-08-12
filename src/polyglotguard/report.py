"""Render stable human-readable PolyglotGuard terminal output."""

from __future__ import annotations

from collections import defaultdict
from typing import TextIO

from polyglotguard.model import ChangeKind, RunResult, TranslationResult, TranslationStatus
from polyglotguard.terminal import escape_terminal_text

_CATEGORY_LABELS = {
    ChangeKind.ADDED: "Added",
    ChangeKind.MODIFIED: "Modified",
    ChangeKind.DELETED: "Deleted",
}


def render_report(result: RunResult, stdout: TextIO, stderr: TextIO) -> None:
    """Write successful result blocks to stdout and error blocks to stderr."""

    successful = [
        translation
        for translation in result.translations
        if translation.status is not TranslationStatus.ERROR
    ]
    if successful:
        stdout.write("PolyglotGuard\n\n")
        stdout.write(f"Source: {escape_terminal_text(result.source.as_posix())}\n")
        stdout.write(f"Current revision: {escape_terminal_text(result.current_revision)}\n")

    for translation in result.translations:
        if translation.status is TranslationStatus.ERROR:
            _render_error(result, translation, stderr)
        else:
            _render_success(translation, stdout)

    if successful:
        stale = sum(translation.status is TranslationStatus.STALE for translation in successful)
        total_review = sum(translation.review_count for translation in successful)
        stdout.write("\nSummary\n")
        stdout.write(f"  Checked translations: {len(successful)}\n")
        stdout.write(f"  Stale translations: {stale}\n")
        stdout.write(f"  Section reviews: {total_review}\n")


def render_fatal(error_code: str, message: str, hint: str | None, stderr: TextIO) -> None:
    stderr.write("PolyglotGuard\n\n")
    stderr.write(f"ERROR [{escape_terminal_text(error_code)}]\n")
    stderr.write(f"  {escape_terminal_text(message)}\n")
    if hint:
        stderr.write(f"  Hint: {escape_terminal_text(hint)}\n")


def _render_success(translation: TranslationResult, stream: TextIO) -> None:
    stream.write("\nTranslation\n")
    stream.write(f"  Path: {escape_terminal_text(translation.path.as_posix())}\n")
    if translation.locale is not None:
        stream.write(f"  Locale: {escape_terminal_text(translation.locale)}\n")
    stream.write(f"  Baseline: {escape_terminal_text(translation.resolved_baseline or '')}\n")
    if translation.status is TranslationStatus.UP_TO_DATE:
        stream.write("  Status: UP TO DATE\n")
        stream.write("  No reportable source changes were found after this baseline.\n")
        return

    stream.write("  Status: STALE\n")
    stream.write("  Source changes after this baseline require human translation review.\n")
    grouped: defaultdict[ChangeKind, list[str]] = defaultdict(list)
    for change in translation.changes:
        grouped[change.kind].append(change.path.display())
    for kind in (ChangeKind.ADDED, ChangeKind.MODIFIED, ChangeKind.DELETED):
        paths = grouped[kind]
        if not paths:
            continue
        stream.write(f"\n  {_CATEGORY_LABELS[kind]}\n")
        for path in paths:
            stream.write(f"    - {path}\n")
    count = translation.review_count
    noun = "section" if count == 1 else "sections"
    verb = "requires" if count == 1 else "require"
    stream.write(f"\n  {count} {noun} {verb} translation review.\n")


def _render_error(result: RunResult, translation: TranslationResult, stream: TextIO) -> None:
    error = translation.error
    stream.write("\nPolyglotGuard translation error\n\n")
    stream.write(f"Source: {escape_terminal_text(result.source.as_posix())}\n")
    stream.write(f"Translation: {escape_terminal_text(translation.path.as_posix())}\n")
    if translation.locale is not None:
        stream.write(f"Locale: {escape_terminal_text(translation.locale)}\n")
    stream.write(f"Configured baseline: {escape_terminal_text(translation.configured_baseline)}\n")
    if error is None:
        stream.write("Status: ERROR [UNKNOWN]\n  An unknown error occurred.\n")
        return
    stream.write(f"Status: ERROR [{escape_terminal_text(error.code)}]\n")
    stream.write(f"  {escape_terminal_text(error.message)}\n")
    if error.hint:
        stream.write(f"  Hint: {escape_terminal_text(error.hint)}\n")
