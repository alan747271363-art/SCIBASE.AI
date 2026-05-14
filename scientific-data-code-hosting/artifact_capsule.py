"""Reproducible scientific artifact capsules.

This module is intentionally dependency-free so reviewers can run it in a bare
Python environment. It models the core data/code hosting primitives requested in
issue #14: artifact manifests, FAIR checks, metadata exports, version diffs, and
executable environment readiness.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_EXTENSIONS = {".csv", ".tsv", ".json", ".xlsx", ".parquet"}
CODE_EXTENSIONS = {".py", ".r", ".jl", ".ipynb"}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4", ".mov"}
MODEL_EXTENSIONS = {".pkl", ".joblib", ".pt", ".pth", ".onnx", ".h5"}
ENVIRONMENT_FILES = {
    "Dockerfile",
    "environment.yml",
    "environment.yaml",
    "requirements.txt",
    "pyproject.toml",
}


@dataclass(frozen=True)
class ArtifactVersion:
    version: str
    path: str
    artifact_type: str
    media_type: str
    sha256: str
    size_bytes: int
    preview: dict[str, Any]
    created_at: str


@dataclass
class ArtifactRecord:
    logical_path: str
    tags: list[str] = field(default_factory=list)
    versions: list[ArtifactVersion] = field(default_factory=list)

    @property
    def latest(self) -> ArtifactVersion:
        if not self.versions:
            raise ValueError(f"artifact {self.logical_path!r} has no versions")
        return self.versions[-1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def classify_artifact(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in DATA_EXTENSIONS:
        return "dataset", _media_type_for_suffix(suffix)
    if suffix in CODE_EXTENSIONS:
        return "code", _media_type_for_suffix(suffix)
    if suffix in MEDIA_EXTENSIONS:
        return "supplementary", _media_type_for_suffix(suffix)
    if suffix in MODEL_EXTENSIONS:
        return "model", "application/octet-stream"
    return "supplementary", "application/octet-stream"


def _media_type_for_suffix(suffix: str) -> str:
    return {
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".parquet": "application/vnd.apache.parquet",
        ".py": "text/x-python",
        ".r": "text/x-r",
        ".jl": "text/x-julia",
        ".ipynb": "application/x-ipynb+json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }.get(suffix, "application/octet-stream")


def build_artifact_version(path: Path, root: Path, version: str = "v1") -> ArtifactVersion:
    content = path.read_bytes()
    artifact_type, media_type = classify_artifact(path)
    return ArtifactVersion(
        version=version,
        path=path.relative_to(root).as_posix(),
        artifact_type=artifact_type,
        media_type=media_type,
        sha256=sha256_bytes(content),
        size_bytes=len(content),
        preview=preview_artifact(path, content),
        created_at=utc_now(),
    )


def preview_artifact(path: Path, content: bytes) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        text = content.decode("utf-8", errors="replace")
        rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
        headers = rows[0] if rows else []
        return {
            "kind": "table",
            "headers": headers,
            "row_count": max(len(rows) - 1, 0),
            "column_count": len(headers),
            "sample_rows": rows[1:4],
        }
    if suffix == ".json":
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return {"kind": "json", "valid": False, "error": str(exc)}
        return {
            "kind": "json",
            "valid": True,
            "top_level": type(data).__name__,
            "keys": sorted(data.keys())[:10] if isinstance(data, dict) else [],
        }
    if suffix in CODE_EXTENSIONS:
        text = content.decode("utf-8", errors="replace")
        return {
            "kind": "code",
            "line_count": len(text.splitlines()),
            "entrypoint_hint": "main" in text or "__main__" in text,
        }
    if suffix in MEDIA_EXTENSIONS:
        return {"kind": "media", "thumbnail_ready": suffix != ".mp4"}
    return {"kind": "binary", "preview_available": False}


def build_capsule_manifest(
    root: Path,
    metadata: dict[str, Any],
    *,
    tags_by_path: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    tags_by_path = tags_by_path or {}
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts and path.name not in ENVIRONMENT_FILES
    ]
    artifacts: list[ArtifactRecord] = []
    for file_path in sorted(files):
        relative_path = file_path.relative_to(root).as_posix()
        artifacts.append(
            ArtifactRecord(
                logical_path=relative_path,
                tags=tags_by_path.get(relative_path, []),
                versions=[build_artifact_version(file_path, root)],
            )
        )

    manifest = {
        "schema": "scibase.reproducible-artifact-capsule.v1",
        "generated_at": utc_now(),
        "metadata": metadata,
        "artifacts": [_artifact_to_dict(artifact) for artifact in artifacts],
        "environment": check_environment_readiness(root),
        "compute_triggers": plan_compute_triggers(metadata),
    }
    manifest["fair"] = evaluate_fair_compliance(manifest)
    return manifest


def _artifact_to_dict(record: ArtifactRecord) -> dict[str, Any]:
    return {
        "logical_path": record.logical_path,
        "tags": record.tags,
        "versions": [version.__dict__ for version in record.versions],
    }


def evaluate_fair_compliance(manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = manifest.get("metadata", {})
    artifacts = manifest.get("artifacts", [])
    checks = {
        "findable": bool(metadata.get("identifier") and metadata.get("title")),
        "accessible": bool(metadata.get("access") and metadata.get("license")),
        "interoperable": all(
            "sha256" in artifact["versions"][-1] and "media_type" in artifact["versions"][-1]
            for artifact in artifacts
        ),
        "reusable": bool(metadata.get("license") and metadata.get("creators") and artifacts),
    }
    findings = []
    for key, passed in checks.items():
        if not passed:
            findings.append(f"{key} requirement is incomplete")

    score = round(sum(1 for passed in checks.values() if passed) / len(checks), 2)
    return {"score": score, "checks": checks, "findings": findings}


def check_environment_readiness(root: Path) -> dict[str, Any]:
    present = sorted(file_name for file_name in ENVIRONMENT_FILES if (root / file_name).exists())
    runtime = "container" if "Dockerfile" in present else "language-environment"
    ready = bool(present)
    recommendations = []
    if not present:
        recommendations.append("Add Dockerfile, environment.yml, requirements.txt, or pyproject.toml")
    if "Dockerfile" not in present:
        recommendations.append("Add Dockerfile for one-click reproducible execution")
    return {
        "ready": ready,
        "runtime": runtime if ready else "unknown",
        "definition_files": present,
        "recommendations": recommendations,
    }


def plan_compute_triggers(metadata: dict[str, Any]) -> list[dict[str, str]]:
    base_command = metadata.get("reproduce_command", "python analysis.py")
    return [
        {
            "name": "run-analysis",
            "kind": "manual",
            "command": base_command,
            "purpose": "Run the main analysis once from the capsule environment.",
        },
        {
            "name": "reproduce-results",
            "kind": "review",
            "command": metadata.get("reproduce_command", base_command),
            "purpose": "Re-run the documented workflow during review or publication checks.",
        },
        {
            "name": "scheduled-refresh",
            "kind": "cron",
            "command": metadata.get("refresh_command", base_command),
            "purpose": "Refresh derived outputs for periodically updated datasets.",
        },
    ]


def diff_tabular_versions(old_content: str, new_content: str, delimiter: str = ",") -> dict[str, Any]:
    old_rows = list(csv.reader(old_content.splitlines(), delimiter=delimiter))
    new_rows = list(csv.reader(new_content.splitlines(), delimiter=delimiter))
    old_header = old_rows[0] if old_rows else []
    new_header = new_rows[0] if new_rows else []
    old_body = {tuple(row) for row in old_rows[1:]}
    new_body = {tuple(row) for row in new_rows[1:]}
    return {
        "kind": "table-diff",
        "headers_changed": old_header != new_header,
        "old_row_count": len(old_rows[1:]),
        "new_row_count": len(new_rows[1:]),
        "rows_added": len(new_body - old_body),
        "rows_removed": len(old_body - new_body),
    }


def build_metadata_exports(manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = manifest["metadata"]
    artifacts = manifest["artifacts"]
    creators = metadata.get("creators", [])
    identifier = metadata.get("identifier", "local-capsule")
    keywords = metadata.get("keywords", [])
    title = metadata.get("title", "Untitled scientific artifact capsule")
    description = metadata.get("description", "")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": identifier,
        "name": title,
        "description": description,
        "keywords": keywords,
        "license": metadata.get("license"),
        "creator": [{"@type": "Person", "name": creator} for creator in creators],
        "hasPart": [
            {
                "@type": "DigitalDocument",
                "name": artifact["logical_path"],
                "encodingFormat": artifact["versions"][-1]["media_type"],
                "sha256": artifact["versions"][-1]["sha256"],
            }
            for artifact in artifacts
        ],
    }
    datacite = {
        "identifier": {"identifier": identifier, "identifierType": "DOI" if identifier.startswith("10.") else "UUID"},
        "creators": [{"name": creator} for creator in creators],
        "titles": [{"title": title}],
        "publisher": metadata.get("publisher", "SCIBASE.AI"),
        "publicationYear": metadata.get("publication_year", datetime.now(timezone.utc).year),
        "types": {"resourceTypeGeneral": "Dataset"},
        "descriptions": [{"description": description, "descriptionType": "Abstract"}],
        "subjects": [{"subject": keyword} for keyword in keywords],
    }
    schema_org = {
        "type": "Dataset",
        "name": title,
        "identifier": identifier,
        "isAccessibleForFree": metadata.get("access", "public") == "public",
        "distribution": [
            {
                "contentUrl": artifact["logical_path"],
                "encodingFormat": artifact["versions"][-1]["media_type"],
            }
            for artifact in artifacts
        ],
    }
    return {"json_ld": json_ld, "datacite": datacite, "schema_org": schema_org}


def summarize_capsule(manifest: dict[str, Any]) -> str:
    artifacts = manifest["artifacts"]
    fair = manifest["fair"]
    ready = "ready" if manifest["environment"]["ready"] else "needs environment"
    return (
        f"{manifest['metadata'].get('title', 'Capsule')} contains {len(artifacts)} artifacts, "
        f"FAIR score {fair['score']:.2f}, execution {ready}."
    )
