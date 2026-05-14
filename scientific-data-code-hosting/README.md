# Scientific Data & Code Hosting Capsule

This is a dependency-free milestone for SCIBASE issue #14. It models a
reviewable "artifact capsule" for scientific data/code hosting: every file gets
typed, hashed, previewed, checked against FAIR metadata expectations, and linked
to executable environment readiness.

## What It Covers

- Scalable storage primitives: folder-aware artifact manifests for datasets,
  code, supplementary files, and model files.
- Metadata-aware previews: CSV/TSV table summaries, JSON validity/key summaries,
  code line counts, and media preview flags.
- Versioning and diffing: content hashes for immutable versions plus a tabular
  diff helper for dataset row changes.
- Structured metadata exports: JSON-LD, DataCite-style metadata, and schema.org
  dataset distribution payloads.
- FAIR checks: findable, accessible, interoperable, and reusable checks with a
  reviewer-readable score and findings.
- Executable environments: detection of Dockerfile, environment.yml,
  requirements.txt, or pyproject.toml, plus recommendations when missing.
- Compute triggers: manual run, reproduce-results, and scheduled refresh command
  plans.

## Files

- `artifact_capsule.py` - core capsule builder, FAIR checker, metadata exporters,
  environment readiness checks, and dataset diff logic.
- `demo.py` - creates a temporary sample project and prints a manifest summary
  plus JSON-LD export.
- `DEMO.md` - reviewer-facing command transcript and proof checklist.
- `test_artifact_capsule.py` - unittest coverage for classification, manifests,
  metadata exports, FAIR findings, diffs, summaries, and invalid JSON previews.

## Run Locally

```bash
python scientific-data-code-hosting/demo.py
python -m unittest discover scientific-data-code-hosting -v
```

## Requirement Mapping

| Issue #14 requirement | This milestone |
| --- | --- |
| Support major file types | Classifies datasets, code, media, model, and supplementary files by extension. |
| Folder organization | Builds relative logical paths from nested project folders. |
| Metadata previews | Generates table, JSON, code, media, and binary preview records. |
| Upload versioning/diffing | Stores SHA-256 version records and includes a tabular diff helper. |
| JSON-LD/DataCite/schema.org | `build_metadata_exports()` emits all three payload shapes. |
| FAIR compliance | `evaluate_fair_compliance()` scores findable/access/interoperable/reusable checks. |
| Executable environments | `check_environment_readiness()` detects Dockerfile/env/requirements definitions. |
| Reproduce buttons/triggers | `plan_compute_triggers()` defines run-analysis, reproduce-results, and scheduled-refresh commands. |

## Review Notes

The module is deterministic and does not call external services. It does not
require credentials, cloud storage, Docker daemon access, payment accounts, or
private data. It is designed as a safe first implementation layer that can later
be wired into real upload, DOI, storage, and execution services.
