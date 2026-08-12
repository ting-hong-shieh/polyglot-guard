# PolyglotGuard

PolyglotGuard is a read-only CLI that finds source Markdown sections changed since a
translation was last reviewed. It reports translation maintenance work without
comparing prose across languages or editing documentation.

> **Project status:** v0.1 is implemented and under pre-release validation. The
> documented installation path is a source checkout.

## How it works

For each translated document, a maintainer records the source commit used during the
last complete translation review. PolyglotGuard compares that historical source with
the source at the current `HEAD`:

```text
source at verified baseline ──compare──> source at HEAD
             │                              │
             └──────── Added / Modified / Deleted sections
```

The translation file identifies who needs the report, but v0.1 does not parse its
prose or require its headings to match the source. `STALE` means that human review is
needed; it does not mean the translation has been proven incorrect.

## Requirements

- Python 3.11 or later
- Git 2.45 or later available on `PATH`
- a non-bare local Git worktree

PolyglotGuard runs offline after installation.

## Install from source

```bash
git clone https://github.com/ting-hong-shieh/polyglot-guard.git
cd polyglot-guard
python -m pip install .
```

The install adds the `polyglotguard` command.

## Configure a repository

Create `polyglotguard.toml` at the root of the repository being checked:

```toml
version = 1
source = "README.md"

[[translations]]
path = "docs/README.zh-TW.md"
locale = "zh-TW"
baseline = "0123456789abcdef0123456789abcdef01234567"

[[translations]]
path = "docs/README.ja.md"
baseline = "89abcdef0123456789abcdef0123456789abcdef"
```

Each `baseline` must be the full commit ID of the source revision actually reviewed
for that translation. Find the full ID of a known commit with:

```bash
git rev-parse <verified-commit>
```

Do not choose the latest translation commit merely because it changed the translated
file. If no historical source baseline can be verified, you may start tracking from
the current source:

```bash
git rev-parse HEAD
```

This bootstrap records no information about drift before that commit. After a human
reviews a later source revision and updates the translation as needed, manually replace
only that translation's baseline with the exact reviewed commit.

See [the v0.1 design](docs/design.md#configuration) for the full validation contract.

## Check translations

Run the command anywhere inside the configured repository:

```bash
polyglotguard check
```

Example stale report:

```text
PolyglotGuard

Source: README.md
Current revision: a5f5c8f52ec82fdbf53f8f608f87ae2d44ff21b8

Translation
  Path: docs/README.zh-TW.md
  Locale: zh-TW
  Baseline: 0123456789abcdef0123456789abcdef01234567
  Status: STALE
  Source changes after this baseline require human translation review.

  Added
    - "Installation" > "Package manager"

  Modified
    - "Installation"

  Deleted
    - "Legacy setup"

  3 sections require translation review.
```

PolyglotGuard reads both source versions from committed Git objects. Staged,
unstaged, and untracked source edits are ignored. It never fetches missing history;
an unavailable baseline produces an error explaining that the local clone may be
incomplete.

Use `--config` to select a different TOML file inside the repository:

```bash
polyglotguard check --config config/docs-drift.toml
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Every configured translation is up to date |
| `1` | At least one translation needs review |
| `2` | A configuration, repository, parsing, or runtime error occurred |

An error takes precedence over a stale result when a run contains both.

## v0.1 boundaries

PolyglotGuard v0.1:

- checks one source Markdown file mapped to one or more translations;
- detects Added, Modified, and Deleted source sections using CommonMark headings;
- supports a separate immutable baseline for each translation;
- produces deterministic terminal output for local use and CI;
- performs no repository writes and requires no AI model or network service.

It does not judge translation quality, compare source and translation structure,
modify translated files, generate translations, publish JSON, or open pull requests.

## Development

Create an isolated environment and install the development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run the same checks used by CI:

```bash
ruff check .
ruff format --check .
pytest --cov=polyglotguard --cov-report=term-missing
python -m build
```

The test suite includes a pinned, attributed DeepTutor adaptation and a wholly
independent synthetic fixture. Neither fixture changes detector behavior.

## Documentation

- [Product requirements](docs/PRD.md)
- [v0.1 design and behavior](docs/design.md)
- [Research evidence](docs/research.md)
- [Contributing](CONTRIBUTING.md)

## License

PolyglotGuard is licensed under the [Apache License 2.0](LICENSE).
