from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from artifact_capsule import (
    build_capsule_manifest,
    build_metadata_exports,
    classify_artifact,
    diff_tabular_versions,
    summarize_capsule,
)


class ArtifactCapsuleTests(unittest.TestCase):
    def make_project(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "data").mkdir()
        (root / "notebooks").mkdir()
        (root / "data" / "observations.csv").write_text(
            "id,value\nobs-1,4.2\nobs-2,5.1\n",
            encoding="utf-8",
        )
        (root / "notebooks" / "reproduce.py").write_text(
            "def main():\n    return 'ok'\n",
            encoding="utf-8",
        )
        (root / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
        return root

    def metadata(self) -> dict[str, object]:
        return {
            "identifier": "10.1234/scibase.capsule",
            "title": "Reproducible sensor study",
            "description": "A tiny reproducible capsule used by tests.",
            "creators": ["Ada Lovelace", "Grace Hopper"],
            "keywords": ["sensor", "FAIR"],
            "license": "MIT",
            "access": "public",
            "reproduce_command": "python notebooks/reproduce.py",
        }

    def test_classifies_data_and_code_files(self) -> None:
        self.assertEqual(classify_artifact(Path("table.csv")), ("dataset", "text/csv"))
        self.assertEqual(classify_artifact(Path("workflow.py")), ("code", "text/x-python"))

    def test_build_manifest_hashes_artifacts_and_scores_fair(self) -> None:
        root = self.make_project()
        manifest = build_capsule_manifest(root, self.metadata())
        self.assertEqual(manifest["schema"], "scibase.reproducible-artifact-capsule.v1")
        self.assertEqual(len(manifest["artifacts"]), 2)
        self.assertEqual(manifest["fair"]["score"], 1.0)
        self.assertTrue(manifest["environment"]["ready"])
        first_version = manifest["artifacts"][0]["versions"][0]
        self.assertEqual(len(first_version["sha256"]), 64)

    def test_metadata_exports_include_artifact_distribution(self) -> None:
        manifest = build_capsule_manifest(self.make_project(), self.metadata())
        exports = build_metadata_exports(manifest)
        self.assertEqual(exports["json_ld"]["@type"], "Dataset")
        self.assertEqual(exports["datacite"]["identifier"]["identifierType"], "DOI")
        self.assertEqual(len(exports["schema_org"]["distribution"]), 2)

    def test_fair_findings_report_missing_metadata(self) -> None:
        manifest = build_capsule_manifest(self.make_project(), {"title": "Partial"})
        findings = manifest["fair"]["findings"]
        self.assertLess(manifest["fair"]["score"], 1.0)
        self.assertIn("accessible requirement is incomplete", findings)

    def test_tabular_diff_counts_added_and_removed_rows(self) -> None:
        old_csv = "id,value\nobs-1,4.2\nobs-2,5.1\n"
        new_csv = "id,value\nobs-2,5.1\nobs-3,7.3\n"
        diff = diff_tabular_versions(old_csv, new_csv)
        self.assertEqual(diff["rows_added"], 1)
        self.assertEqual(diff["rows_removed"], 1)
        self.assertFalse(diff["headers_changed"])

    def test_summary_is_reviewer_readable(self) -> None:
        manifest = build_capsule_manifest(self.make_project(), self.metadata())
        summary = summarize_capsule(manifest)
        self.assertIn("Reproducible sensor study", summary)
        self.assertIn("FAIR score 1.00", summary)

    def test_json_preview_marks_invalid_json(self) -> None:
        root = self.make_project()
        (root / "data" / "broken.json").write_text("{bad json", encoding="utf-8")
        manifest = build_capsule_manifest(root, self.metadata())
        json_artifact = next(a for a in manifest["artifacts"] if a["logical_path"] == "data/broken.json")
        self.assertFalse(json_artifact["versions"][0]["preview"]["valid"])


if __name__ == "__main__":
    unittest.main()
