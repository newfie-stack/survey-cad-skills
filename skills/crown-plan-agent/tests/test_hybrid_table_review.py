"""Invented native PDF tables exercise bounded clause observations, not compliance."""
import copy
import hashlib
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime


class HybridTableReviewTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("hybrid_table_review")
        self.runtime = load_pdf_runtime()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "invented-hybrid.pdf"

    def make(self, rows=None, *, complete=True, raster=False, rotate=False, native_rotation=0, labels=False):
        rows = rows or [("1", "6000000.00", "500000.00", "OC"),
                        ("2", "6001000.00", "500000.00", "OC"),
                        ("3", "6000000.00", "510000.00", "EC")]
        regions = []
        with self.runtime.open() as document:
            page = document.new_page(width=700, height=700)
            for index, values in enumerate(rows):
                record = {}
                y = 65 + index * 35
                for field, x, text in zip(("point_id", "northing", "easting", "type"),
                                          (40, 140, 320, 500), values):
                    def transform(px, py):
                        return {0: (px, py), 90: (py, 700-px),
                                180: (700-px, 700-py), 270: (700-py, px)}[native_rotation]
                    label = {"point_id": "ID:", "northing": "N:", "easting": "E:", "type": "T:"}[field]
                    if text:
                        page.insert_text(transform(x, y), (label + " " if labels else "") + text,
                                         fontsize=10, rotate=native_rotation)
                    left, top = transform(x-5, y-15)
                    right, bottom = transform(x+155 if field in {"northing", "easting"} else x+60, y+5)
                    record[field] = {"page": 1, "bbox_points": [min(left,right), min(top,bottom), max(left,right), max(top,bottom)],
                                     "role": "invented " + field}
                    if labels:
                        record[field]["label"] = label
                regions.append(record)
            if raster:
                tile = page.get_pixmap(clip=self.runtime.Rect(620, 600, 630, 610))
                page.insert_image(self.runtime.Rect(145, 53, 155, 63), pixmap=tile)
            if rotate:
                page.set_rotation(90)
            document.save(self.pdf)
        return {"schema_version": 1, "source_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                "prepared_by": "Invented table author", "table_complete": ({
                    "status": "TEXT_COMPLETE", "method": "VISUAL_TO_TEXT_COMPARISON",
                    "reviewer": "Invented fixture author", "statement": "All invented table rows and fields reviewed."} if complete else None),
                "crs_identifier": "EPSG:26912", "crs_verified": True,
                "coordinate_frame_id": "invented NAD83 UTM12 grid XY", "coordinate_units": "m",
                "provenance_verified": True, "coordinate_roles_resolved": True, "rows": regions}

    def review(self, spec):
        before = self.pdf.read_bytes()
        original = copy.deepcopy(spec)
        result = self.module.review_hybrid_table(self.pdf, spec)
        self.assertEqual(self.pdf.read_bytes(), before)
        self.assertEqual(spec, original)
        self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(result["source_sha256"], spec["source_sha256"])
        self.assertEqual(len(result["findings"]), 7)
        return {row["check_id"]: row for row in result["findings"]}, result

    def test_clean_full_native_table_and_exact_ten_km_boundary(self):
        findings, result = self.review(self.make())
        self.assertEqual({row["mechanical_status"] for row in findings.values()}, {"PASS"})
        self.assertTrue(result["table"]["complete"])
        self.assertEqual(result["table"]["rows"][2]["easting"], "510000.00")
        locator = result["table"]["rows"][2]["source_locator"]
        self.assertEqual(locator["source_sha256"], result["source_sha256"])
        self.assertEqual(locator["fields"]["easting"]["page"], 1)
        self.assertIn("510000.00", locator["fields"]["easting"]["text"])
        self.assertEqual(findings["C_3_5_6_3_01"]["execution_status"], "EXECUTED")

    def test_one_centimetre_beyond_ten_km_fails(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC"),
                                             ("3", "6000000.00", "510000.01", "RC")]))
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "FAIL")

    def test_spatial_comparison_accepts_one_centimetre_inside(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC"),
                                             ("3", "6000000.00", "509999.99", "XC")]))
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "PASS")

    def test_gap_duplicate_and_suffix_point_numbers_fail_sequence(self):
        for ids in (("1", "3", "4"), ("1", "2", "2"), ("1", "2A", "3"), ("1", "2.1", "3")):
            with self.subTest(ids=ids):
                spec = self.make([(ids[0], "6000000.00", "500000.00", "OC"),
                                  (ids[1], "6001000.00", "500000.00", "OC"),
                                  (ids[2], "6000000.00", "510000.00", "EC")])
                findings, _ = self.review(spec)
                self.assertEqual(findings["C_3_5_2_1_02"]["mechanical_status"], "FAIL")

    def test_start_number_failure_is_distinct_from_sequential_order(self):
        findings, _ = self.review(self.make([("2", "6000000.00", "500000.00", "OC"),
                                             ("3", "6001000.00", "500000.00", "OC")]))
        self.assertEqual(findings["C_3_5_2_1_01"]["mechanical_status"], "FAIL")

    def test_spec_cannot_reorder_a_printed_out_of_sequence_table_to_pass(self):
        spec = self.make([("1", "6000000.00", "500000.00", "OC"),
                          ("3", "6001000.00", "500000.00", "OC"),
                          ("2", "6000000.00", "510000.00", "EC")])
        spec["rows"] = [spec["rows"][0], spec["rows"][2], spec["rows"][1]]
        findings, _ = self.review(spec)
        self.assertEqual(findings["C_3_5_2_1_02"]["mechanical_status"], "FAIL")

    def test_cross_row_coordinate_pairing_cannot_fabricate_oc_locations(self):
        spec = self.make()
        first, third = spec["rows"][0], spec["rows"][2]
        for field in ("northing", "easting"):
            first[field], third[field] = third[field], first[field]
        findings, result = self.review(spec)
        self.assertEqual({r["mechanical_status"] for r in findings.values()}, {"REVIEW_REQUIRED"})
        self.assertFalse(result["table"]["complete"])

    def test_coordinate_precision_and_grouping_are_distinct_findings(self):
        findings, _ = self.review(self.make([("1", "6,000,000.00", "500000.0", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC")]))
        self.assertEqual(findings["C_3_5_2_2_01"]["mechanical_status"], "FAIL")
        self.assertEqual(findings["C_3_5_2_2_02"]["mechanical_status"], "FAIL")
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "REVIEW_REQUIRED")

    def test_space_grouping_cannot_pass(self):
        findings, _ = self.review(self.make([("1", "6 000 000.00", "500000.00", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC")]))
        self.assertEqual(findings["C_3_5_2_2_02"]["mechanical_status"], "FAIL")

    def test_unrecognized_category_fails_lexical_check_but_blocks_spatial(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC"),
                                             ("3", "6000000.00", "510000.00", "CP")]))
        self.assertEqual(findings["C_3_5_2_3_01"]["mechanical_status"], "FAIL")
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "REVIEW_REQUIRED")

    def test_duplicate_oc_coordinates_do_not_count_as_two(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "OC"),
                                             ("2", "6000000.00", "500000.00", "OC"),
                                             ("3", "6000010.00", "500000.00", "EC")]))
        self.assertEqual(findings["C_3_5_6_2_01"]["mechanical_status"], "FAIL")

    def test_no_oc_does_not_vacuously_pass_distance(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "EC")]))
        self.assertEqual(findings["C_3_5_6_2_01"]["mechanical_status"], "FAIL")
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "REVIEW_REQUIRED")

    def test_no_governing_coordinates_does_not_vacuously_pass_distance(self):
        findings, _ = self.review(self.make([("1", "6000000.00", "500000.00", "OC"),
                                             ("2", "6001000.00", "500000.00", "OC")]))
        self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "REVIEW_REQUIRED")

    def test_incomplete_table_cannot_pass_or_fail_collective_checks(self):
        findings, result = self.review(self.make(complete=False))
        self.assertEqual({row["mechanical_status"] for row in findings.values()}, {"REVIEW_REQUIRED"})
        self.assertFalse(result["table"]["complete"])

    def test_blank_raster_clipped_ambiguous_and_reused_fields_block_all(self):
        for kind in ("blank", "raster", "clip", "ambiguous", "reuse"):
            with self.subTest(kind=kind):
                spec = self.make(raster=kind == "raster")
                if kind == "blank":
                    spec["rows"][0]["type"]["bbox_points"] = [600, 600, 650, 650]
                elif kind == "clip":
                    spec["rows"][0]["northing"]["bbox_points"][2] = 145
                elif kind == "ambiguous":
                    spec["rows"][0]["northing"]["bbox_points"][3] = 110
                elif kind == "reuse":
                    spec["rows"][1]["northing"] = copy.deepcopy(spec["rows"][0]["northing"])
                findings, result = self.review(spec)
                self.assertEqual({row["mechanical_status"] for row in findings.values()}, {"REVIEW_REQUIRED"})
                self.assertFalse(result["table"]["complete"])

    def test_metric_crs_frame_provenance_and_role_gates_block_counts_and_distance(self):
        for name, value in (("crs_identifier", None), ("crs_verified", False),
                            ("coordinate_frame_id", None), ("coordinate_units", None),
                            ("provenance_verified", False), ("coordinate_roles_resolved", False)):
            with self.subTest(name=name):
                spec = self.make()
                spec[name] = value
                findings, _ = self.review(spec)
                self.assertEqual(findings["C_3_5_6_2_01"]["mechanical_status"], "REVIEW_REQUIRED")
                self.assertEqual(findings["C_3_5_6_3_01"]["mechanical_status"], "REVIEW_REQUIRED")
                self.assertEqual(findings["C_3_5_2_1_01"]["mechanical_status"], "PASS")

    def test_rotated_page_keeps_source_location_and_reads_native_table(self):
        findings, result = self.review(self.make(rotate=True))
        self.assertEqual({row["mechanical_status"] for row in findings.values()}, {"PASS"})
        self.assertEqual(result["table"]["rows"][0]["source_locator"]["fields"]["point_id"]["page"], 1)

    def test_native_tables_in_all_cardinal_directions_read_in_their_own_source_order(self):
        for angle in (90, 180, 270):
            with self.subTest(angle=angle):
                findings, result = self.review(self.make(native_rotation=angle, labels=True))
                self.assertEqual({row["mechanical_status"] for row in findings.values()}, {"PASS"})
                self.assertEqual([r["point_id"] for r in result["table"]["rows"]], ["1", "2", "3"])

    def test_synthetic_span_joining_cannot_create_a_grouping_failure(self):
        spec = self.make()
        # Replace one source field with two adjacent native spans. The reader
        # cannot establish literal printed spacing solely from its span join.
        with self.runtime.open(self.pdf) as document:
            page = document[0]
            page.add_redact_annot(self.runtime.Rect(135, 50, 295, 70), fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_text((140, 65), "6000", fontsize=10)
            page.insert_text((162.24, 65), "000.00", fontsize=11)
            changed = document.tobytes()
        self.pdf.write_bytes(changed)
        spec["source_sha256"] = hashlib.sha256(changed).hexdigest()
        findings, _ = self.review(spec)
        self.assertEqual({r["mechanical_status"] for r in findings.values()}, {"REVIEW_REQUIRED"})

    def test_wrong_source_digest_is_rejected(self):
        spec = self.make()
        spec["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.module.review_hybrid_table(self.pdf, spec)

    def test_changed_source_during_review_is_rejected(self):
        spec = self.make()
        real = self.module.read_pdf_snapshot
        count = 0
        def changed(path):
            nonlocal count
            count += 1
            data, digest = real(path)
            return data, "0" * 64 if count > 1 else digest
        with patch.object(self.module, "read_pdf_snapshot", side_effect=changed):
            with self.assertRaises(ValueError):
                self.module.review_hybrid_table(self.pdf, spec)

    def test_strict_schema_rejects_unknown_keys_bad_flags_and_bounds(self):
        original = self.make()
        mutations = [lambda s: s.update(extra=True),
                     lambda s: s.update(crs_verified=1),
                     lambda s: s.update(coordinate_units="ft"),
                     lambda s: s.update(rows=[]),
                     lambda s: s.update(rows=s["rows"] * 200),
                     lambda s: s["rows"][0].update(text="invented assertion"),
                     lambda s: s["rows"][0]["type"].update(coverage_review=s["table_complete"]),
                     lambda s: s["rows"][0]["type"].update(page=True),
                     lambda s: s["rows"][0]["type"].update(bbox_points=[0, 0, float("inf"), 2]),
                     lambda s: s["table_complete"].update(status="ASSUMED_COMPLETE")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                spec = copy.deepcopy(original)
                mutation(spec)
                with self.assertRaises(ValueError):
                    self.module.validate_hybrid_spec(spec)

    def test_outside_page_and_nonexistent_page_rejected(self):
        for field in ({"page": 2}, {"bbox_points": [0, 0, 999, 999]}):
            spec = self.make()
            spec["rows"][0]["type"].update(field)
            with self.assertRaises(ValueError):
                self.module.review_hybrid_table(self.pdf, spec)


if __name__ == "__main__":
    unittest.main()
