# Agent instructions

These instructions apply to the entire repository.

## Product boundaries

- Treat `docs/PRD.md` as the product scope and `docs/design.md` as the implemented v0.1
  behavior contract.
- Keep `polyglotguard check` read-only, deterministic, and offline.
- Preserve the Git 2.45 minimum that enforces no lazy object fetching.
- Compare committed source history, not source and translated prose.
- Do not add AI translation, automatic edits, network calls, pull-request creation, or
  repository-specific detector rules to v0.1.
- DeepTutor is a fixture only. Core code must also pass the independent fixture.

## Public language

Use English for source code, comments, identifiers, documentation, errors, issues,
pull requests, and commit messages. Do not commit private learning notes or duplicate
translated documentation during v0.1.

## Commands

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest --cov=polyglotguard --cov-report=term-missing
python -m build
```

Update tests and documentation whenever public behavior changes. Keep fixtures offline
and record provenance beside any third-party-derived material.
