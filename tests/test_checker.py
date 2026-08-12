from __future__ import annotations

import os
from pathlib import PurePosixPath

from polyglotguard.checker import check_repository
from polyglotguard.git import GitRepository
from polyglotguard.model import (
    ProjectConfig,
    TranslationConfig,
    TranslationStatus,
)


def test_checks_two_translations_at_independent_baselines(repository, commit_files) -> None:
    first = commit_files(
        "baseline",
        {
            "README.md": "# Install\nold\n# Removed\ngone\n",
            "README.zh.md": "# 安裝\n",
            "README.ja.md": "# インストール\n",
        },
    )
    second = commit_files(
        "middle",
        {"README.md": "# Install\nnew\n# Added\nnew\n"},
    )
    head = commit_files("head", {"notes.txt": "no source change\n"})
    config = ProjectConfig(
        source=PurePosixPath("README.md"),
        translations=(
            TranslationConfig(PurePosixPath("README.zh.md"), first, "zh"),
            TranslationConfig(PurePosixPath("README.ja.md"), second, "ja"),
            TranslationConfig(PurePosixPath("missing.md"), first, None),
        ),
    )

    result = check_repository(GitRepository(root=repository), config)

    assert result.current_revision == head
    assert result.exit_code == 2
    assert [item.status for item in result.translations] == [
        TranslationStatus.STALE,
        TranslationStatus.UP_TO_DATE,
        TranslationStatus.ERROR,
    ]
    changes = [
        (change.kind.value, change.path.display()) for change in result.translations[0].changes
    ]
    assert changes == [
        ("added", '"Added"'),
        ("modified", '"Install"'),
        ("deleted", '"Removed"'),
    ]


def test_bootstrap_at_head_is_up_to_date(repository, commit_files) -> None:
    head = commit_files(
        "bootstrap",
        {"README.md": "# Source\n", "README.zh.md": "# 翻譯\n"},
    )
    config = ProjectConfig(
        source=PurePosixPath("README.md"),
        translations=(TranslationConfig(PurePosixPath("README.zh.md"), head, "zh"),),
    )
    result = check_repository(GitRepository(root=repository), config)
    assert result.exit_code == 0
    assert result.translations[0].status is TranslationStatus.UP_TO_DATE


def test_rejects_duplicate_translations_that_are_the_same_physical_file(
    repository, commit_files
) -> None:
    head = commit_files(
        "source",
        {"README.md": "# Source\n", "translation.md": "# Translation\n"},
    )
    os.link(repository / "translation.md", repository / "translation.alias.md")
    config = ProjectConfig(
        source=PurePosixPath("README.md"),
        translations=(
            TranslationConfig(PurePosixPath("translation.md"), head, "one"),
            TranslationConfig(PurePosixPath("translation.alias.md"), head, "alias"),
        ),
    )

    result = check_repository(GitRepository(root=repository), config)
    assert result.exit_code == 2
    assert result.translations[0].status is TranslationStatus.UP_TO_DATE
    assert result.translations[1].status is TranslationStatus.ERROR
    assert result.translations[1].error is not None
    assert result.translations[1].error.code == "CONFIG_MAPPING"


def test_dirty_source_symlink_does_not_change_result(repository, commit_files) -> None:
    head = commit_files(
        "source",
        {"README.md": "# Source\n", "translation.md": "# Translation\n"},
    )
    (repository / "README.md").unlink()
    (repository / "README.md").symlink_to("translation.md")
    config = ProjectConfig(
        source=PurePosixPath("README.md"),
        translations=(TranslationConfig(PurePosixPath("translation.md"), head, "one"),),
    )

    result = check_repository(GitRepository(root=repository), config)
    assert result.exit_code == 0
    assert result.translations[0].status is TranslationStatus.UP_TO_DATE
