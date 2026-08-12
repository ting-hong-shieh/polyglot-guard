from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "PolyglotGuard Tests",
            "GIT_AUTHOR_EMAIL": "tests@polyglotguard.invalid",
            "GIT_COMMITTER_NAME": "PolyglotGuard Tests",
            "GIT_COMMITTER_EMAIL": "tests@polyglotguard.invalid",
        }
    )
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[Path]:
    git(tmp_path, "init", "-b", "main")
    yield tmp_path


@pytest.fixture
def commit_files(repository: Path):
    def commit_files(message: str, files: dict[str, str]) -> str:
        for relative, content in files.items():
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
        git(repository, "add", ".")
        git(repository, "commit", "-m", message)
        return git(repository, "rev-parse", "HEAD").stdout.strip()

    return commit_files
