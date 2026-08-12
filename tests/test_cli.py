from __future__ import annotations

import os
import subprocess
from io import StringIO
from pathlib import Path

from polyglotguard.cli import main


def write_config(repository: Path, baseline: str, *, extra: str = "") -> None:
    (repository / "polyglotguard.toml").write_text(
        f'''version = 1
source = "README.md"
[[translations]]
path = "README.zh.md"
locale = "zh-TW"
baseline = "{baseline}"
{extra}''',
        encoding="utf-8",
    )


def run_cli(repository: Path, monkeypatch, *arguments: str) -> tuple[int, str, str]:
    monkeypatch.chdir(repository)
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main(arguments, stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_cli_reports_up_to_date(repository: Path, commit_files, monkeypatch) -> None:
    head = commit_files(
        "initial",
        {"README.md": "# Source\n", "README.zh.md": "# 翻譯\n"},
    )
    write_config(repository, head)
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 0
    assert "Status: UP TO DATE" in stdout
    assert "No reportable source changes" in stdout
    assert stderr == ""


def test_cli_discovers_root_configuration_from_subdirectory(
    repository: Path, commit_files, monkeypatch
) -> None:
    head = commit_files(
        "initial",
        {"README.md": "# Source\n", "README.zh.md": "# 翻譯\n"},
    )
    write_config(repository, head)
    subdirectory = repository / "docs" / "nested"
    subdirectory.mkdir(parents=True)
    exit_code, stdout, stderr = run_cli(subdirectory, monkeypatch, "check")
    assert exit_code == 0
    assert "Source: README.md" in stdout
    assert stderr == ""


def test_cli_reports_stale_and_exit_one(repository: Path, commit_files, monkeypatch) -> None:
    baseline = commit_files(
        "baseline",
        {
            "README.md": "# Install\nold\n# Removed\ngone\n",
            "README.zh.md": "# 安裝\n",
        },
    )
    commit_files(
        "current",
        {"README.md": "# Install\nnew\n# Added\nnew\n"},
    )
    write_config(repository, baseline)
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 1
    assert "Status: STALE" in stdout
    assert 'Added\n    - "Added"' in stdout
    assert 'Modified\n    - "Install"' in stdout
    assert 'Deleted\n    - "Removed"' in stdout
    assert "3 sections require translation review" in stdout
    assert stderr == ""


def test_cli_uses_singular_review_grammar(repository: Path, commit_files, monkeypatch) -> None:
    baseline = commit_files(
        "baseline",
        {"README.md": "# Install\nold\n", "README.zh.md": "# 安裝\n"},
    )
    commit_files("current", {"README.md": "# Install\nnew\n"})
    write_config(repository, baseline)
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 1
    assert "1 section requires translation review" in stdout
    assert stderr == ""


def test_cli_error_has_actionable_hint(repository: Path, commit_files, monkeypatch) -> None:
    head = commit_files(
        "initial",
        {"README.md": "# Source\n", "README.zh.md": "# 翻譯\n"},
    )
    write_config(repository, "f" * len(head))
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 2
    assert "Stale translations: 0" not in stdout
    assert "ERROR [BASELINE_UNAVAILABLE]" in stderr
    assert "does not fetch or deepen" in stderr


def test_cli_mixed_stale_and_error_uses_both_streams_and_exit_two(
    repository: Path, commit_files, monkeypatch
) -> None:
    baseline = commit_files(
        "baseline",
        {"README.md": "# Install\nold\n", "README.zh.md": "# 安裝\n"},
    )
    commit_files("current", {"README.md": "# Install\nnew\n"})
    (repository / "polyglotguard.toml").write_text(
        f'''version = 1
source = "README.md"
[[translations]]
path = "README.zh.md"
baseline = "{baseline}"
[[translations]]
path = "missing.md"
baseline = "{baseline}"
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 2
    assert "Path: README.zh.md" in stdout
    assert "Status: STALE" in stdout
    assert 'Modified\n    - "Install"' in stdout
    assert "Translation: missing.md" in stderr
    assert "Status: ERROR [FILE_MISSING]" in stderr


def test_cli_fatal_config_error_uses_exit_two(repository: Path, commit_files, monkeypatch) -> None:
    commit_files("initial", {"README.md": "# Source\n"})
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 2
    assert stdout == ""
    assert "ERROR [CONFIG_NOT_FOUND]" in stderr


def test_cli_version_and_help_do_not_need_repository(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    stdout = StringIO()
    assert main(["--version"], stdout=stdout, stderr=StringIO()) == 0
    assert stdout.getvalue() == "polyglotguard 0.1.0\n"

    help_output = StringIO()
    assert main([], stdout=help_output, stderr=StringIO()) == 0
    assert "{check}" in help_output.getvalue()


def test_cli_does_not_change_repository_state(repository: Path, commit_files, monkeypatch) -> None:
    head = commit_files(
        "initial",
        {"README.md": "# Source\n", "README.zh.md": "# 翻譯\n"},
    )
    write_config(repository, head)
    tracked_paths = [repository / "README.md", repository / "README.zh.md"]
    config_path = repository / "polyglotguard.toml"
    trace_path = repository / "unexpected-git-trace.log"
    before_content = {path: path.read_bytes() for path in [*tracked_paths, config_path]}
    before_mtime = {path: os.stat(path).st_mtime_ns for path in [*tracked_paths, config_path]}
    before_status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v2", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    monkeypatch.setenv("GIT_TRACE", str(trace_path))
    exit_code, _stdout, _stderr = run_cli(repository, monkeypatch, "check")
    assert not trace_path.exists()
    monkeypatch.delenv("GIT_TRACE")
    after_content = {path: path.read_bytes() for path in [*tracked_paths, config_path]}
    after_mtime = {path: os.stat(path).st_mtime_ns for path in [*tracked_paths, config_path]}
    after_status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v2", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert exit_code == 0
    assert before_content == after_content
    assert before_mtime == after_mtime
    assert before_status == after_status


def test_cli_converts_unexpected_failure_to_runtime_error(monkeypatch) -> None:
    def fail_discovery(_start: Path):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("polyglotguard.cli.GitRepository.discover", fail_discovery)
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main(["check"], stdout=stdout, stderr=stderr)
    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "ERROR [RUNTIME_ERROR]" in stderr.getvalue()
    assert "simulated failure" in stderr.getvalue()


def test_cli_escapes_format_controls_in_config_error(
    repository: Path, commit_files, monkeypatch
) -> None:
    commit_files("initial", {"README.md": "# Source\n"})
    (repository / "polyglotguard.toml").write_text(
        "version = 1\nsource = 'docs/\u202eSOURCE.md'\ntranslations = []\n",
        encoding="utf-8",
    )
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 2
    assert stdout == ""
    assert "\u202e" not in stderr
    assert "\\u202e" in stderr


def test_cli_escapes_unicode_line_separator_in_config_error(
    repository: Path, commit_files, monkeypatch
) -> None:
    commit_files("initial", {"README.md": "# Source\n"})
    (repository / "polyglotguard.toml").write_text(
        "version = 1\nsource = 'docs/safe\u2028spoof.txt'\ntranslations = []\n",
        encoding="utf-8",
    )
    exit_code, stdout, stderr = run_cli(repository, monkeypatch, "check")
    assert exit_code == 2
    assert stdout == ""
    assert "\u2028" not in stderr
    assert "\\u2028" in stderr
