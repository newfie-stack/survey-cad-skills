"""End-to-end synthetic PDF smoke test. Generates its own document in memory.

No real client plan, fixture PDF, or PDF extraction is committed.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from pdf_inspector import extract_pdf, write_inventory

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class SyntheticPdfIntegrationTests(unittest.TestCase):
    def test_rotated_sheets_keep_text_and_vectors_in_unrotated_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            for rotation in (0, 90, 180, 270):
                with self.subTest(rotation=rotation):
                    path = Path(directory) / f"synthetic-rotation-{rotation}.pdf"
                    with fitz.open() as document:
                        page = document.new_page(width=400, height=600)
                        page.insert_text((250, 540), "SYNTHETIC LABEL", fontsize=10)
                        page.draw_line((240, 550), (350, 550))
                        page.set_rotation(rotation)
                        document.save(str(path))
                    result = extract_pdf(path)
                    span = result["spans"][0]
                    self.assertEqual(span["text"], "SYNTHETIC LABEL")
                    self.assertEqual(span["page_size_points"], [400.0, 600.0])
                    self.assertEqual(span["bbox_points"][0], 250.0)
                    self.assertGreater(span["bbox_points"][1], 500)
                    self.assertEqual(span["text_direction"], [1.0, 0.0])
                    self.assertEqual(result["vectors"][0]["endpoints_points"],
                                     [240.0, 550.0, 350.0, 550.0])
                    self.assertEqual(extract_pdf(path, include_vectors=False)["spans"],
                                     result["spans"])

    def test_nonzero_cropbox_origin_keeps_crop_relative_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            for rotation in (0, 90, 270):
                with self.subTest(rotation=rotation):
                    path = Path(directory) / f"synthetic-crop-{rotation}.pdf"
                    with fitz.open() as document:
                        page = document.new_page(width=500, height=700)
                        page.insert_text((140, 550), "SYNTHETIC LABEL", fontsize=10)
                        page.draw_line((135, 560), (235, 560))
                        page.set_cropbox(fitz.Rect(100, 100, 400, 600))
                        page.set_rotation(rotation)
                        document.save(str(path))
                    result = extract_pdf(path)
                    span = result["spans"][0]
                    self.assertEqual(span["page_size_points"], [300.0, 500.0])
                    self.assertEqual(span["bbox_points"][0], 40.0)
                    self.assertGreater(span["bbox_points"][1], 400)
                    self.assertLess(span["bbox_points"][3], 500)
                    self.assertEqual(result["vectors"][0]["endpoints_points"],
                                     [35.0, 460.0, 135.0, 460.0])

    def test_user_unit_scaled_rotated_sheets_keep_pdf_point_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            for rotation in (0, 90, 270):
                with self.subTest(rotation=rotation):
                    path = Path(directory) / f"synthetic-scaled-{rotation}.pdf"
                    with fitz.open() as document:
                        page = document.new_page(width=400, height=600)
                        page.insert_text((250, 540), "SYNTHETIC LABEL", fontsize=10)
                        document.xref_set_key(page.xref, "UserUnit", "2")
                        page.set_rotation(rotation)
                        document.save(str(path))
                    span = extract_pdf(path, include_vectors=False)["spans"][0]
                    self.assertEqual(span["page_size_points"], [800.0, 1200.0])
                    self.assertEqual(span["bbox_points"][0], 500.0)
                    self.assertGreater(span["bbox_points"][1], 1000)
                    self.assertNotIn("original_bbox_points", span)

    def test_edge_clipped_labels_keep_visible_bounds_and_original_provenance(self):
        cases = (("left", (-2, 20), 0), ("top", (20, 5), 0),
                 ("right", (399, 100), 90), ("bottom", (20, 599), 0))
        with tempfile.TemporaryDirectory() as directory:
            for edge, position, text_rotation in cases:
                with self.subTest(edge=edge):
                    path = Path(directory) / f"synthetic-edge-{edge}.pdf"
                    with fitz.open() as document:
                        page = document.new_page(width=400, height=600)
                        page.insert_text(position, "SYNTHETIC EDGE", fontsize=10,
                                         rotate=text_rotation)
                        document.save(str(path))
                    with fitz.open(path) as document:
                        blocks = document[0].get_text("dict")["blocks"]
                        original = next(span["bbox"] for block in blocks
                                        for line in block.get("lines", [])
                                        for span in line["spans"])
                    result = extract_pdf(path, include_vectors=False)
                    self.assertEqual(len(result["spans"]), 1)
                    span = result["spans"][0]
                    self.assertEqual(span["text"], "SYNTHETIC EDGE")
                    self.assertEqual(span["original_bbox_points"], list(original))
                    self.assertEqual(span["bbox_points"],
                                     [max(0, original[0]), max(0, original[1]),
                                      min(400, original[2]), min(600, original[3])])

    def test_text_only_inventory_skips_vector_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-dense.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((50, 50), "SYNTHETIC LABEL")
                page.draw_line((30, 100), (50, 100))
                page.draw_line((30, 120), (50, 120))
                document.save(str(path))
            with self.assertRaisesRegex(ValueError, "Vector line limit"):
                extract_pdf(path, max_spans=1)
            result = extract_pdf(path, max_spans=1, include_vectors=False)
            self.assertEqual(result["status"], "TEXT_INVENTORY_ONLY")
            self.assertEqual(result["spans"][0]["text"], "SYNTHETIC LABEL")
            self.assertEqual(result["vectors"], [])
            self.assertEqual(result["curves"], [])

    def test_generate_extract_page_coordinates_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-crown-test.pdf"
            document = fitz.open()
            page = document.new_page(width=612, height=792)
            page.insert_text((50, 100), "SYNTHETIC SKETCH PLAN", fontsize=12)
            page.insert_text((50, 125), "SCALE 1:5000", fontsize=10)
            page.draw_line((100, 200), (200, 200), width=1)
            shape = page.new_shape()
            shape.draw_bezier(fitz.Point(100, 250), fitz.Point(130, 250),
                              fitz.Point(170, 300), fitz.Point(200, 300))
            shape.finish()
            shape.commit()
            document.save(str(path))
            document.close()
            inventory = extract_pdf(path)
            self.assertEqual(inventory["pages"], 1)
            self.assertEqual(inventory["status"], "TEXT_AND_VECTOR_INVENTORY_ONLY")
            self.assertGreaterEqual(len(inventory["vectors"]), 1)
            self.assertGreaterEqual(len(inventory["curves"]), 1)
            self.assertEqual(inventory["curves"][0]["role"], "UNCLASSIFIED_GRAPHIC")
            self.assertEqual(inventory["vectors"][0]["role"], "UNCLASSIFIED_GRAPHIC")
            self.assertEqual(inventory["vectors"][0]["page"], 1)
            labels = {item["text"] for item in inventory["spans"]}
            self.assertIn("SYNTHETIC SKETCH PLAN", labels)
            self.assertIn("SCALE 1:5000", labels)
            self.assertTrue(all(item["page"] == 1 for item in inventory["spans"]))
            self.assertTrue(all(0 <= item["bbox_points"][0] < 612 for item in inventory["spans"]))
            output = Path(directory) / "inventory.json"
            write_inventory(inventory, output)
            self.assertTrue(output.is_file())
            with self.assertRaises(FileExistsError):
                write_inventory(inventory, output)

    def test_inventory_contract_after_vector_extension(self):
        """Prevent text-only status regressions after adding PDF vectors."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((30, 50), "SYNTHETIC PLAN")
            page.draw_line((30, 90), (90, 90))
            document.save(str(path))
            document.close()
            result = extract_pdf(path)
            self.assertEqual(result["status"], "TEXT_AND_VECTOR_INVENTORY_ONLY")
            self.assertTrue(result["spans"])
            self.assertTrue(result["vectors"])
            self.assertTrue(all(x["role"] == "UNCLASSIFIED_GRAPHIC" for x in result["vectors"]))
            self.assertIn("No regulatory compliance determination", result["limitations"])

    def test_reject_file_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(str(path))
            doc.close()
            with self.assertRaisesRegex(ValueError, "file size"):
                extract_pdf(path, max_file_bytes=1)

    def test_reject_cumulative_curve_limit_across_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            doc = fitz.open()
            for _ in range(2):
                page = doc.new_page()
                shape = page.new_shape()
                shape.draw_bezier(fitz.Point(10,10), fitz.Point(20,10),
                                  fitz.Point(30,40), fitz.Point(40,40))
                shape.finish()
                shape.commit()
            doc.save(str(path))
            doc.close()
            with self.assertRaisesRegex(ValueError, "Curve limit"):
                extract_pdf(path, max_spans=1)

    def test_reject_boolean_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(str(path))
            doc.close()
            with self.assertRaises(ValueError):
                extract_pdf(path, max_pages=True)

    def test_reject_page_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.new_page()
            doc.save(str(path))
            doc.close()
            with self.assertRaises(ValueError):
                extract_pdf(path, max_pages=1)


if __name__ == "__main__":
    unittest.main()
