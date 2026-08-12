"""Parse source Markdown into the v0.1 hierarchical section model."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from polyglotguard.errors import PolyglotGuardError
from polyglotguard.model import HeadingComponent, Section, SectionPath, SectionTree

_WHITESPACE = re.compile(r"\s+")
_COMMONMARK = MarkdownIt("commonmark", {"html": True})


@dataclass(frozen=True, slots=True)
class _Heading:
    level: int
    label: str
    start_line: int
    body_start_line: int


def parse_markdown(source: str) -> SectionTree:
    """Parse CommonMark ATX and Setext headings into ordered sections."""

    if "\0" in source:
        raise PolyglotGuardError(
            "MARKDOWN_NUL",
            "Source Markdown contains a NUL character and cannot be parsed safely.",
        )

    normalized_source = source.replace("\r\n", "\n").replace("\r", "\n")
    tokens = _COMMONMARK.parse(normalized_source)
    headings = _collect_headings(tokens)

    lines = normalized_source.split("\n")
    first_heading_line = headings[0].start_line if headings else len(lines)
    sections: list[Section] = [
        Section(
            path=SectionPath.preamble(),
            level=0,
            body=_normalize_body(lines[:first_heading_line]),
            order=0,
        )
    ]

    stack: list[tuple[int, SectionPath]] = []
    occurrences: defaultdict[tuple[SectionPath, str], int] = defaultdict(int)
    for index, heading in enumerate(headings):
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        parent_path = stack[-1][1] if stack else SectionPath.preamble()
        occurrence_key = (parent_path, heading.label)
        occurrences[occurrence_key] += 1
        component = HeadingComponent(
            label=heading.label,
            occurrence=occurrences[occurrence_key],
        )
        path = SectionPath(components=(*parent_path.components, component))
        next_heading_line = (
            headings[index + 1].start_line if index + 1 < len(headings) else len(lines)
        )
        sections.append(
            Section(
                path=path,
                level=heading.level,
                body=_normalize_body(lines[heading.body_start_line : next_heading_line]),
                order=index + 1,
            )
        )
        stack.append((heading.level, path))

    return SectionTree(sections=tuple(sections))


def _collect_headings(tokens: list[Token]) -> list[_Heading]:
    headings: list[_Heading] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        inline = tokens[index + 1]
        headings.append(
            _Heading(
                level=int(token.tag[1:]),
                label=_normalize_heading(_inline_text(inline.children or [])),
                start_line=token.map[0],
                body_start_line=token.map[1],
            )
        )
    return headings


def _inline_text(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.type in {"text", "text_special", "code_inline"}:
            parts.append(token.content)
        elif token.type == "image":
            parts.append(_inline_text(token.children or []))
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
        elif token.type == "html_inline":
            # CommonMark treats raw inline HTML as formatting, not heading text.
            continue
        elif token.children:
            parts.append(_inline_text(token.children))
    return "".join(parts)


def _normalize_heading(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return _WHITESPACE.sub(" ", normalized).strip()


def _normalize_body(lines: list[str]) -> str:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip(" \t"):
        start += 1
    while end > start and not lines[end - 1].strip(" \t"):
        end -= 1
    return "\n".join(lines[start:end])
