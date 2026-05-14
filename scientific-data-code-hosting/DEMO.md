# Reviewer Demo

This demo is text-first so reviewers can verify the implementation without
installing screen-recording tools or third-party packages.

## Command

```bash
python scientific-data-code-hosting/demo.py
```

## Expected Output Summary

```text
SCIBASE FAIR artifact capsule demo contains 2 artifacts, FAIR score 1.00, execution ready.
```

The demo then prints a schema.org JSON-LD `Dataset` export with:

- `@id`: `10.0000/scibase-demo-capsule`
- `name`: `SCIBASE FAIR artifact capsule demo`
- `creator`: `SCIBASE reviewer`
- `hasPart`: one Python analysis file and one CSV measurement dataset
- SHA-256 hashes for both artifacts

## What The Demo Proves

- The capsule builder can scan a nested project folder.
- Dataset and code artifacts are classified correctly.
- CSV metadata previews are generated.
- Environment readiness detects `requirements.txt`.
- FAIR scoring reaches 1.00 when required metadata is present.
- JSON-LD metadata can be emitted without external APIs.

## Test Command

```bash
python -m unittest discover scientific-data-code-hosting -v
```

Current local result: 7 tests passed.
