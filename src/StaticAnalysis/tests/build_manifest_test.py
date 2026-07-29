#!/usr/bin/env python3
"""Regression tests for the embedded production build manifest."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parent
GENERATOR = SOURCE_ROOT / "scripts" / "generate_embedded_manifest.py"


def load_generator():
    specification = importlib.util.spec_from_file_location(
        "rift_manifest_generator", GENERATOR
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load build-manifest generator")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class BuildManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rift-manifest-test-")
        self.root = Path(self.temporary.name)
        module = load_generator()
        selected = module.selected_files(
            SOURCE_ROOT,
            module.CORE_FILES,
            module.CORE_TREES,
            module.CORE_EXCLUDES,
        ) + module.selected_files(SOURCE_ROOT, (), (module.SCHEMA_TREE,))
        for source in selected:
            destination = self.root / "relocated" / source.relative_to(SOURCE_ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def generate(self, source_root: Path, name: str) -> tuple[bytes, dict[str, object]]:
        header = self.root / name / "manifest.h"
        document = self.root / name / "manifest.json"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--source-root",
                str(source_root),
                "--output-header",
                str(header),
                "--output-json",
                str(document),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return header.read_bytes(), json.loads(document.read_text(encoding="utf-8"))

    def test_relocation_does_not_change_identity(self) -> None:
        first_header, first = self.generate(SOURCE_ROOT, "source")
        second_header, second = self.generate(self.root / "relocated", "copy")
        self.assertEqual(first_header, second_header)
        self.assertEqual(first, second)
        encoded = json.dumps(second, sort_keys=True)
        self.assertNotIn(str(SOURCE_ROOT), encoded)
        self.assertNotIn(str(self.root), encoded)

    def test_core_and_schema_identities_are_separate(self) -> None:
        _, before = self.generate(self.root / "relocated", "before")
        # M5 implementation files must be part of the attested identity, not
        # merely CMake rebuild dependencies.
        core_file = self.root / "relocated" / "core" / "production" / "recipe.cpp"
        core_file.write_bytes(core_file.read_bytes() + b"\n")
        _, core_changed = self.generate(self.root / "relocated", "core-changed")
        self.assertNotEqual(
            before["production_core_sha256"], core_changed["production_core_sha256"]
        )
        self.assertEqual(
            before["schema_bundle_sha256"], core_changed["schema_bundle_sha256"]
        )

        schema_file = self.root / "relocated" / "schema" / "common.schema.json"
        schema_file.write_bytes(schema_file.read_bytes() + b"\n")
        _, schema_changed = self.generate(self.root / "relocated", "schema-changed")
        self.assertEqual(
            core_changed["production_core_sha256"],
            schema_changed["production_core_sha256"],
        )
        self.assertNotEqual(
            core_changed["schema_bundle_sha256"],
            schema_changed["schema_bundle_sha256"],
        )

    def test_file_records_bind_bytes(self) -> None:
        _, manifest = self.generate(SOURCE_ROOT, "records")
        production_paths = {
            record["path"] for record in manifest["production_core_files"]
        }
        self.assertTrue(
            {
                "core/production/model.cpp",
                "core/production/capabilities.cpp",
                "core/production/frontier.cpp",
                "core/production/predicate_occurrence.cpp",
                "core/production/recipe.cpp",
                "core/production/sha256.cpp",
            }.issubset(production_paths)
        )
        self.assertNotIn("core/production/production_smoke.cpp", production_paths)
        self.assertFalse(any("/baselines/" in path for path in production_paths))
        for section in ("production_core_files", "schema_files"):
            for record in manifest[section]:
                self.assertEqual(
                    record["sha256"],
                    hashlib.sha256((SOURCE_ROOT / record["path"]).read_bytes()).hexdigest(),
                )


if __name__ == "__main__":
    unittest.main()
