"""Synthetic-only originals and bounded snapshots for revision comparisons."""
from hashlib import sha256
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
try:
    import pymupdf as fitz
except ImportError:
    fitz = None
try:
    import revision_sources
except ModuleNotFoundError as exc:
    if exc.name != "revision_sources":
        raise
    revision_sources = None


class BoundedFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "shared-reference.data"
        self.path.write_bytes(b"abc")

    def read(self, max_bytes=3):
        self.assertIsNotNone(revision_sources, "revision source snapshots are not implemented")
        return revision_sources.read_bounded_file(self.path, max_bytes)

    def test_exact_boundary_snapshot_is_immutable_and_hash_bound(self):
        content, digest = self.read()
        self.path.write_bytes(b"xyz")
        self.assertEqual(content, b"abc")
        self.assertEqual(digest, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertNotEqual(self.read()[1], digest)

    def test_empty_arbitrary_file_is_a_valid_snapshot(self):
        self.path.write_bytes(b"")
        self.assertEqual(self.read(), (b"", sha256(b"").hexdigest()))

    def test_invalid_limits_fail_explicitly(self):
        for limit in (0, -1, True, False, 1.0, "3", None):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "positive integer"):
                self.read(limit)

    def test_missing_file_and_directory_are_rejected(self):
        for path in (self.path.parent, self.path.with_name("missing")):
            with self.subTest(path=path):
                self.path = path
                with self.assertRaisesRegex(ValueError, "[Ff]ile"):
                    self.read()

    def test_oversized_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.read(2)

    def test_stale_stat_cannot_allow_unbounded_or_oversized_read(self):
        self.assertIsNotNone(revision_sources, "revision source snapshots are not implemented")
        original_stat = Path.stat
        source = self.path
        source.write_bytes(b"abcdef")

        def stale_stat(path, *args, **kwargs):
            value = original_stat(path, *args, **kwargs)
            if path == source:
                fields = list(value)
                fields[6] = 1
                return os.stat_result(fields)
            return value

        class GrowingReader(io.BytesIO):
            def read(self, size=-1):
                if size < 1 or size > 4:
                    raise AssertionError("Read must be bounded by remaining allowance plus one")
                return super().read(size)

        reader = GrowingReader(b"abcdef")
        with patch.object(Path, "stat", stale_stat), patch.object(Path, "open", return_value=reader):
            with self.assertRaisesRegex(ValueError, "size limit"):
                self.read(3)
        self.assertEqual(source.read_bytes(), b"abcdef")


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class OriginalPdfTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "original.PDF"
        self.make_pdf()

    def make_pdf(self, *, comment=None, index=None, extras=False, pages=1, encrypted=False):
        with fitz.open() as document:
            for _ in range(pages):
                document.new_page().insert_text((60, 150), "SCALE 1:5000")
            page = document[0]
            if comment:
                note = page.add_text_annot((80, 180), comment.get("content", "Edited commentary"))
                note.set_info(**comment)
                note.update()
            if extras:
                page.insert_text((60, 210), "Company: Crown Plan Agent Consulting")
                page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(60, 240, 180, 260),
                                  "uri": "https://example.invalid/original"})
                widget = fitz.Widget()
                widget.field_name = "source-field"
                widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                widget.field_value = "Original form value"
                widget.rect = fitz.Rect(60, 300, 180, 320)
                page.add_widget(widget)
            if index:
                document.new_page().insert_text((36, 33), index, fontsize=9)
            options = {"encryption": fitz.PDF_ENCRYPT_AES_256, "owner_pw": "owner", "user_pw": "secret"} if encrypted else {}
            document.save(self.path, **options)

    def inspect(self):
        self.assertIsNotNone(revision_sources, "original PDF inspection is not implemented")
        return revision_sources.inspect_original_pdf(self.path)

    def test_normal_renamed_original_has_exact_hash_and_source_inventory(self):
        self.path = self.path.rename(self.path.with_name("renamed-original.pdf"))
        before = self.path.read_bytes()
        result = self.inspect()
        self.assertEqual(result["source_filename"], "renamed-original.pdf")
        self.assertEqual(result["source_sha256"], sha256(before).hexdigest())
        self.assertEqual(result["pages"], 1)
        self.assertEqual([span["text"] for span in result["spans"]], ["SCALE 1:5000"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_source_snapshot_captures_actual_rotation_media_crop_and_display_frames(self):
        with fitz.open() as document:
            page = document.new_page(width=500, height=700)
            page.insert_text((40, 85), "SCALE 1:5000")
            page.set_cropbox(fitz.Rect(10, 20, 490, 680))
            page.set_rotation(90)
            document.save(self.path)
        result = self.inspect()
        self.assertEqual(result.get("page_frames"), [{
            "page": 1, "rotation": 90, "mediabox_points": [0.0, 0.0, 500.0, 700.0],
            "cropbox_points": [10.0, 20.0, 490.0, 680.0],
            "display_rect_points": [0.0, 0.0, 660.0, 480.0]}])
        from pdf_inspector import extract_pdf
        self.assertNotIn("page_frames", extract_pdf(self.path, include_vectors=False))

    def test_ordinary_comments_widgets_uri_and_company_mention_are_allowed(self):
        self.make_pdf(comment={"title": "Surveyor", "subject": "R001: source note",
                               "content": "Popup is not source text"}, extras=True)
        result = self.inspect()
        text = " ".join(span["text"] for span in result["spans"])
        self.assertIn("Company: Crown Plan Agent Consulting", text)
        self.assertNotIn("Popup is not source text", text)

    def test_crown_author_with_unrelated_subject_is_not_a_generated_copy(self):
        self.make_pdf(comment={"title": "Crown Plan Agent", "subject": "Original surveyor note"})
        self.assertEqual(self.inspect()["pages"], 1)

    def test_known_crown_comment_is_rejected_even_with_rewritten_body(self):
        for content in ("Source PDF SHA-256: " + "a" * 64, "Entirely replaced commentary", ""):
            with self.subTest(content=content):
                self.make_pdf(comment={"title": "Crown Plan Agent", "subject": "R001: CANDIDATE-PLAN-SCALE",
                                       "content": content})
                with self.assertRaisesRegex(ValueError, "original"):
                    self.inspect()

    def test_known_appended_index_without_annotations_is_rejected(self):
        self.make_pdf(index="Crown Plan Agent - Review notes 1 of 1\n"
                      "REVIEW_REQUIRED. Derived review copy; not a regulatory certificate.\n"
                      "Source PDF SHA-256: " + "b" * 64)
        with self.assertRaisesRegex(ValueError, "original"):
            self.inspect()

    def test_actual_standard_review_copy_is_recognized_by_each_signature(self):
        from pdf_inspector import extract_pdf
        from pdf_markup import build_annotated_pdf
        from regulatory_catalog import load_candidate_catalog
        from review_pipeline import review_inventory

        catalogue = [entry for entry in load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine/candidate_requirements.json")
            if entry["requirement_id"] == "CANDIDATE-PLAN-SCALE"]
        scenario = {"land_class": "alberta_crown", "regulator": "AER",
                    "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
                    "purpose": "Synthetic purpose", "subactivity": "Synthetic activity"}
        inventory = extract_pdf(self.path, include_vectors=False)
        report = review_inventory(inventory, scenario, catalogue)
        generated, _ = build_annotated_pdf(self.path, report, inventory)
        for signature in ("metadata", "index"):
            with self.subTest(signature=signature), fitz.open(stream=generated, filetype="pdf") as document:
                if signature == "metadata":
                    document.delete_pages(1, document.page_count - 1)
                else:
                    page = document[0]
                    for annotation in list(page.annots() or ()):
                        page.delete_annot(annotation)
                self.path.write_bytes(document.tobytes())
                with self.assertRaisesRegex(ValueError, "original"):
                    self.inspect()

    def test_company_text_and_generic_review_wording_do_not_match_index_signature(self):
        self.make_pdf(index="Crown Plan Agent Consulting\nReview notes for original survey\nSource PDF SHA-256: " + "b" * 64)
        self.assertEqual(self.inspect()["pages"], 2)

    def test_encrypted_invalid_and_empty_pdf_are_rejected(self):
        self.make_pdf(encrypted=True)
        with self.assertRaisesRegex(ValueError, "[Ee]ncrypted"):
            self.inspect()
        for content in (b"not a PDF", b""):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(ValueError):
                    self.inspect()

    def test_too_many_pages_are_rejected_before_extraction(self):
        self.make_pdf(pages=101)
        with self.assertRaisesRegex(ValueError, "[Pp]age limit"):
            self.inspect()

    def test_changed_source_between_detection_and_extraction_fails_binding(self):
        self.assertIsNotNone(revision_sources, "original PDF inspection is not implemented")
        actual_extract = revision_sources.extract_pdf

        def changed_extract(path, **kwargs):
            self.make_pdf(extras=True)
            return actual_extract(path, **kwargs)

        with patch.object(revision_sources, "extract_pdf", side_effect=changed_extract):
            with self.assertRaisesRegex(ValueError, "[Ss]ource.*changed|SHA-256"):
                self.inspect()


if __name__ == "__main__":
    unittest.main()
