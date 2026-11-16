"""Synthetic source-package tests; no project files or account metadata."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib


SKILL_ROOT = Path(__file__).resolve().parents[1]
BUILDER = SKILL_ROOT / "tools" / "build_chatgpt_plugin.py"
PROMPTS = [
    "Review my Alberta Crown land plan and explain what needs attention.",
    "Run the Crown Plan Agent synthetic example.",
    "List the evidence missing from this plan review.",
]


def synthetic_png(width=256, height=256, compressed_data=None):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    pixels = b"\x00" + b"\x00\x00\x00\x00" * width
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(pixels * height) if compressed_data is None else compressed_data)
            + chunk(b"IEND", b""))


class ChatGPTPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="crown-package-test-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / "repository" / "skills" / "crown-plan-agent"
        self.root.mkdir(parents=True)
        self.output = self.folder / "release.zip"
        (self.root.parents[1] / "LICENSE").write_text("MIT License\nSynthetic packaging fixture.\n")
        self.write("SKILL.md", "---\nname: crown-plan-agent\ndescription: Use when reviewing an invented plan.\nversion: 0.4.0\n---\n# Fixture\nSee [note](references/note.md).\n")
        self.write("requirements.txt", "PyMuPDF>=1.24,<2\n")
        self.write("engine/review.py", "STATUS = 'REVIEW_REQUIRED'\n")
        self.write("references/note.md", "# Invented evidence\n")
        self.write("tests/test_runtime.py", "# Synthetic runtime test fixture\n")
        self.write("agents/openai.yaml", "interface:\n  display_name: Crown Plan Agent\n  short_description: Review Crown land plans\n")
        self.template = self.root / "packaging/chatgpt"
        self.write("packaging/chatgpt/README.md", "# ChatGPT package\nSee [skill](skills/crown-plan-agent/SKILL.md).\n")
        self.interface = {
            "displayName": "Crown Plan Agent", "shortDescription": "Review Crown land plans",
            "developerName": "newfie-stack", "category": "Productivity", "capabilities": [],
            "defaultPrompt": list(PROMPTS), "brandColor": "#174D3C", "brandColorDark": "#E4C675",
            "logo": "./assets/light.png", "composerIcon": "./assets/light.png",
            "logoDark": "./assets/dark.png", "composerIconDark": "./assets/dark.png",
        }
        self.manifest = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "crown-plan-agent-chatgpt", "version": "0.4.0",
            "description": "Synthetic packaging fixture", "author": {"name": "newfie-stack"},
            "license": "MIT", "extensions": {"com.openai": {"interface": self.interface}},
        }
        self.save_manifest()
        for name in ("light.png", "dark.png"):
            p = self.template / "assets" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(synthetic_png())

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def save_manifest(self):
        self.write("packaging/chatgpt/plugin.json", json.dumps(self.manifest, indent=2) + "\n")

    def builder(self):
        self.assertTrue(BUILDER.is_file(), "The reproducible ChatGPT build tool is missing")
        spec = importlib.util.spec_from_file_location("crown_test_package_builder", BUILDER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build_plugin_archive

    def build(self, output=None):
        return self.builder()(self.root, output or self.output)

    def test_repeated_builds_are_identical_and_preserve_canonical_content(self):
        result = self.build()
        other = self.folder / "other-name.zip"
        self.build(other)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())
        self.assertEqual(result["archive_sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        with zipfile.ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())
            prefix = "crown-plan-agent-chatgpt/"
            self.assertTrue(all(name.startswith(prefix) for name in archive.namelist()))
            self.assertEqual(archive.read(prefix + "skills/crown-plan-agent/SKILL.md"),
                             (self.root / "SKILL.md").read_bytes())
            stored = json.loads(archive.read(prefix + "plugin.json"))
            self.assertEqual(stored["extensions"]["com.openai"]["interface"]["defaultPrompt"], PROMPTS)
            self.assertEqual(archive.read(prefix + "assets/dark.png"),
                             (self.template / "assets/dark.png").read_bytes())
            self.assertIn(prefix + "LICENSE", archive.namelist())

    def test_source_change_changes_archive_fingerprint(self):
        first = self.build()["archive_sha256"]
        self.write("engine/review.py", "STATUS = 'REVIEW_REQUIRED'\n# Reviewed source change\n")
        second = self.build(self.folder / "changed.zip")["archive_sha256"]
        self.assertNotEqual(first, second)

    def test_version_mismatch_creates_no_archive(self):
        self.manifest["version"] = "0.3.1"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "version"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_missing_icon_creates_no_archive(self):
        (self.template / "assets/dark.png").unlink()
        with self.assertRaisesRegex(ValueError, "asset|icon"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_non_square_icon_is_rejected(self):
        (self.template / "assets/dark.png").write_bytes(synthetic_png(256, 128))
        with self.assertRaisesRegex(ValueError, "square|dimensions"):
            self.build()

    def test_symlinked_runtime_file_is_rejected(self):
        outside = self.folder / "outside.txt"
        outside.write_text("Not approved source")
        (self.root / "engine/linked.py").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
            self.build()

    def test_symlinked_runtime_directory_is_rejected(self):
        outside = self.folder / "outside"
        outside.mkdir()
        (self.root / "tests/linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
            self.build()

    def test_pdf_cad_and_image_artifacts_are_rejected_in_runtime_source(self):
        for name in ("tests/unapproved.pdf", "engine/unapproved.dxf", "references/unapproved.png"):
            with self.subTest(name=name):
                path = self.write(name, "Unexpected source artifact")
                with self.assertRaisesRegex(ValueError, "[Uu]nexpected|[Ff]orbidden"):
                    self.build()
                path.unlink()
                self.assertFalse(self.output.exists())

    def test_output_must_be_outside_skill_source(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.build(self.root / "release.zip")
        self.assertFalse((self.root / "release.zip").exists())

    def test_existing_output_is_never_overwritten(self):
        self.output.write_bytes(b"Keep existing release")
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(self.output.read_bytes(), b"Keep existing release")

    def test_asset_traversal_is_rejected(self):
        self.interface["logo"] = "../outside.png"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "asset|contained|path"):
            self.build()

    def test_unresolved_relative_reference_is_rejected(self):
        self.write("references/note.md", "See [unavailable](missing.md).\n")
        with self.assertRaisesRegex(ValueError, "[Mm]arkdown|reference|target"):
            self.build()

    def test_normalized_account_author_cannot_enter_public_template(self):
        self.manifest["author"]["email"] = "synthetic-account@example.invalid"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "author|account"):
            self.build()

    def test_duplicate_manifest_keys_are_rejected(self):
        self.write("packaging/chatgpt/plugin.json", '{"name":"one", "name":"two"}')
        with self.assertRaisesRegex(ValueError, "[Dd]uplicate"):
            self.build()

    def test_known_development_files_are_not_in_runtime_package(self):
        self.write("tools/build_chatgpt_plugin.py", "# Development tool\n")
        self.write("tests/test_chatgpt_packaging.py", "# Development packaging test\n")
        self.write("engine/__pycache__/generated.pyc", "Ignored cache")
        self.build()
        with zipfile.ZipFile(self.output) as archive:
            names = archive.namelist()
            self.assertFalse(any("/tools/" in name or "/packaging/" in name or "__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith("test_chatgpt_packaging.py") for name in names))
            self.assertTrue(any(name.endswith("tests/test_runtime.py") for name in names))

    def test_unexpected_source_directory_is_rejected(self):
        self.write("private-review/notes.md", "Not runtime source")
        with self.assertRaisesRegex(ValueError, "[Uu]nexpected"):
            self.build()

    def test_unreferenced_symlinked_asset_directory_is_rejected(self):
        outside = self.folder / "outside-icons"
        outside.mkdir()
        (self.template / "assets/linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
            self.build()

    def test_invalid_numeric_prerelease_version_is_rejected(self):
        self.manifest["version"] = "0.4.0-01"
        self.save_manifest()
        text = (self.root / "SKILL.md").read_text().replace("version: 0.4.0", "version: 0.4.0-01")
        self.write("SKILL.md", text)
        with self.assertRaisesRegex(ValueError, "version|semantic"):
            self.build()

    def test_nonstring_license_metadata_is_rejected(self):
        self.manifest["license"] = {"unreviewed": "metadata"}
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "license|metadata"):
            self.build()

    def test_crc_correct_png_with_invalid_compressed_pixels_is_rejected(self):
        (self.template / "assets/dark.png").write_bytes(synthetic_png(compressed_data=b"This is not a zlib stream"))
        with self.assertRaisesRegex(ValueError, "PNG|pixel"):
            self.build()

    def test_png_with_wrong_decompressed_row_length_is_rejected(self):
        (self.template / "assets/dark.png").write_bytes(synthetic_png(compressed_data=zlib.compress(b"\x00")))
        with self.assertRaisesRegex(ValueError, "PNG|pixel"):
            self.build()

    def test_unresolved_reference_style_markdown_target_is_rejected(self):
        self.write("references/note.md", "[Unavailable guide][missing]\n\n[missing]: missing-guide.md\n")
        with self.assertRaisesRegex(ValueError, "Markdown|reference|target"):
            self.build()


if __name__ == "__main__":
    unittest.main()
