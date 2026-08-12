# Multilingual Markdown drift: research notes

**Status:** Complete

**Research cutoff:** 2026-08-12

**Timebox:** 2–3 day desk study

## Purpose

This spike examines how open-source projects notice and manage translated
documentation after the source changes. It is bounded to detection and maintenance
state. It does not evaluate translation quality, design automatic repair, or claim
that the sampled workflows are exhaustive or novel.

For this study, **drift** means source changes made after a translation's last
verified synchronization point. A drift report identifies work that needs human
review; it does not prove that the translated prose is wrong.

## Method and evidence set

The study uses repository files and history rather than comparing prose across
languages. Every repository observation below is pinned to an immutable commit.

| Case | Why it was selected | Pinned evidence |
| --- | --- | --- |
| DeepTutor | The motivating case: one large Markdown README and ten localized README files | [snapshot `456f9c2`](https://github.com/HKUDS/DeepTutor/tree/456f9c24226e008f1ff07a7e3455d7b4d39f6221), [source-only change `cd26210`](https://github.com/HKUDS/DeepTutor/commit/cd2621014ad81255558a6f563e827a406bff3e8a), [later localized update `8bced8e`](https://github.com/HKUDS/DeepTutor/commit/8bced8eef169a5838eecb464b7e689bb7e0dd3bf) |
| FastAPI | Page-for-page Markdown translations plus a custom maintenance workflow | [`0e6342d`](https://github.com/fastapi/fastapi/tree/0e6342d90e62e93d1082280dde87c322ecbc524e) |
| Rust By Example | Markdown source translated through gettext catalogs | [`15308f3`](https://github.com/rust-lang/rust-by-example/tree/15308f3e951814ef3475d2b58f48276e6b17b9af), with [`mdbook-i18n-helpers@7f9468a`](https://github.com/google/mdbook-i18n-helpers/tree/7f9468a5a01a3d83bad900bba186fc56eb2fae9b) |
| MDN Web Docs | A cross-repository workflow with an explicit source commit on each translated page | translated content at [`64d96ff`](https://github.com/mdn/translated-content/tree/64d96ff9d2290f31405ec5d988c302cee61432c4), English content at [`df16a79`](https://github.com/mdn/content/tree/df16a79ae972a3e27c129b35d9e2c9baf753da40) |

## Observations

### DeepTutor

1. Source and translation updates can be separate batches. Commit
   [`cd26210`](https://github.com/HKUDS/DeepTutor/commit/cd2621014ad81255558a6f563e827a406bff3e8a)
   added `CONTAINERIZATION.md` and a pointer in the English README without changing a
   localized README. Six days later,
   [`8bced8e`](https://github.com/HKUDS/DeepTutor/commit/8bced8eef169a5838eecb464b7e689bb7e0dd3bf)
   updated all ten localized README files with the corresponding pointer. This is one
   concrete maintenance window, not evidence of a general update cadence.
2. Touching source and translations in the same commit does not establish complete
   synchronization. Release commit
   [`456f9c2`](https://github.com/HKUDS/DeepTutor/commit/456f9c24226e008f1ff07a7e3455d7b4d39f6221)
   added and reorganized English release entries and changed Settings documentation.
   Each localized README changed only its Settings description.
3. Structure can differ by design or history. At that snapshot, the English README
   contains a long
   [`Releases` section](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/README.md#L49-L180),
   while the
   [Chinese README](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/assets/README/README_CN.md#L47-L58)
   moves directly to News and Key Features. The files do not show whether that
   difference is intentional, so it is evidence of structural divergence rather
   than an incorrect translation.
4. The sampled [English](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/README.md),
   [Chinese](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/assets/README/README_CN.md),
   and [Japanese](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/assets/README/README_JA.md)
   README files contain no source commit identifying the last verified synchronization
   point. File history shows when files changed, not which source revision a
   maintainer reviewed.
5. Markdown context matters. Shell comments beginning with `#` occur inside a
   [fenced block](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/README.md#L231-L246);
   a heading regular expression would misclassify them. Product tours also use
   [`<details>` elements](https://github.com/HKUDS/DeepTutor/blob/456f9c24226e008f1ff07a7e3455d7b4d39f6221/README.md#L452-L470),
   so a heading-based model deliberately reports some areas at coarse granularity.

### FastAPI

1. FastAPI maps English Markdown paths to locale paths and maintains explicit
   exclusions ([mapping rules](https://github.com/fastapi/fastapi/blob/0e6342d90e62e93d1082280dde87c322ecbc524e/scripts/translate.py#L18-L58)).
2. Its script reports missing, removable, and outdated pages. “Outdated” compares
   the latest commit time for the English path with the latest commit time for the
   locale path ([implementation](https://github.com/fastapi/fastapi/blob/0e6342d90e62e93d1082280dde87c322ecbc524e/scripts/translate.py#L301-L376)).
   It does not store a verified source baseline or identify changed sections.
3. A [scheduled workflow](https://github.com/fastapi/fastapi/blob/0e6342d90e62e93d1082280dde87c322ecbc524e/.github/workflows/translate.yml#L1-L137)
   checks full history, invokes those reports, uses an external model to prepare
   updates, validates output, and opens pull requests. That repair workflow requires
   network access and writes, both outside PolyglotGuard v0.1.

### Rust By Example

1. Rust By Example extracts Markdown into a gettext template, initializes locale PO
   catalogs, merges source changes with `msgmerge`, and exposes progress through
   `msgfmt --statistics` ([translation guide](https://github.com/rust-lang/rust-by-example/blob/15308f3e951814ef3475d2b58f48276e6b17b9af/TRANSLATING.md#L8-L59)).
2. The underlying helper preserves unchanged messages, marks removed messages as old,
   and marks changed messages as fuzzy
   ([tool documentation](https://github.com/google/mdbook-i18n-helpers/blob/7f9468a5a01a3d83bad900bba186fc56eb2fae9b/i18n-helpers/USAGE.md#L116-L129)).
   This records unit-level state, but the translated artifact is a PO catalog rather
   than mapped Markdown.
3. Running the documented statistics command at `15308f3` reported 2,761 translated
   and 151 untranslated messages in
   [`po/ja.po`](https://github.com/rust-lang/rust-by-example/blob/15308f3e951814ef3475d2b58f48276e6b17b9af/po/ja.po),
   while [`po/zh.po`](https://github.com/rust-lang/rust-by-example/blob/15308f3e951814ef3475d2b58f48276e6b17b9af/po/zh.po)
   reported 2,959 translated messages. These are completeness signals, not quality
   scores.
4. CI builds every locale and checks links, but it does not use translation statistics
   as a completeness gate ([workflow](https://github.com/rust-lang/rust-by-example/blob/15308f3e951814ef3475d2b58f48276e6b17b9af/.github/workflows/rbe.yml#L1-L79)).
   Build validity, link validity, and completeness are separate signals.

### MDN Web Docs

1. MDN stores English and translated Markdown in separate repositories. A pinned
   Japanese page records an immutable English revision in front matter as
   [`l10n.sourceCommit`](https://github.com/mdn/translated-content/blob/64d96ff9d2290f31405ec5d988c302cee61432c4/files/ja/web/accessibility/aria/reference/attributes/aria-atomic/index.md#L1-L7).
2. That revision resolves to an
   [English source page](https://github.com/mdn/content/blob/f6d04a43eadf5ab26a3488942dfb318b58234eb5/files/en-us/web/accessibility/aria/attributes/aria-atomic/index.md).
   By the pinned current snapshot, the page has a
   [new path and changed metadata, links, and heading capitalization](https://github.com/mdn/content/blob/df16a79ae972a3e27c129b35d9e2c9baf753da40/files/en-us/web/accessibility/aria/reference/attributes/aria-atomic/index.md).
   The baseline remains distinct from later path maintenance.
3. A [daily workflow](https://github.com/mdn/translated-content/blob/64d96ff9d2290f31405ec5d988c302cee61432c4/.github/workflows/sync-translated-content.yml#L1-L117)
   checks out both repositories, synchronizes moved content, and opens a pull request.
   It illustrates cross-repository structural maintenance beyond v0.1.

## Recurring patterns

| Source change or condition | Evidence | Maintenance consequence |
| --- | --- | --- |
| Added guidance or sections | DeepTutor's container guide and README pointer | Add corresponding information to maintained locales |
| Modified prose within an existing section | DeepTutor's Settings description | Review the mapped section without rereading the whole document |
| Link, metadata, or path changes | MDN's `aria-atomic` page | Review technical references even if prose is mostly stable |
| Deleted or moved material | FastAPI removable pages, gettext old messages, MDN path sync | Remove, relocate, or explicitly retain locale content |
| Batched locale updates | DeepTutor's six-day window and FastAPI's schedule | Track each translation independently |
| Persistent structural differences | DeepTutor's source-only Releases section | Do not treat structure parity as proof of drift |
| Markdown that resembles headings | DeepTutor's fenced shell comments | Parse Markdown context instead of scanning `#` prefixes |

## Approaches compared

These workflows solve overlapping parts of the maintenance problem. This sample is
too small to support a novelty or market-coverage claim.

| Approach | Recorded state | Unit | Automation observed |
| --- | --- | --- | --- |
| Co-edit source and locale replicas | Commit membership only | Whole files selected manually | DeepTutor commits |
| Compare last commit times | Latest source and locale timestamps | Whole page | FastAPI scheduled workflow |
| Merge gettext messages | Translated, untranslated, fuzzy, and old entries | Extracted message | Rust By Example commands and CI |
| Record an immutable source revision | `l10n.sourceCommit` per translated page | Whole page with an exact historical reference | MDN synchronization workflow |
| Use GitHub Actions | Schedule and runner configuration, not synchronization state | Defined by the invoked script | FastAPI, Rust By Example, and MDN use different checks |

## Inferences

The statements in this section are project-level interpretations of the observations.

1. **An explicit source revision is stronger than a timestamp or co-edit heuristic.**
   A full commit ID identifies the source tree a maintainer verified. A later
   locale-only edit does not prove every intervening source change was reviewed, and
   files in the same commit can receive different subsets of a change.
2. **Synchronization state belongs to each translation.** Locales are updated at
   different times and in different batches, so each mapping needs its own baseline.
3. **Source-history comparison avoids an unnecessary language problem.** Once a
   baseline is known, the tool can identify changed source sections without comparing
   prose across languages.
4. **STALE should mean “review required,” not “translation incorrect.”** Structural
   divergence can be intentional, and some source changes do not need new translated
   prose.
5. **Heading paths provide a useful middle ground.** Whole-page flags are coarse for
   long READMEs, while gettext requires a transformed catalog workflow. Markdown
   headings are human-readable units for repositories that keep translations in
   Markdown.
6. **Detection and repair should remain separate.** Generation, validation, PR
   creation, and human coordination form a larger, write-enabled workflow.
7. **A baseline cannot reconstruct earlier unrecorded drift.** Starting at a newly
   verified current revision is honest; claiming older coverage would not be.

## Implications for v0.1

1. Require a full immutable source commit for every translation. Do not infer it from
   file timestamps, the latest translation commit, or a commit that touched both files.
2. Resolve the baseline locally and compare committed source Markdown at that commit
   with committed `HEAD`. Missing history is an error; do not fetch or deepen a clone.
3. Keep baselines per translation.
4. Parse only the two source revisions. Translation paths identify mappings and must
   exist, but translated prose and structure are not inspected.
5. Parse fenced code blocks contextually. Treat raw HTML deterministically as content;
   HTML summaries do not become section identities.
6. Report Added, Modified, and Deleted sections by normalized heading path. Use
   delete-plus-add for uncertain renames and moves.
7. Include links, code, and other Markdown in content comparison, with normalization
   rules fixed by the parser contract and tests.
8. Keep `check` read-only, offline, deterministic, and free of repair side effects.
9. Exercise the detector with one pinned DeepTutor-derived fixture and one independent
   Markdown fixture, without repository-specific logic.
10. When historical synchronization cannot be verified, allow a maintainer to record
    current `HEAD` as a new baseline and state that earlier drift was not assessed.

## Later work

- a GitHub Actions integration around the same local, read-only command;
- a reviewed workflow for advancing baselines after human verification;
- machine-readable reports and notifications;
- cross-repository mappings and gettext catalogs;
- optional checks for link, asset, HTML, code-block, or heading parity;
- more sophisticated rename or move matching;
- translation generation, automated edits, or pull-request creation.

## Limitations

- This is a purposive four-case sample, not a survey of all localization tools.
- Repository artifacts show behavior, not maintainer intent; no maintainers were
  interviewed.
- DeepTutor lacks a verified historical marker in the sampled files, so the study
  identifies update windows and structural differences without declaring its prose
  linguistically stale.
- Rust By Example statistics are completeness measurements, not quality scores.
- MDN uses separate repositories and Rust By Example uses PO catalogs. Both are useful
  comparisons but outside v0.1's same-repository Markdown mapping.

## Conclusion

The evidence supports a narrow first release: record a verified source commit per
translation, compare source Markdown history at section granularity, and report review
work without modifying anything. Timestamps, co-edited files, build success, and
direct cross-language structure checks should not substitute for that baseline.
