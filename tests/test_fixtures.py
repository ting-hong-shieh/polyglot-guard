from __future__ import annotations

import tomllib
from io import StringIO
from pathlib import Path

import pytest

from polyglotguard.cli import main
from polyglotguard.detector import compare_section_trees
from polyglotguard.markdown import parse_markdown
from polyglotguard.model import ChangeKind

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("name", ["deeptutor", "independent"])
def test_fixture_matches_reviewed_expectations(name: str) -> None:
    directory = FIXTURES / name
    baseline = parse_markdown((directory / "baseline.md").read_text(encoding="utf-8"))
    current = parse_markdown((directory / "current.md").read_text(encoding="utf-8"))
    with (directory / "expected.toml").open("rb") as stream:
        expected = tomllib.load(stream)

    actual = {kind.value: [] for kind in ChangeKind}
    for change in compare_section_trees(baseline, current):
        actual[change.kind.value].append(change.path.display())

    assert actual == expected


def test_deeptutor_fixture_hashes_preserve_reviewed_adaptation() -> None:
    import hashlib

    directory = FIXTURES / "deeptutor"
    expected = {
        "baseline.md": "6fbdca625485d5b21fb8978ee4121f2c3a066f7d13ee6e906d5eb07fa59d686e",
        "current.md": "8e7b95b1a01c06eb72e3370f90139030428bfc65c78e77c209dcd2383405fbeb",
        "LICENSE.deeptutor": "cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4",
        "translation.zh-CN.md": "c2c82055ab2b90a395ef0136b15997b68e7819918dadd2fde2c584ff9fe31f08",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest


def test_independent_fixture_hashes_preserve_reviewed_scenario() -> None:
    import hashlib

    directory = FIXTURES / "independent"
    expected = {
        "baseline.md": "14478cfc629417085bc1b3b731549d9cef220f8bce1f199785848e75c51354ab",
        "current.md": "31ccced0556890fb685387ca0140a16fdb03d793d6d4da46412abebdca384466",
        "translation.fr.md": "9cbac0b729a07ca87de0fda86d356f4bb4be7ca9407320e76cfbc92b155c78aa",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest


def test_deeptutor_fixture_produces_useful_cli_report(
    repository: Path, commit_files, monkeypatch
) -> None:
    directory = FIXTURES / "deeptutor"
    baseline = commit_files(
        "verified translation baseline",
        {
            "README.md": (directory / "baseline.md").read_text(encoding="utf-8"),
            "README.zh-CN.md": (directory / "translation.zh-CN.md").read_text(encoding="utf-8"),
        },
    )
    commit_files(
        "current source",
        {"README.md": (directory / "current.md").read_text(encoding="utf-8")},
    )
    (repository / "polyglotguard.toml").write_text(
        f'''version = 1
source = "README.md"
[[translations]]
path = "README.zh-CN.md"
locale = "zh-CN"
baseline = "{baseline}"
''',
        encoding="utf-8",
    )
    monkeypatch.chdir(repository)
    stdout = StringIO()
    stderr = StringIO()

    assert main(["check"], stdout=stdout, stderr=stderr) == 1
    assert stderr.getvalue() == ""
    report = stdout.getvalue()
    assert "Status: STALE" in report
    assert "Option 1 — Install From PyPI" in report
    assert "🚀 Get Started" in report
    assert "Option 1 — Install DeepTutor" in report
    assert "3 sections require translation review" in report


def test_independent_non_readme_mapping_uses_the_same_detector(
    repository: Path, commit_files, monkeypatch
) -> None:
    directory = FIXTURES / "independent"
    baseline = commit_files(
        "verified orchard translation baseline",
        {
            "docs/orchard.md": (directory / "baseline.md").read_text(encoding="utf-8"),
            "translations/fr/manuel.md": (directory / "translation.fr.md").read_text(
                encoding="utf-8"
            ),
        },
    )
    commit_files(
        "current orchard source",
        {"docs/orchard.md": (directory / "current.md").read_text(encoding="utf-8")},
    )
    (repository / "polyglotguard.toml").write_text(
        f'''version = 1
source = "docs/orchard.md"
[[translations]]
path = "translations/fr/manuel.md"
locale = "fr"
baseline = "{baseline}"
''',
        encoding="utf-8",
    )
    monkeypatch.chdir(repository)
    stdout = StringIO()

    assert main(["check"], stdout=stdout, stderr=StringIO()) == 1
    report = stdout.getvalue()
    assert '"Orchard Manual" > "Seasonal Care" > "Frost Alerts"' in report
    assert '"Orchard Manual" > "Seasonal Care" > "Watering"' in report
    assert '"Orchard Manual" > "Seasonal Care" > "Retired Sprayer"' in report
