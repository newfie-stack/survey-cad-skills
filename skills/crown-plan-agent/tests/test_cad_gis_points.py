"""Actual invented CSV bytes are compared; native CAD and acceptance stay open."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from cad_gis_points import compare_point_export, validate_point_export_spec


class PointExportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "invented-export.csv"
        self.content = ("point_id,easting,northing,type\n"
                        "1,500000.00,6100000.00,OC\n"
                        "2,500010.00,6100000.00,EC\n")
        self.path.write_text(self.content, encoding="utf-8")
        declarations = {"crs_identifier": "INVENTED_PROJECTED_METRIC",
                        "coordinate_units": "m", "coordinate_frame_id": "INVENTED_GRID_EPOCH",
                        "crs_verified": True, "provenance_verified": True,
                        "coordinate_roles_resolved": True, "complete": True}
        self.spec = {**declarations, "schema_version": 1,
                     "format": "CSV_POINT_EXPORT", "origin_kind": "CAD",
                     "source_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest()}
        self.table = {**declarations, "source_sha256": "a" * 64, "rows": [
            {"point_id": "1", "easting": "500000.00", "northing": "6100000.00",
             "type": "OC", "source_locator": {"page": 1, "detail": "invented row1"}},
            {"point_id": "2", "easting": "500010.00", "northing": "6100000.00",
             "type": "EC", "source_locator": {"page": 1, "detail": "invented row2"}}]}

    def write_export(self, content):
        self.path.write_bytes(content.encode("utf-8"))
        self.spec["source_sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def codes(self, result):
        return [f["reason_code"] for f in result["findings"]]

    def test_actual_bound_bytes_agree_without_native_cad_or_regulatory_clearance(self):
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "PASS")
        self.assertEqual(result["regulatory_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["execution_status"], "EXECUTED")
        self.assertEqual(result["source_sha256"], self.spec["source_sha256"])
        self.assertEqual(result["plan_source_sha256"], self.table["source_sha256"])
        self.assertEqual(result["counts"], {"export_rows": 2, "table_rows": 2,
                                          "matched_ids": 2, "compared_points": 2})
        self.assertIn("native CAD/GIS", " ".join(result["limitations"]))

    def test_gis_origin_is_preserved(self):
        self.spec["origin_kind"] = "GIS"
        self.assertEqual(compare_point_export(self.path, self.spec, self.table)["origin_kind"], "GIS")

    def test_original_coordinate_strings_survive_exact_numeric_comparison(self):
        self.write_export(self.content.replace("500010.00", "500010.000000"))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "PASS")
        self.assertEqual(result["comparisons"][1]["export"]["easting"], "500010.000000")
        self.assertEqual(result["comparisons"][1]["table"]["easting"], "500010.00")
        self.assertEqual(result["comparisons"][1]["table"]["source_locator"],
                         self.table["rows"][1]["source_locator"])

    def test_changed_actual_bytes_cannot_reuse_expected_hash(self):
        self.path.write_text(self.content.replace("500010.00", "500011.00"))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            compare_point_export(self.path, self.spec, self.table)

    def test_coordinate_difference_is_reported_without_rounding_or_tolerance(self):
        self.write_export(self.content.replace("500010.00", "500010.000001"))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "FAIL")
        self.assertIn("COORDINATES_DIFFER", self.codes(result))
        self.assertEqual(result["comparisons"][1]["delta_easting"], "0.000001")

    def test_type_difference_is_reported_independently(self):
        self.write_export(self.content.replace(",EC\n", ",RC\n"))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "FAIL")
        self.assertIn("POINT_TYPE_DIFFERS", self.codes(result))

    def test_complete_set_missing_and_extra_ids_are_explicit(self):
        self.write_export(self.content.replace("2,500010", "3,500010"))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "FAIL")
        self.assertEqual(set(self.codes(result)), {"MISSING_EXPORT_POINT", "EXTRA_EXPORT_POINT"})

    def test_duplicate_export_id_remains_unresolved_instead_of_picking_first(self):
        self.write_export(self.content + "2,500011.00,6100000.00,EC\n")
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
        self.assertIn("DUPLICATE_EXPORT_POINT_ID", self.codes(result))
        self.assertEqual(result["counts"]["compared_points"], 0)

    def test_duplicate_table_id_remains_unresolved(self):
        self.table["rows"].append(copy.deepcopy(self.table["rows"][1]))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
        self.assertIn("DUPLICATE_TABLE_POINT_ID", self.codes(result))

    def test_zero_padded_ids_are_not_silently_joined(self):
        self.write_export(self.content.replace("2,500010", "02,500010"))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
        self.assertIn("POINT_ID_UNRESOLVED", self.codes(result))

    def test_invalid_ids_and_coordinate_lexemes_are_unresolved(self):
        for field, value in [("point_id", "2a"), ("point_id", "2.0"),
                             ("easting", "5e5"), ("easting", "NaN"),
                             ("easting", "=1+1"), ("northing", "6 100 000.00")]:
            with self.subTest(field=field, value=value):
                table = copy.deepcopy(self.table)
                table["rows"][1][field] = value
                result = compare_point_export(self.path, self.spec, table)
                self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
                self.assertEqual(result["counts"]["compared_points"], 0)

    def test_all_verification_and_completeness_gates_apply_to_both_sides(self):
        for side in ("spec", "table"):
            for field in ("crs_verified", "provenance_verified", "coordinate_roles_resolved", "complete"):
                with self.subTest(side=side, field=field):
                    spec, table = copy.deepcopy(self.spec), copy.deepcopy(self.table)
                    (spec if side == "spec" else table)[field] = False
                    result = compare_point_export(self.path, spec, table)
                    self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
                    self.assertEqual(result["counts"]["compared_points"], 0)

    def test_crs_identifier_difference_is_not_transformed_or_compared(self):
        self.spec["crs_identifier"] = "DIFFERENT_INVENTED_CRS"
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertIn("CRS_MISMATCH", self.codes(result))
        self.assertEqual(result["counts"]["compared_points"], 0)

    def test_optional_frame_identity_must_agree_when_supplied(self):
        self.spec["coordinate_frame_id"] = "grid-epoch-A"
        self.table["coordinate_frame_id"] = "ground-epoch-A"
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertIn("COORDINATE_FRAME_UNRESOLVED", self.codes(result))
        self.assertEqual(result["counts"]["compared_points"], 0)

    def test_missing_frame_or_metric_units_cannot_be_compared(self):
        for side in ("spec", "table"):
            for field, value in (("coordinate_frame_id", None), ("coordinate_units", None)):
                with self.subTest(side=side, field=field):
                    spec, table = copy.deepcopy(self.spec), copy.deepcopy(self.table)
                    (spec if side == "spec" else table)[field] = value
                    result = compare_point_export(self.path, spec, table)
                    self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
                    self.assertEqual(result["counts"]["compared_points"], 0)

    def test_unresolved_native_table_cells_do_not_abort_export_review(self):
        for field in ("point_id", "easting", "northing", "type"):
            with self.subTest(field=field):
                table = copy.deepcopy(self.table)
                table["rows"][1][field] = None
                table["complete"] = False
                result = compare_point_export(self.path, self.spec, table)
                self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
                self.assertEqual(result["counts"]["compared_points"], 0)

    def test_boolean_declarations_do_not_accept_truthy_strings(self):
        self.spec["complete"] = "true"
        with self.assertRaises(ValueError):
            compare_point_export(self.path, self.spec, self.table)

    def test_malformed_hash_and_missing_metadata_are_rejected(self):
        for field, value in [("source_sha256", "bad"), ("origin_kind", "DWG"),
                             ("format", "NATIVE_DWG"), ("crs_identifier", "")]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    compare_point_export(self.path, {**self.spec, field: value}, self.table)

    def test_non_csv_binary_and_invalid_utf8_are_rejected(self):
        self.path.write_bytes(b"\xff\x00\x11")
        self.spec["source_sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            compare_point_export(self.path, self.spec, self.table)

    def test_exact_header_and_column_count_are_required(self):
        for content in [self.content.replace("point_id", "id", 1),
                        self.content.replace("point_id,easting,northing,type", "point_id,easting,easting,type"),
                        self.content.replace("2,500010.00,6100000.00,EC", "2,500010.00,EC"),
                        self.content + '3,"500.00,6100000.00,EC\n']:
            with self.subTest(content=content):
                self.write_export(content)
                with self.assertRaises(ValueError):
                    compare_point_export(self.path, self.spec, self.table)

    def test_empty_sets_cannot_pass(self):
        self.write_export("point_id,easting,northing,type\n")
        self.table["rows"] = []
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual(result["mechanical_status"], "REVIEW_REQUIRED")
        self.assertIn("POINT_SET_EMPTY", self.codes(result))

    def test_utf8_bom_and_quoted_fields_are_read_from_actual_csv(self):
        self.write_export("\ufeff" + self.content.replace("500010.00", '"500010.00"'))
        self.assertEqual(compare_point_export(self.path, self.spec, self.table)["mechanical_status"], "PASS")

    def test_size_and_row_bounds_are_enforced(self):
        self.path.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
        self.spec["source_sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "size"):
            compare_point_export(self.path, self.spec, self.table)
        self.write_export("point_id,easting,northing,type\n" + "1,1,1,OC\n" * 10001)
        with self.assertRaisesRegex(ValueError, "row"):
            compare_point_export(self.path, self.spec, self.table)

    def test_inputs_and_returned_locator_data_are_independent(self):
        before = copy.deepcopy((self.spec, self.table))
        result = compare_point_export(self.path, self.spec, self.table)
        self.assertEqual((self.spec, self.table), before)
        result["comparisons"][0]["table"]["source_locator"]["page"] = 99
        self.assertEqual(self.table["rows"][0]["source_locator"]["page"], 1)

    def test_spec_preflight_is_strict_and_never_reads_a_file(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("file read during preflight")):
            result = validate_point_export_spec(self.spec)
        self.assertEqual(result, self.spec)
        result["complete"] = False
        self.assertTrue(self.spec["complete"])
        for changed in ({**self.spec, "unexpected": "field"},
                        {k: v for k, v in self.spec.items() if k != "coordinate_frame_id"},
                        {**self.spec, "schema_version": True}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_point_export_spec(changed)


if __name__ == "__main__":
    unittest.main()
