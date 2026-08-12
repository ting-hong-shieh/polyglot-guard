from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PUBLIC_DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs").glob("*.md")),
]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


@pytest.mark.parametrize("document", PUBLIC_DOCUMENTS, ids=lambda path: path.name)
def test_local_document_links_exist(document: Path) -> None:
    failures: list[str] = []
    for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
        if target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        path_text, _separator, _fragment = target.partition("#")
        if not path_text:
            continue
        resolved = (document.parent / path_text).resolve()
        if not resolved.is_file():
            failures.append(target)
    assert failures == []
