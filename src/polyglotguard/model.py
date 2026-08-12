"""Language-independent models shared by detection and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from polyglotguard.errors import ErrorDetail
from polyglotguard.terminal import quote_terminal_text


@dataclass(frozen=True, slots=True)
class HeadingComponent:
    """One normalized heading and its occurrence among equal sibling headings."""

    label: str
    occurrence: int = 1

    def display(self) -> str:
        label = quote_terminal_text(self.label)
        if self.occurrence == 1:
            return label
        return f"{label} [{self.occurrence}]"


@dataclass(frozen=True, slots=True)
class SectionPath:
    """The deterministic identity of a section in a Markdown hierarchy."""

    components: tuple[HeadingComponent, ...]

    @classmethod
    def preamble(cls) -> SectionPath:
        return cls(components=())

    def display(self) -> str:
        if not self.components:
            return "(document preamble)"
        return " > ".join(component.display() for component in self.components)


@dataclass(frozen=True, slots=True)
class Section:
    """A source section with only its direct body, excluding descendant sections."""

    path: SectionPath
    level: int
    body: str
    order: int


@dataclass(frozen=True, slots=True)
class SectionTree:
    """A source document represented as deterministic ordered sections."""

    sections: tuple[Section, ...]


class ChangeKind(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class SectionChange:
    kind: ChangeKind
    path: SectionPath


@dataclass(frozen=True, slots=True)
class TranslationConfig:
    path: PurePosixPath
    baseline: str
    locale: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    source: PurePosixPath
    translations: tuple[TranslationConfig, ...]


class TranslationStatus(StrEnum):
    UP_TO_DATE = "up_to_date"
    STALE = "stale"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TranslationResult:
    path: PurePosixPath
    locale: str | None
    configured_baseline: str
    resolved_baseline: str | None
    status: TranslationStatus
    changes: tuple[SectionChange, ...] = ()
    error: ErrorDetail | None = None

    @property
    def review_count(self) -> int:
        return len(self.changes)


@dataclass(frozen=True, slots=True)
class RunResult:
    source: PurePosixPath
    current_revision: str
    translations: tuple[TranslationResult, ...]

    @property
    def exit_code(self) -> int:
        statuses = {translation.status for translation in self.translations}
        if TranslationStatus.ERROR in statuses:
            return 2
        if TranslationStatus.STALE in statuses:
            return 1
        return 0
