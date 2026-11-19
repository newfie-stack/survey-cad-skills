"""Native rotated-text acceptance using wholly invented PDFs, not client plans."""
from __future__ import annotations

import copy
import hashlib
import math
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_review import review_finished_plan


class RotatedNativeTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "invented-rotated-text.pdf"
        self.document = fitz.open()
        self.addCleanup(self.document.close)

    def page(self):
        return self.document.new_page(width=1000, height=1000)

    def text(self, page, text, *, angle=90, x=0, y=0, font="helv", origin=(400, 400)):
        # Source construction only: x/y are an invented note's reading axes.
        radians = math.radians(angle)
        c, s = math.cos(radians), math.sin(radians)
        point = fitz.Point(origin[0] + c * x + s * y,
                           origin[1] - s * x + c * y)
        page.insert_text(point, text, fontsize=10, fontname=font,
                         morph=(point, fitz.Matrix(angle)))

    def region(self, page=1, box=None, label=None, complete=False):
        result = {"page": page, "bbox_points": box or [0, 0, 1000, 1000],
                  "role": "invented source field"}
        if label is not None:
            result["label"] = label
        if complete:
            result["coverage_review"] = {
                "status": "TEXT_COMPLETE", "method": "VISUAL_TO_TEXT_COMPARISON",
                "reviewer": "invented fixture author",
                "statement": "Invented fixture only; this complete source field is represented."
            }
        return result

    def check(self, kind="required_text", regions=None, **kwargs):
        return {"id": "invented", "kind": kind, "description": "Read invented source text",
                "basis": "Invented drafting comparison, not a regulatory requirement",
                "regions": regions or [self.region()], **kwargs}

    def review(self, checks):
        self.document.save(self.pdf)
        original = self.pdf.read_bytes()
        spec = {"schema_version": 1, "source_sha256": hashlib.sha256(original).hexdigest(),
                "prepared_by": "invented fixture author", "checks": checks}
        original_spec = copy.deepcopy(spec)
        report = review_finished_plan(self.pdf, spec)
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertEqual(spec, original_spec)
        self.assertEqual(report["source_sha256"], spec["source_sha256"])
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["regulatory_status"], "NOT_ASSESSED")
        return report

    def test_native_text_is_read_at_cardinal_and_oblique_angles(self):
        checks = []
        for index, angle in enumerate((0, 90, 180, 270, 35, 45, 135), 1):
            self.text(self.page(), "DISTANCES ARE IN METRES", angle=angle)
            checks.append({**self.check(regions=[self.region(index)],
                                        expected="DISTANCES ARE IN METRES"), "id": f"angle-{angle}"})
        report = self.review(checks)
        for row in report["findings"]:
            with self.subTest(angle=row["check_id"]):
                self.assertEqual(row["status"], "PASS")
                self.assertIn("DISTANCES ARE IN METRES", row["evidence"][0]["text"])
                self.assertEqual(row["evidence"][0]["bbox_points"], [0, 0, 1000, 1000])

    def test_split_fonts_and_wrapped_lines_follow_the_reading_direction(self):
        checks = []
        for angle in (90, 180, 270, 35):
            page = self.page()
            self.text(page, "DISTANCES ARE", angle=angle, font="hebo")
            next_x = fitz.get_text_length("DISTANCES ARE ", fontname="hebo", fontsize=10)
            self.text(page, "IN METRES", angle=angle, x=next_x)
            checks.append({**self.check(regions=[self.region(len(self.document))],
                                        expected="DISTANCES ARE IN METRES"), "id": f"split-{angle}"})
            page = self.page()
            self.text(page, "DISTANCES ARE", angle=angle)
            self.text(page, "IN METRES", angle=angle, y=15)
            checks.append({**self.check(regions=[self.region(len(self.document))],
                                        expected="DISTANCES ARE IN METRES"), "id": f"wrapped-{angle}"})
        for row in self.review(checks)["findings"]:
            with self.subTest(case=row["check_id"]):
                self.assertEqual(row["status"], "PASS")

    def test_scale_identifiers_and_decimal_sum_read_rotated_fields(self):
        checks = []
        for angle in (90, 180, 270, 35):
            first = len(self.document) + 1
            for text in ("SCALE 1:5000", "SUBJECT: LOT 7", "SUBJECT: LOT 8",
                         "PART A: 0.100 ha", "PART B: 0.200 ha", "TOTAL: 0.301 ha"):
                self.text(self.page(), text, angle=angle)
            checks += [
                {**self.check("scale", [self.region(first)], expected_denominator=5000),
                 "id": f"scale-{angle}"},
                {**self.check("same_text", [self.region(first + 1, label="SUBJECT:"),
                                           self.region(first + 2, label="SUBJECT:")]),
                 "id": f"identity-{angle}"},
                {**self.check("decimal_sum", [self.region(first + 3, label="PART A:"),
                                             self.region(first + 4, label="PART B:"),
                                             self.region(first + 5, label="TOTAL:")],
                              unit="ha", tolerance="0.000"), "id": f"sum-{angle}"}]
        for row in self.review(checks)["findings"]:
            with self.subTest(case=row["check_id"]):
                if row["kind"] == "scale":
                    self.assertEqual(row["status"], "PASS")
                    self.assertEqual(row["observed"], [5000])
                elif row["kind"] == "same_text":
                    self.assertEqual(row["status"], "FAIL")
                    self.assertEqual(row["observed"], ["LOT 7", "LOT 8"])
                else:
                    self.assertEqual(row["status"], "FAIL")
                    self.assertEqual(row["difference"], "0.001")

    def test_page_rotation_and_crop_do_not_change_source_region_coordinates(self):
        checks = []
        cases = ((90, 270, 1, [0, 0, 750, 780]),
                 (35, 90, 1, [0, 0, 750, 780]),
                 (270, 180, 2, [0, 0, 1500, 1560]))
        for index, (text_angle, page_angle, user_unit, box) in enumerate(cases, 1):
            page = self.page()
            self.text(page, "DISTANCES ARE IN METRES", angle=text_angle)
            page.set_cropbox(fitz.Rect(100, 120, 850, 900))
            self.document.xref_set_key(page.xref, "UserUnit", str(user_unit))
            page.set_rotation(page_angle)
            checks.append({**self.check(regions=[self.region(index, box)],
                                        expected="DISTANCES ARE IN METRES"), "id": f"page-{index}"})
        for row, case in zip(self.review(checks)["findings"], cases):
            self.assertEqual(row["status"], "PASS")
            self.assertEqual(row["evidence"][0]["bbox_points"], case[3])

    def test_oblique_separate_rows_do_not_become_a_wrapped_phrase(self):
        page = self.page()
        self.text(page, "DISTANCES ARE", angle=35)
        self.text(page, "IN METRES", angle=35, y=55)
        row = self.review([self.check(expected="DISTANCES ARE IN METRES")])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_normal_leading_does_not_turn_wrapped_notes_into_missing_text_failures(self):
        checks = []
        for angle in (0, 90, 180, 270, 35):
            for leading in (10, 12, 13):
                page = self.page()
                self.text(page, "DISTANCES ARE", angle=angle)
                self.text(page, "IN METRES", angle=angle, y=leading)
                checks.append({**self.check(
                    regions=[self.region(len(self.document), complete=True)],
                    expected="DISTANCES ARE IN METRES"), "id": f"leading-{angle}-{leading}"})
        for row in self.review(checks)["findings"]:
            with self.subTest(case=row["check_id"]):
                self.assertEqual(row["status"], "PASS")

    def test_nonuniform_oblique_font_geometry_cannot_join_separate_rows(self):
        checks = []
        for angle in (35, 45, 135):
            page = self.document.new_page(width=5000, height=5000)
            origin = fitz.Point(2500, 2500)
            matrix = fitz.Matrix(10, 0.05) * fitz.Matrix(angle)
            page.insert_text(origin, "DISTANCES ARE", fontsize=10, morph=(origin, matrix))
            page.insert_text((2580, 2555), "IN METRES", fontsize=10, morph=(origin, matrix))
            checks.append({**self.check(
                regions=[self.region(len(self.document), [0, 0, 5000, 5000])],
                expected="DISTANCES ARE IN METRES"), "id": f"affine-{angle}"})
        for row in self.review(checks)["findings"]:
            with self.subTest(case=row["check_id"]):
                self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_mixed_and_opposite_directions_cannot_fabricate_one_phrase(self):
        checks = []
        for index, (first, second) in enumerate(((0, 90), (90, 270), (0, 180)), 1):
            page = self.page()
            self.text(page, "DISTANCES ARE", angle=first)
            self.text(page, "IN METRES", angle=second, origin=(400, 300))
            checks.append({**self.check(regions=[self.region(index)],
                                        expected="DISTANCES ARE IN METRES"), "id": f"directions-{index}"})
        for row in self.review(checks)["findings"]:
            self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_distant_same_angle_columns_do_not_become_one_phrase(self):
        page = self.page()
        self.text(page, "DISTANCES ARE", angle=35, origin=(250, 450))
        self.text(page, "IN METRES", angle=35, x=400, origin=(250, 450))
        row = self.review([self.check(expected="DISTANCES ARE IN METRES")])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_partially_selected_rotated_text_remains_unresolved(self):
        page = self.page()
        self.text(page, "DISTANCES ARE IN METRES", angle=35)
        row = self.review([self.check(regions=[self.region(box=[400, 0, 1000, 1000], complete=True)],
                                      expected="DISTANCES ARE IN METRES")])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")
        self.assertIn("Clipped", row["reason"])

    def test_page_edge_clipped_rotated_text_remains_unresolved(self):
        self.text(self.page(), "DISTANCES ARE IN METRES", angle=90, origin=(999, 400))
        row = self.review([self.check(regions=[self.region(complete=True)],
                                      expected="DISTANCES ARE IN METRES")])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")
        self.assertIn("Clipped", row["reason"])

    def test_raster_overlap_still_blocks_a_native_rotated_match(self):
        page = self.page()
        raster = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 4, 4))
        raster.clear_with(255)
        page.insert_image(fitz.Rect(300, 300, 600, 500), stream=raster.tobytes("png"))
        self.text(page, "DISTANCES ARE IN METRES", angle=35)
        row = self.review([self.check(regions=[self.region(complete=True)],
                                      expected="DISTANCES ARE IN METRES")])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")
        self.assertIn("Raster", row["reason"])

    def test_rotated_absence_needs_the_existing_completeness_declaration(self):
        self.text(self.page(), "OTHER PRINTED NOTE", angle=90)
        checks = [{**self.check(regions=[self.region(complete=complete)],
                                expected="DISTANCES ARE IN METRES"), "id": str(complete)}
                  for complete in (False, True)]
        rows = self.review(checks)["findings"]
        self.assertEqual([row["status"] for row in rows], ["REVIEW_REQUIRED", "FAIL"])

    def test_overlapping_regions_cannot_reuse_one_rotated_observation(self):
        self.text(self.page(), "SUBJECT: LOT 7", angle=35)
        row = self.review([self.check("same_text", [self.region(label="SUBJECT:"),
                           self.region(box=[50, 50, 950, 950], label="SUBJECT:")])])["findings"][0]
        self.assertEqual(row["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
