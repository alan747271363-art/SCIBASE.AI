from __future__ import annotations

import json
import tempfile
from pathlib import Path

from artifact_capsule import build_capsule_manifest, build_metadata_exports, summarize_capsule


def create_demo_project(root: Path) -> None:
    (root / "data").mkdir()
    (root / "analysis").mkdir()
    (root / "data" / "measurements.csv").write_text(
        "sample,temperature_c,signal\nA,21.2,0.84\nB,22.0,0.91\n",
        encoding="utf-8",
    )
    (root / "analysis" / "analysis.py").write_text(
        "print('Reproducing SCIBASE demo analysis')\n",
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("numpy>=1.26\npandas>=2.2\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        create_demo_project(root)
        manifest = build_capsule_manifest(
            root,
            {
                "identifier": "10.0000/scibase-demo-capsule",
                "title": "SCIBASE FAIR artifact capsule demo",
                "description": "Small reproducible data/code package for issue #14 review.",
                "creators": ["SCIBASE reviewer"],
                "keywords": ["FAIR", "reproducibility", "data hosting"],
                "license": "MIT",
                "access": "public",
                "reproduce_command": "python analysis/analysis.py",
            },
            tags_by_path={"data/measurements.csv": ["temperature", "instrument-output"]},
        )
        exports = build_metadata_exports(manifest)
        print(summarize_capsule(manifest))
        print(json.dumps(exports["json_ld"], indent=2))


if __name__ == "__main__":
    main()
