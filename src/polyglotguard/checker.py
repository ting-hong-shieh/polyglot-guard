"""Coordinate configuration, Git reads, parsing, detection, and per-translation results."""

from __future__ import annotations

from polyglotguard.detector import compare_section_trees
from polyglotguard.errors import PolyglotGuardError
from polyglotguard.git import GitRepository
from polyglotguard.markdown import parse_markdown
from polyglotguard.model import (
    ProjectConfig,
    RunResult,
    SectionTree,
    TranslationResult,
    TranslationStatus,
)


def check_repository(repository: GitRepository, config: ProjectConfig) -> RunResult:
    """Check every configured translation while preserving declaration order."""

    current_revision = repository.current_revision()
    current_source = repository.read_markdown(
        current_revision,
        config.source,
        role="current source",
    )
    current_tree = parse_markdown(current_source)
    baseline_trees: dict[str, SectionTree] = {current_revision: current_tree}

    results: list[TranslationResult] = []
    validated_translation_paths = []
    for translation in config.translations:
        try:
            repository.ensure_worktree_regular_file(
                translation.path,
                role="translation",
            )
            repository.ensure_distinct_worktree_file(
                translation.path,
                validated_translation_paths,
                role="translation",
            )
            validated_translation_paths.append(translation.path)
            baseline = repository.resolve_baseline(
                translation.baseline,
                current_revision=current_revision,
            )
            baseline_tree = baseline_trees.get(baseline)
            if baseline_tree is None:
                baseline_source = repository.read_markdown(
                    baseline,
                    config.source,
                    role="baseline source",
                )
                baseline_tree = parse_markdown(baseline_source)
                baseline_trees[baseline] = baseline_tree

            changes = compare_section_trees(baseline_tree, current_tree)
            status = TranslationStatus.STALE if changes else TranslationStatus.UP_TO_DATE
            results.append(
                TranslationResult(
                    path=translation.path,
                    locale=translation.locale,
                    configured_baseline=translation.baseline,
                    resolved_baseline=baseline,
                    status=status,
                    changes=changes,
                )
            )
        except PolyglotGuardError as exc:
            results.append(
                TranslationResult(
                    path=translation.path,
                    locale=translation.locale,
                    configured_baseline=translation.baseline,
                    resolved_baseline=None,
                    status=TranslationStatus.ERROR,
                    error=exc.detail,
                )
            )

    return RunResult(
        source=config.source,
        current_revision=current_revision,
        translations=tuple(results),
    )
