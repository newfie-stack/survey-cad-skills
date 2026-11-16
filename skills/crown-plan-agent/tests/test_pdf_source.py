"""Synthetic-only tests for bounded immutable PDF snapshots."""
import hashlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from pdf_source import read_pdf_snapshot


class PdfSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "synthetic.pdf"
        self.content = b"%PDF-1.4\nSYNTHETIC ONLY\n%%EOF\n"
        self.source.write_bytes(self.content)

    def test_snapshot_contains_exact_bytes_and_lowercase_sha256(self):
        snapshot, digest = read_pdf_snapshot(self.source)
        self.assertIs(type(snapshot), bytes)
        self.assertEqual(snapshot, self.content)
        self.assertEqual(digest, hashlib.sha256(self.content).hexdigest())
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_changed_source_has_a_new_hash_without_mutating_snapshot(self):
        original_snapshot, original_hash = read_pdf_snapshot(self.source)
        replacement = b"%PDF-1.4\nDIFFERENT SYNTHETIC SOURCE\n%%EOF\n"
        self.source.write_bytes(replacement)
        changed_snapshot, changed_hash = read_pdf_snapshot(self.source)
        self.assertEqual(original_snapshot, self.content)
        self.assertEqual(original_hash, hashlib.sha256(self.content).hexdigest())
        self.assertEqual(changed_snapshot, replacement)
        self.assertEqual(changed_hash, hashlib.sha256(replacement).hexdigest())
        self.assertNotEqual(original_hash, changed_hash)

    def test_accepts_case_insensitive_pdf_suffix_and_string_path(self):
        source = self.source.with_suffix(".PDF")
        self.source.rename(source)
        snapshot, _ = read_pdf_snapshot(str(source))
        self.assertEqual(snapshot, self.content)

    def test_rejects_missing_path_directory_and_non_pdf_suffix(self):
        directory = Path(self.temp.name) / "directory.pdf"
        directory.mkdir()
        wrong_suffix = self.source.with_suffix(".txt")
        wrong_suffix.write_bytes(self.content)
        for path in (self.source.with_name("missing.pdf"), directory, wrong_suffix):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "PDF path"):
                read_pdf_snapshot(path)

    def test_rejects_nonpositive_and_noninteger_limits_including_bools(self):
        for limit in (0, -1, True, False, 1.0, "100", None):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "positive integer"):
                read_pdf_snapshot(self.source, max_file_bytes=limit)

    def test_file_size_limit_is_inclusive(self):
        snapshot, _ = read_pdf_snapshot(self.source, max_file_bytes=len(self.content))
        self.assertEqual(snapshot, self.content)
        with self.assertRaisesRegex(ValueError, "size limit"):
            read_pdf_snapshot(self.source, max_file_bytes=len(self.content) - 1)

    def test_rejects_empty_pdf(self):
        self.source.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "[Ee]mpty"):
            read_pdf_snapshot(self.source)

    def test_stale_low_stat_cannot_allow_an_oversized_read(self):
        limit = 8
        self.source.write_bytes(b"%PDF-" + b"x" * 1024)
        original_stat = Path.stat

        def stale_stat(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == self.source:
                fields = list(result)
                fields[6] = 1
                return os.stat_result(fields)
            return result

        class BoundedReader(io.BytesIO):
            def read(self, size=-1):
                if size < 0 or size > limit + 1:
                    raise AssertionError("Snapshot attempted an unbounded read")
                return super().read(size)

        reader = BoundedReader(self.source.read_bytes())
        with patch.object(Path, "stat", stale_stat), patch.object(Path, "open", return_value=reader):
            with self.assertRaisesRegex(ValueError, "size limit"):
                read_pdf_snapshot(self.source, max_file_bytes=limit)


if __name__ == "__main__":
    unittest.main()
