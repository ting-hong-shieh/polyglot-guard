"""PolyglotGuard's command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from polyglotguard import __version__
from polyglotguard.checker import check_repository
from polyglotguard.config import DEFAULT_CONFIG_NAME, load_config
from polyglotguard.errors import PolyglotGuardError
from polyglotguard.git import GitRepository, resolve_config_path
from polyglotguard.report import render_fatal, render_report


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return its documented process exit code."""

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = _build_parser()
    arguments = parser.parse_args(argv)

    if arguments.version:
        stdout.write(f"polyglotguard {__version__}\n")
        return 0
    if arguments.command != "check":
        parser.print_help(stdout)
        return 0

    try:
        repository = GitRepository.discover(Path(os.getcwd()))
        config_path = resolve_config_path(
            repository.root,
            arguments.config,
            DEFAULT_CONFIG_NAME,
        )
        config = load_config(config_path)
        result = check_repository(repository, config)
        render_report(result, stdout, stderr)
        return result.exit_code
    except PolyglotGuardError as exc:
        render_fatal(
            exc.detail.code,
            exc.detail.message,
            exc.detail.hint,
            stderr,
        )
        return 2
    except KeyboardInterrupt:
        render_fatal("INTERRUPTED", "Operation interrupted.", None, stderr)
        return 2
    except Exception as exc:  # Keep the documented runtime-error contract at the CLI boundary.
        render_fatal(
            "RUNTIME_ERROR",
            f"Unexpected runtime error: {exc}",
            (
                "Run the command again. If the error persists, report it with the "
                "PolyglotGuard version."
            ),
            stderr,
        )
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polyglotguard",
        description=(
            "Detect source Markdown sections that changed after a translation's "
            "recorded synchronization baseline."
        ),
    )
    parser.add_argument("--version", action="store_true", help="show the version and exit")
    commands = parser.add_subparsers(dest="command")
    check = commands.add_parser("check", help="check every configured translation")
    check.add_argument(
        "--config",
        metavar="PATH",
        help=f"repository-relative configuration path (default: {DEFAULT_CONFIG_NAME})",
    )
    return parser
