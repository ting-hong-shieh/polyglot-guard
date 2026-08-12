from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from polyglotguard.config import load_config
from polyglotguard.errors import PolyglotGuardError

VALID_OID = "0123456789abcdef0123456789abcdef01234567"


def write_config(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_one_source_and_ordered_translations(tmp_path: Path) -> None:
    config = load_config(
        write_config(
            tmp_path / "polyglotguard.toml",
            f'''version = 1
source = "README.md"

[[translations]]
path = "docs/README.zh-TW.md"
locale = "zh-TW"
baseline = "{VALID_OID.upper()}"

[[translations]]
path = "docs/README.ja.markdown"
baseline = "{VALID_OID}"
''',
        )
    )

    assert config.source == PurePosixPath("README.md")
    assert [item.path.as_posix() for item in config.translations] == [
        "docs/README.zh-TW.md",
        "docs/README.ja.markdown",
    ]
    assert config.translations[0].locale == "zh-TW"
    assert config.translations[1].locale is None
    assert config.translations[0].baseline == VALID_OID


@pytest.mark.parametrize(
    ("content", "code"),
    [
        ("source = 'README.md'\ntranslations = []\n", "CONFIG_VERSION"),
        ("version = true\nsource = 'README.md'\ntranslations = []\n", "CONFIG_VERSION"),
        ("version = 1\nsource = 'README.md'\ntranslations = []\n", "CONFIG_TRANSLATIONS"),
        (
            "version = 1\nsource = 'README.md'\nunknown = 3\ntranslations = []\n",
            "CONFIG_UNKNOWN_FIELD",
        ),
        (
            f"version = 1\nsource = 'README.md'\n[[translations]]\n"
            f"path='zh.txt'\nbaseline='{VALID_OID}'\n",
            "CONFIG_PATH",
        ),
        (
            "version = 1\nsource = 'README.md'\n[[translations]]\n"
            "path='../zh.md'\nbaseline='main'\n",
            "CONFIG_PATH",
        ),
        (
            "version = 1\nsource = 'README.md'\n[[translations]]\npath='zh.md'\nbaseline='main'\n",
            "CONFIG_BASELINE",
        ),
        (
            f"version = 1\nsource = 'README.md'\n[[translations]]\n"
            f"path='README.md'\nbaseline='{VALID_OID}'\n",
            "CONFIG_MAPPING",
        ),
        (
            f"version = 1\nsource = 'README.md'\n[[translations]]\n"
            f"path='zh.md'\nbaseline='{VALID_OID}'\nlocale=' zh '\n",
            "CONFIG_LOCALE",
        ),
        (
            f"version = 1\nsource = 'README.md'\n[[translations]]\n"
            f"path='zh.md'\nbaseline='{VALID_OID}'\nlocale='zh\u0085TW'\n",
            "CONFIG_LOCALE",
        ),
        (
            f"version = 1\nsource = 'README.md'\n[[translations]]\n"
            f"path='zh.md'\nbaseline='{VALID_OID}'\nlocale='zh\u202eTW'\n",
            "CONFIG_LOCALE",
        ),
    ],
)
def test_rejects_invalid_contract(tmp_path: Path, content: str, code: str) -> None:
    with pytest.raises(PolyglotGuardError) as captured:
        load_config(write_config(tmp_path / "polyglotguard.toml", content))
    assert captured.value.detail.code == code


def test_rejects_duplicate_mapping(tmp_path: Path) -> None:
    content = f'''version = 1
source = "README.md"
[[translations]]
path = "zh.md"
baseline = "{VALID_OID}"
[[translations]]
path = "zh.md"
baseline = "{VALID_OID}"
'''
    with pytest.raises(PolyglotGuardError) as captured:
        load_config(write_config(tmp_path / "polyglotguard.toml", content))
    assert captured.value.detail.code == "CONFIG_MAPPING"


def test_reports_toml_duplicate_key(tmp_path: Path) -> None:
    content = "version = 1\nversion = 1\nsource = 'README.md'\ntranslations = []\n"
    with pytest.raises(PolyglotGuardError) as captured:
        load_config(write_config(tmp_path / "polyglotguard.toml", content))
    assert captured.value.detail.code == "CONFIG_TOML"


def test_reports_unreadable_configuration_path(tmp_path: Path) -> None:
    config_directory = tmp_path / "polyglotguard.toml"
    config_directory.mkdir()
    with pytest.raises(PolyglotGuardError) as captured:
        load_config(config_directory)
    assert captured.value.detail.code == "CONFIG_UNREADABLE"


def test_reports_invalid_utf8_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "polyglotguard.toml"
    config_path.write_bytes(b"version = 1\nsource = '\xff.md'\ntranslations = []\n")
    with pytest.raises(PolyglotGuardError) as captured:
        load_config(config_path)
    assert captured.value.detail.code == "CONFIG_TOML"
