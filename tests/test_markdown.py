from __future__ import annotations

import pytest

from polyglotguard.errors import PolyglotGuardError
from polyglotguard.markdown import parse_markdown


def sections(source: str) -> list[tuple[int, str, str]]:
    return [
        (section.level, section.path.display(), section.body)
        for section in parse_markdown(source).sections
    ]


def test_parses_preamble_atx_setext_fences_and_skipped_levels() -> None:
    source = (
        "Preamble\r\n\r\n"
        "# Parent\r\n"
        "direct  \r\n\r\n"
        "### Child\r\n"
        "child\r\n\r\n"
        "~~~python\r\n"
        "# not a heading\r\n"
        "~~~\r\n\r\n"
        "Setext child\r\n"
        "------------\r\n"
        "setext body\r\n"
    )

    assert sections(source) == [
        (0, "(document preamble)", "Preamble"),
        (1, '"Parent"', "direct  "),
        (3, '"Parent" > "Child"', "child\n\n~~~python\n# not a heading\n~~~"),
        (2, '"Parent" > "Setext child"', "setext body"),
    ]


def test_heading_text_uses_plain_inline_content_and_normalization() -> None:
    source = (
        "# **Cafe\u0301**   [`code`](https://example.com) ![*image* `alt` &amp;](image.png) &amp;\n"
    )
    assert sections(source)[1][:2] == (1, '"Café code image alt & &"')


def test_duplicate_headings_are_scoped_to_siblings() -> None:
    source = """# A
## Child
## Child
# A
## Child
"""
    assert [path for _level, path, _body in sections(source)] == [
        "(document preamble)",
        '"A"',
        '"A" > "Child"',
        '"A" > "Child" [2]',
        '"A" [2]',
        '"A" [2] > "Child"',
    ]


def test_unclosed_fence_consumes_heading_like_lines() -> None:
    source = "# Before\n```\n## not a heading\n"
    assert [path for _level, path, _body in sections(source)] == [
        "(document preamble)",
        '"Before"',
    ]


def test_html_heading_is_not_a_commonmark_heading() -> None:
    source = "<h1>HTML only</h1>\n\n# Markdown\n"
    assert sections(source) == [
        (0, "(document preamble)", "<h1>HTML only</h1>"),
        (1, '"Markdown"', ""),
    ]


def test_display_distinguishes_literal_delimiters_and_duplicate_suffixes() -> None:
    source = "# A > B\n# A\n## B\n# Foo [2]\n# Foo\n# Foo\n"
    assert [path for _level, path, _body in sections(source)] == [
        "(document preamble)",
        '"A > B"',
        '"A"',
        '"A" > "B"',
        '"Foo [2]"',
        '"Foo"',
        '"Foo" [2]',
    ]


def test_display_escapes_terminal_controls_and_bidi_formatting() -> None:
    source = "# safe\u009bcontrol \u202espoof\n"
    display = sections(source)[1][1]
    assert "\u009b" not in display
    assert "\u202e" not in display
    assert "\\u009b" in display
    assert "\\u202e" in display


def test_rejects_nul_character() -> None:
    with pytest.raises(PolyglotGuardError) as captured:
        parse_markdown("# Before\n\0\n")
    assert captured.value.detail.code == "MARKDOWN_NUL"
