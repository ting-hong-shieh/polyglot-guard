"""Classify source section changes between two revisions."""

from __future__ import annotations

from polyglotguard.model import ChangeKind, SectionChange, SectionTree


def compare_section_trees(
    baseline: SectionTree,
    current: SectionTree,
) -> tuple[SectionChange, ...]:
    """Return Added, Modified, then Deleted changes in document order."""

    baseline_by_path = {section.path: section for section in baseline.sections}
    current_by_path = {section.path: section for section in current.sections}

    added = tuple(
        SectionChange(kind=ChangeKind.ADDED, path=section.path)
        for section in current.sections
        if section.path not in baseline_by_path
    )
    modified = tuple(
        SectionChange(kind=ChangeKind.MODIFIED, path=section.path)
        for section in current.sections
        if section.path in baseline_by_path
        and (
            section.level != baseline_by_path[section.path].level
            or section.body != baseline_by_path[section.path].body
        )
    )
    deleted = tuple(
        SectionChange(kind=ChangeKind.DELETED, path=section.path)
        for section in baseline.sections
        if section.path not in current_by_path
    )
    return (*added, *modified, *deleted)
