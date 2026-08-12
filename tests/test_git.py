from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

import pytest
from conftest import git

from polyglotguard.errors import PolyglotGuardError
from polyglotguard.git import GitRepository, _run_process, resolve_config_path


def test_discovers_repository_from_subdirectory(repository: Path, commit_files) -> None:
    commit_files("initial", {"README.md": "# Source\n"})
    child = repository / "a" / "b"
    child.mkdir(parents=True)
    assert GitRepository.discover(child).root == repository.resolve()


def test_discovery_ignores_inherited_git_repository_context(
    repository: Path, tmp_path: Path, monkeypatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-b", "main")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    assert GitRepository.discover(repository).root == repository.resolve()


def test_discovery_preserves_trailing_space_in_root(tmp_path: Path) -> None:
    repository = tmp_path / "repository "
    repository.mkdir()
    git(repository, "init", "-b", "main")
    assert GitRepository.discover(repository).root == repository.resolve()


def test_reads_committed_utf8_markdown(repository: Path, commit_files) -> None:
    revision = commit_files("initial", {"README.md": "\ufeff# Café\n"})
    repo = GitRepository(root=repository)
    assert repo.read_markdown(revision, PurePosixPath("README.md"), role="source") == "# Café\n"


def test_git_paths_are_treated_literally(repository: Path, commit_files) -> None:
    revision = commit_files("literal path", {"other.md": "# Other\n"})
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).read_markdown(revision, PurePosixPath("*.md"), role="source")
    assert captured.value.detail.code == "FILE_MISSING"


def test_current_revision_ignores_dirty_worktree(repository: Path, commit_files) -> None:
    revision = commit_files("initial", {"README.md": "# Committed\n"})
    (repository / "README.md").write_text("# Dirty\n", encoding="utf-8")
    repo = GitRepository(root=repository)
    assert repo.current_revision() == revision
    content = repo.read_markdown(revision, PurePosixPath("README.md"), role="source")
    assert content == "# Committed\n"


def test_detached_head_is_a_valid_current_revision(repository: Path, commit_files) -> None:
    revision = commit_files("initial", {"README.md": "# Source\n"})
    git(repository, "switch", "--detach", revision)
    assert GitRepository(root=repository).current_revision() == revision


def test_unborn_head_is_actionable(repository: Path) -> None:
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).current_revision()
    assert captured.value.detail.code == "GIT_REVISION"


def test_reads_exact_object_despite_local_replace_ref(repository: Path, commit_files) -> None:
    baseline = commit_files("baseline", {"README.md": "# Baseline\n"})
    replacement = commit_files("replacement", {"README.md": "# Replacement\n"})
    git(repository, "replace", baseline, replacement)

    content = GitRepository(root=repository).read_markdown(
        baseline, PurePosixPath("README.md"), role="source"
    )
    assert content == "# Baseline\n"


def test_ancestry_ignores_legacy_grafts(repository: Path, commit_files) -> None:
    unrelated = commit_files("unrelated", {"README.md": "# Unrelated\n"})
    git(repository, "switch", "--orphan", "current")
    git(repository, "rm", "-rf", "--ignore-unmatch", ".")
    current = commit_files("current", {"README.md": "# Current\n"})
    grafts = repository / ".git" / "info" / "grafts"
    grafts.write_text(f"{current} {unrelated}\n", encoding="ascii")

    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).resolve_baseline(unrelated, current_revision=current)
    assert captured.value.detail.code == "BASELINE_NOT_ANCESTOR"


def test_resolves_ancestor_and_rejects_nonancestor(repository: Path, commit_files) -> None:
    baseline = commit_files("baseline", {"README.md": "# A\n"})
    head = commit_files("head", {"README.md": "# B\n"})
    repo = GitRepository(root=repository)
    assert repo.resolve_baseline(baseline, current_revision=head) == baseline

    git(repository, "switch", "--orphan", "unrelated")
    git(repository, "rm", "-rf", "--ignore-unmatch", ".")
    unrelated = commit_files("unrelated", {"README.md": "# C\n"})
    with pytest.raises(PolyglotGuardError) as captured:
        repo.resolve_baseline(unrelated, current_revision=head)
    assert captured.value.detail.code == "BASELINE_NOT_ANCESTOR"


def test_reports_unavailable_baseline(repository: Path, commit_files) -> None:
    head = commit_files("head", {"README.md": "# A\n"})
    missing = "f" * len(head)
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).resolve_baseline(missing, current_revision=head)
    assert captured.value.detail.code == "BASELINE_UNAVAILABLE"
    assert "does not fetch" in (captured.value.detail.hint or "")


def test_missing_promised_baseline_blob_is_actionable(repository: Path, commit_files) -> None:
    baseline = commit_files("baseline", {"README.md": "# Baseline\n"})
    blob = git(repository, "rev-parse", f"{baseline}:README.md").stdout.strip()
    git(repository, "config", "extensions.partialClone", "origin")
    git(repository, "config", "remote.origin.promisor", "true")
    git(repository, "config", "remote.origin.partialclonefilter", "blob:none")
    git(repository, "config", "remote.origin.url", str(repository / "missing-remote"))
    object_path = repository / ".git" / "objects" / blob[:2] / blob[2:]
    object_path.unlink()

    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).read_markdown(
            baseline, PurePosixPath("README.md"), role="baseline source"
        )
    assert captured.value.detail.code == "BASELINE_UNAVAILABLE"
    assert baseline in captured.value.detail.message
    assert "does not fetch" in (captured.value.detail.hint or "")
    assert not object_path.exists()


def test_rejects_non_commit_object(repository: Path, commit_files) -> None:
    head = commit_files("head", {"README.md": "# A\n"})
    blob = git(repository, "hash-object", "README.md", "-w").stdout.strip()
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).resolve_baseline(blob, current_revision=head)
    assert captured.value.detail.code == "BASELINE_NOT_COMMIT"


def test_rejects_sha256_abbreviation_that_looks_like_sha1(tmp_path: Path) -> None:
    repository = tmp_path / "sha256"
    repository.mkdir()
    initialized = git(
        repository,
        "init",
        "--object-format=sha256",
        "-b",
        "main",
        check=False,
    )
    if initialized.returncode != 0:
        pytest.skip("installed Git does not support SHA-256 repositories")
    (repository / "README.md").write_text("# Source\n", encoding="utf-8")
    git(repository, "add", "README.md")
    git(repository, "commit", "-m", "initial")
    head = git(repository, "rev-parse", "HEAD").stdout.strip()
    assert len(head) == 64

    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).resolve_baseline(head[:40], current_revision=head)
    assert captured.value.detail.code == "BASELINE_FORMAT"


def test_discovery_outside_repository_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository.discover(tmp_path)
    assert captured.value.detail.code == "REPOSITORY_NOT_FOUND"


def test_rejects_symlink_inputs(repository: Path, commit_files) -> None:
    target = repository / "target.md"
    target.write_text("# Target\n", encoding="utf-8")
    (repository / "link.md").symlink_to(target.name)
    git(repository, "add", ".")
    git(repository, "commit", "-m", "symlink")
    revision = git(repository, "rev-parse", "HEAD").stdout.strip()
    repo = GitRepository(root=repository)
    with pytest.raises(PolyglotGuardError) as captured:
        repo.read_markdown(revision, PurePosixPath("link.md"), role="source")
    assert captured.value.detail.code == "FILE_NOT_REGULAR"
    with pytest.raises(PolyglotGuardError):
        repo.ensure_worktree_regular_file(PurePosixPath("link.md"), role="translation")


def test_rejects_nonexact_worktree_spelling_on_case_insensitive_filesystem(
    repository: Path,
) -> None:
    actual = repository / "Translation.md"
    actual.write_text("# Translation\n", encoding="utf-8")
    alias = repository / "translation.md"
    if not alias.exists():
        pytest.skip("filesystem is case-sensitive")
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).ensure_worktree_regular_file(
            PurePosixPath("translation.md"), role="translation"
        )
    assert captured.value.detail.code == "CONFIG_MAPPING"


def test_rejects_invalid_utf8_markdown(repository: Path) -> None:
    (repository / "README.md").write_bytes(b"# \xff\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "binary markdown")
    revision = git(repository, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository(root=repository).read_markdown(
            revision, PurePosixPath("README.md"), role="source"
        )
    assert captured.value.detail.code == "MARKDOWN_ENCODING"


def test_config_path_must_stay_in_repository(repository: Path) -> None:
    with pytest.raises(PolyglotGuardError) as captured:
        resolve_config_path(repository.resolve(), "../outside.toml", "polyglotguard.toml")
    assert captured.value.detail.code == "CONFIG_LOCATION"

    with pytest.raises(PolyglotGuardError) as captured:
        resolve_config_path(
            repository.resolve(),
            str(repository.resolve() / "inside.toml"),
            "polyglotguard.toml",
        )
    assert captured.value.detail.code == "CONFIG_LOCATION"

    with pytest.raises(PolyglotGuardError) as captured:
        resolve_config_path(repository.resolve(), "", "polyglotguard.toml")
    assert captured.value.detail.code == "CONFIG_LOCATION"


def test_git_commands_disable_network_and_optional_writes(monkeypatch) -> None:
    captured_environment: dict[str, str] = {}
    monkeypatch.setenv("GIT_TRACE", "/tmp/polyglotguard-must-not-write-trace")
    monkeypatch.setenv("GIT_DIR", "/tmp/polyglotguard-wrong-repository")

    def capture_run(*_arguments, **options):
        captured_environment.update(options["env"])
        assert options["stdin"] is subprocess.DEVNULL
        return subprocess.CompletedProcess(["git", "--version"], 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", capture_run)
    assert _run_process(["git", "--version"]).returncode == 0
    assert captured_environment["GIT_NO_LAZY_FETCH"] == "1"
    assert captured_environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert captured_environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert captured_environment["GIT_TERMINAL_PROMPT"] == "0"
    assert captured_environment["GIT_LITERAL_PATHSPECS"] == "1"
    assert captured_environment["GIT_GRAFT_FILE"]
    assert "GIT_TRACE" not in captured_environment
    assert "GIT_DIR" not in captured_environment


def test_rejects_git_too_old_for_offline_partial_clone_guarantee(
    tmp_path: Path, monkeypatch
) -> None:
    def report_old_version(*_arguments, **_options):
        return subprocess.CompletedProcess(["git", "--version"], 0, b"git version 2.44.4\n", b"")

    monkeypatch.setattr(subprocess, "run", report_old_version)
    with pytest.raises(PolyglotGuardError) as captured:
        GitRepository.discover(tmp_path)
    assert captured.value.detail.code == "GIT_VERSION"
    assert "2.45.0 or later" in captured.value.detail.message
