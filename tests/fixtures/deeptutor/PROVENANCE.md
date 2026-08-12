# DeepTutor fixture provenance

This fixture is a small, offline hybrid based on public material from
[`HKUDS/DeepTutor`](https://github.com/HKUDS/DeepTutor). It uses adapted source
excerpts, a wholly synthetic translation placeholder, and project-authored expected
results. It is not a complete copy of either upstream README.

## Strategy

| Candidate | Evidence retained | Cost or limitation |
| --- | --- | --- |
| Complete upstream files | Maximum source fidelity | Copies unrelated material, enlarges reviews, and makes fixture changes harder to audit |
| Verbatim excerpts | Real headings and prose with a smaller footprint | Still carries derived material and can require surrounding context to be meaningful |
| Fully synthetic files | Small, license-independent, and easy to control | Does not demonstrate behavior on a change observed in a real project |
| Hybrid: adapted source excerpts plus synthetic mapping (selected) | Preserves a real heading rename and direct-body change while keeping translation prose out of scope | Requires explicit transformation records, attribution, and the upstream license |

The hybrid keeps the real-world reason for the fixture without making DeepTutor's
layout or translated content part of the detector contract.

## Upstream snapshots

| Item | Value |
| --- | --- |
| Upstream repository | `https://github.com/HKUDS/DeepTutor` |
| Source path | `README.md` |
| Baseline commit | [`ff8b6a6d80ab5292f25f76b4d88b3d49717d8784`](https://github.com/HKUDS/DeepTutor/blob/ff8b6a6d80ab5292f25f76b4d88b3d49717d8784/README.md) |
| Baseline blob | `2b0dd9abce5e6423ea4ded707f26fffb29407816` |
| Baseline upstream SHA-256 | `3685346a891bb4c37030dd949cff75be913cdf31f282380e17e2dcc542f3ad33` |
| Current commit | [`c9a833f7c37d7e9898e79a345a8b2c9bdddefb61`](https://github.com/HKUDS/DeepTutor/blob/c9a833f7c37d7e9898e79a345a8b2c9bdddefb61/README.md) |
| Current blob | `6f576d1b9ce654e51a20d5b31533479ab02b3df0` |
| Current upstream SHA-256 | `a56bfbb5511448355312e6ef58e496671e94a8c6ec6a9b5e539cbfdec7278d5f` |
| Upstream license | [Apache License 2.0](https://github.com/HKUDS/DeepTutor/blob/ff8b6a6d80ab5292f25f76b4d88b3d49717d8784/LICENSE), blob `ae1dbfc5e74c6c9ebb3e46ea9ea8dde8a4a04ed8` |

The baseline commit also updated DeepTutor's Chinese README. The current commit changed
only the English README; the Chinese blob remained
`185fbfbb233e7c88ee8d3e329e0791a5768e72f1`. This observation motivates the mapping,
but it does not prove that the upstream translation was fully synchronized at either
revision.

## Fixture inventory

| File | Classification | Origin and role |
| --- | --- | --- |
| `baseline.md` | Adapted excerpt | Derived from `README.md` at the baseline commit; SHA-256 `6fbdca625485d5b21fb8978ee4121f2c3a066f7d13ee6e906d5eb07fa59d686e` |
| `current.md` | Adapted excerpt | Derived from `README.md` at the current commit; SHA-256 `8e7b95b1a01c06eb72e3370f90139030428bfc65c78e77c209dcd2383405fbeb` |
| `translation.zh-CN.md` | Synthetic | Project-authored placeholder used only to validate the mapping; SHA-256 `c2c82055ab2b90a395ef0136b15997b68e7819918dadd2fde2c584ff9fe31f08` |
| `expected.toml` | Synthetic | Project-authored normalized Added, Modified, and Deleted paths; SHA-256 `1a9965c85bbdd2c786fec3dd08574439249d886e9977f9c34edaf5e8fa8e5555` |
| `PROVENANCE.md` | Synthetic (project-authored) | This strategy, transformation, attribution, and reproduction record |
| `LICENSE.deeptutor` | Complete license text | Exact copy of the Apache-2.0 file distributed with the selected revisions; blob `ae1dbfc5e74c6c9ebb3e46ea9ea8dde8a4a04ed8`, SHA-256 `cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4` |

Both adapted Markdown files retain the relevant heading hierarchy. Their prose is
shortened, all unrelated sections are omitted, and an adaptation notice is prepended.
The current file preserves the upstream `Option 1 — Install From PyPI` heading while
the baseline uses the earlier `Option 1 — Install DeepTutor` heading. The direct body
under `🚀 Get Started` is also intentionally different. No upstream translated prose
is included.

## Reviewed expectations

The expected paths are stored in `expected.toml` and are stated here for review:

- **Added:** `"DeepTutor: Agent-Native Personalized Tutoring" > "🚀 Get Started" > "Option 1 — Install From PyPI"`
- **Modified:** `"DeepTutor: Agent-Native Personalized Tutoring" > "🚀 Get Started"`
- **Deleted:** `"DeepTutor: Agent-Native Personalized Tutoring" > "🚀 Get Started" > "Option 1 — Install DeepTutor"`

The heading rename is deliberately classified as one deletion and one addition. The
parent is modified because its direct body changes. Translation structure and
formatting are not evaluated.

## Independent fixture result

The sibling [`independent` fixture expectations](../independent/expected.toml) are
wholly synthetic.
It maps `docs/orchard.md` to `translations/fr/manuel.md`, so it does not use a README
path, DeepTutor headings, or a DeepTutor locale convention. The same parser and
detector classify:

- **Added:** `"Orchard Manual" > "Seasonal Care" > "Frost Alerts"`
- **Modified:** `"Orchard Manual" > "Seasonal Care" > "Watering"`
- **Deleted:** `"Orchard Manual" > "Seasonal Care" > "Retired Sprayer"`

`tests/test_fixtures.py` checks both expectation files through the same detector and
runs each mapping through the CLI. The tests use local temporary Git repositories and
do not contact either upstream project.

## License and attribution conclusion

The adapted source material remains under Apache-2.0. This directory includes the
upstream license text in `LICENSE.deeptutor`, identifies both source revisions and
blobs, marks the adapted files as changed, and preserves this relevant upstream notice:

> Copyright 2025 Data Intelligence Lab, The University of Hong Kong

The selected upstream revisions contain no `NOTICE` file. No unresolved license,
attribution, or provenance blocker was identified for including this fixture under the
recorded terms.
