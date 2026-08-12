# Contributing to PolyglotGuard

PolyglotGuard welcomes focused bug fixes, tests, documentation corrections, and
proposals that preserve its read-only drift-detection model.

## Before starting

For behavior changes, open or select an issue with context, constraints, and testable
acceptance criteria. Discuss changes that affect the configuration schema, section
identity, output contract, or v0.1 scope before implementing them.

Do not add copied third-party documentation as a fixture without an immutable source
revision, license review, attribution, a record of adaptations, and explicit expected
results.

## Development setup

PolyglotGuard requires Python 3.11 or later and Git 2.45 or later.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Create a branch from `main`, keep commits scoped, and use English for public code,
documentation, issues, pull requests, and commit messages.

## Required checks

Run these commands before opening a pull request:

```bash
ruff check .
ruff format --check .
pytest --cov=polyglotguard --cov-report=term-missing
python -m build
```

Tests should cover observable behavior and error recovery. The coverage threshold is a
backstop, not a reason to add assertions without behavioral value.

## Pull requests

Describe the observed problem, the chosen change, and the verification performed.
Keep unrelated refactors out of the same pull request. Merge only after the required
checks pass and the public behavior matches the PRD and design contract.
