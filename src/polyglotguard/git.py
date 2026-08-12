"""Read committed Markdown from a local Git repository without changing it."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from polyglotguard.errors import PolyglotGuardError

_MINIMUM_GIT_VERSION = (2, 45, 0)
_GIT_VERSION = re.compile(r"\bgit version (\d+)\.(\d+)(?:\.(\d+))?")
_OBJECT_ID_LENGTHS = {"sha1": 40, "sha256": 64}


@dataclass(frozen=True, slots=True)
class GitRepository:
    root: Path

    @classmethod
    def discover(cls, start: Path) -> GitRepository:
        """Find the worktree root containing *start*."""

        _require_supported_git()
        start = start.resolve()
        command = ["git", "-C", str(start), "rev-parse", "--show-toplevel"]
        completed = _run_process(command)
        if completed.returncode != 0:
            raise PolyglotGuardError(
                "REPOSITORY_NOT_FOUND",
                f"No Git worktree was found from: {start}",
                hint="Run PolyglotGuard from inside a non-bare Git repository.",
            )
        root_bytes = completed.stdout.removesuffix(b"\n")
        if not root_bytes:
            raise PolyglotGuardError(
                "REPOSITORY_NOT_FOUND",
                "Git returned an empty worktree path.",
            )
        return cls(root=Path(os.fsdecode(root_bytes)).resolve())

    def current_revision(self) -> str:
        return self._rev_parse("HEAD^{commit}", context="current HEAD")

    def resolve_baseline(self, configured: str, *, current_revision: str) -> str:
        """Validate an immutable commit ID and require it to be an ancestor of HEAD."""

        object_format = self.object_format()
        expected_length = _OBJECT_ID_LENGTHS[object_format]
        if len(configured) != expected_length:
            raise PolyglotGuardError(
                "BASELINE_FORMAT",
                (
                    f"Configured baseline must be a full {expected_length}-character "
                    f"{object_format} object ID: {configured}"
                ),
                hint="Record the full object ID of the verified source commit.",
            )

        type_result = self._run(["cat-file", "-t", configured])
        if type_result.returncode != 0:
            raise _unavailable_revision(configured)
        object_type = _decode_command_output(type_result.stdout).strip()
        if object_type != "commit":
            raise PolyglotGuardError(
                "BASELINE_NOT_COMMIT",
                f"Configured baseline does not identify a commit object: {configured}",
                hint="Record the full object ID of the verified source commit.",
            )

        resolved = configured.lower()

        ancestry = self._run(["merge-base", "--is-ancestor", resolved, current_revision])
        shallow = self._run(["rev-parse", "--is-shallow-repository"])
        if ancestry.returncode != 0 and shallow.stdout.strip() == b"true":
            raise _unavailable_revision(configured)
        if ancestry.returncode == 1:
            raise PolyglotGuardError(
                "BASELINE_NOT_ANCESTOR",
                f"Configured baseline is not an ancestor of current HEAD: {configured}",
                hint="Use the verified synchronization commit from the current branch's history.",
            )
        if ancestry.returncode != 0:
            message = _decode_command_output(ancestry.stderr).strip()
            raise PolyglotGuardError(
                "GIT_ANCESTRY",
                f"Git could not verify baseline ancestry: {message or configured}",
            )
        return resolved

    def object_format(self) -> str:
        """Return the repository's storage object format."""

        completed = self._run(["rev-parse", "--show-object-format=storage"])
        value = _decode_command_output(completed.stdout).strip().lower()
        if completed.returncode != 0 or value not in _OBJECT_ID_LENGTHS:
            message = _decode_command_output(completed.stderr).strip()
            raise PolyglotGuardError(
                "GIT_OBJECT_FORMAT",
                f"Git could not determine the repository object format: {message or value}",
            )
        return value

    def ensure_regular_file(
        self,
        revision: str,
        path: PurePosixPath,
        *,
        role: str,
    ) -> str:
        """Require *path* to be a committed regular file at *revision*."""

        completed = self._run(["ls-tree", "-z", revision, "--", path.as_posix()])
        if completed.returncode != 0:
            message = _decode_command_output(completed.stderr).strip()
            raise PolyglotGuardError(
                "GIT_READ",
                f"Git could not inspect {role} '{path}' at {revision}: {message}",
            )
        if not completed.stdout:
            raise PolyglotGuardError(
                "FILE_MISSING",
                f"Configured {role} does not exist at {revision}: {path}",
            )

        metadata, _separator, _returned_path = completed.stdout.partition(b"\t")
        fields = metadata.split()
        if len(fields) != 3:
            raise PolyglotGuardError(
                "GIT_READ",
                f"Git returned unexpected metadata for {role}: {path}",
            )
        mode, object_type, object_id = fields
        if object_type != b"blob" or mode not in {b"100644", b"100755"}:
            raise PolyglotGuardError(
                "FILE_NOT_REGULAR",
                f"Configured {role} is not a regular committed file at {revision}: {path}",
                hint="Symlinks, directories, and submodules are not accepted as Markdown inputs.",
            )
        return _decode_command_output(object_id).strip().lower()

    def read_markdown(
        self,
        revision: str,
        path: PurePosixPath,
        *,
        role: str,
    ) -> str:
        """Return a committed regular Markdown file decoded as UTF-8."""

        try:
            object_id = self.ensure_regular_file(revision, path, role=role)
        except PolyglotGuardError as exc:
            if role == "baseline source" and exc.detail.code == "GIT_READ":
                raise _unavailable_revision(revision, path) from exc
            raise
        completed = self._run(["cat-file", "blob", object_id])
        if completed.returncode != 0:
            message = _decode_command_output(completed.stderr).strip()
            if role == "baseline source":
                raise _unavailable_revision(revision, path)
            raise PolyglotGuardError(
                "SOURCE_UNAVAILABLE",
                f"Git could not read {role} '{path}' at {revision}: {message}",
                hint=(
                    "Ensure the required source object exists locally. "
                    "PolyglotGuard does not fetch missing objects."
                ),
            )
        try:
            return completed.stdout.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise PolyglotGuardError(
                "MARKDOWN_ENCODING",
                f"Configured {role} is not valid UTF-8 at {revision}: {path}",
            ) from exc

    def ensure_worktree_regular_file(self, path: PurePosixPath, *, role: str) -> None:
        """Require a mapped worktree path to exist as a regular, non-symlink file."""

        candidate = self.root.joinpath(*path.parts)
        try:
            metadata = candidate.lstat()
        except FileNotFoundError as exc:
            raise PolyglotGuardError(
                "FILE_MISSING",
                f"Configured {role} does not exist in the worktree: {path}",
            ) from exc
        except OSError as exc:
            raise PolyglotGuardError(
                "FILE_UNREADABLE",
                f"Configured {role} could not be inspected: {path}: {exc}",
            ) from exc
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, ValueError) as exc:
            raise PolyglotGuardError(
                "FILE_OUTSIDE_REPOSITORY",
                f"Configured {role} resolves outside the repository: {path}",
            ) from exc
        if resolved != candidate:
            raise PolyglotGuardError(
                "FILE_NOT_REGULAR",
                f"Configured {role} passes through a symbolic link: {path}",
                hint="Use a regular file whose path stays inside the repository.",
            )
        self._ensure_exact_worktree_spelling(path, role=role)
        if not stat.S_ISREG(metadata.st_mode):
            raise PolyglotGuardError(
                "FILE_NOT_REGULAR",
                f"Configured {role} is not a regular worktree file: {path}",
                hint="Symlinks, directories, and submodules are not accepted as mappings.",
            )

    def _ensure_exact_worktree_spelling(self, path: PurePosixPath, *, role: str) -> None:
        directory = self.root
        for component in path.parts:
            try:
                names = {entry.name for entry in os.scandir(directory)}
            except OSError as exc:
                raise PolyglotGuardError(
                    "FILE_UNREADABLE",
                    f"Configured {role} path could not be inspected exactly: {path}: {exc}",
                ) from exc
            if component not in names:
                raise PolyglotGuardError(
                    "CONFIG_MAPPING",
                    f"Configured {role} path does not match on-disk spelling: {path}",
                    hint="Use the exact case and Unicode spelling of every path component.",
                )
            directory /= component

    def ensure_distinct_worktree_file(
        self,
        path: PurePosixPath,
        others: Sequence[PurePosixPath],
        *,
        role: str,
    ) -> None:
        """Require a mapping to identify a different physical file from its peers."""

        candidate = self.root.joinpath(*path.parts)
        for other in others:
            other_candidate = self.root.joinpath(*other.parts)
            try:
                same_file = candidate.samefile(other_candidate)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise PolyglotGuardError(
                    "FILE_UNREADABLE",
                    f"Configured {role} file identity could not be checked: {path}: {exc}",
                ) from exc
            if same_file:
                raise PolyglotGuardError(
                    "CONFIG_MAPPING",
                    f"Configured {role} must identify a distinct worktree file: {path}",
                    hint=f"Do not map the same physical file as '{other}'.",
                )

    def _rev_parse(self, expression: str, *, context: str) -> str:
        completed = self._run(["rev-parse", "--verify", expression])
        if completed.returncode != 0:
            message = _decode_command_output(completed.stderr).strip()
            raise PolyglotGuardError(
                "GIT_REVISION",
                f"Git could not resolve {context}: {message or expression}",
            )
        value = _decode_command_output(completed.stdout).strip().lower()
        return value

    def _run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
        return _run_process(["git", "-C", str(self.root), *arguments])


def resolve_config_path(repository_root: Path, value: str | None, default_name: str) -> Path:
    """Resolve a CLI configuration path and keep it inside the repository."""

    if value is not None and (
        not value
        or "\\" in value
        or Path(value).is_absolute()
        or bool(PureWindowsPath(value).drive)
    ):
        raise PolyglotGuardError(
            "CONFIG_LOCATION",
            f"Configuration path must be repository-relative: {value}",
        )
    candidate = repository_root / (default_name if value is None else value)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise PolyglotGuardError(
            "CONFIG_LOCATION",
            f"Configuration must be inside the repository: {candidate}",
        ) from exc
    return resolved


def _run_process(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    environment = {
        name: value for name, value in os.environ.items() if not name.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    try:
        return subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=environment,
        )
    except FileNotFoundError as exc:
        raise PolyglotGuardError(
            "GIT_NOT_FOUND",
            "Git is required but was not found on PATH.",
        ) from exc
    except OSError as exc:
        raise PolyglotGuardError(
            "GIT_EXECUTION",
            f"Git could not be started: {exc}",
        ) from exc


def _decode_command_output(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _require_supported_git() -> None:
    completed = _run_process(["git", "--version"])
    output = _decode_command_output(completed.stdout).strip()
    match = _GIT_VERSION.search(output)
    if completed.returncode != 0 or match is None:
        raise PolyglotGuardError(
            "GIT_VERSION",
            f"PolyglotGuard could not determine the installed Git version: {output}",
        )
    version = tuple(int(part or 0) for part in match.groups())
    if version < _MINIMUM_GIT_VERSION:
        required = ".".join(str(part) for part in _MINIMUM_GIT_VERSION)
        installed = ".".join(str(part) for part in version)
        raise PolyglotGuardError(
            "GIT_VERSION",
            f"PolyglotGuard requires Git {required} or later; found {installed}.",
            hint=(
                "Upgrade Git so missing partial-clone objects can be checked without lazy fetching."
            ),
        )


def _unavailable_revision(revision: str, path: PurePosixPath | None = None) -> PolyglotGuardError:
    subject = f"Configured baseline is unavailable from local Git history: {revision}"
    if path is not None:
        subject += f" (source: {path})"
    return PolyglotGuardError(
        "BASELINE_UNAVAILABLE",
        subject,
        hint=(
            "Confirm the commit ID and ensure the required history exists locally. "
            "PolyglotGuard does not fetch or deepen a clone automatically."
        ),
    )
