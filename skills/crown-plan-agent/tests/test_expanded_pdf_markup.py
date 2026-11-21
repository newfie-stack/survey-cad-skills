"""Actual review copies preserve actionable bounded checks and original sources."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))
from runtime_security import load_pdf_runtime
from pdf_inspector import extract_pdf
from pdf_markup import build_annotated_pdf
from pdf_markup_plan import build_markup_plan
from finished_plan_review import review_finished_plan
from review_pipeline import review_inventory
from cad_gis_points import compare_point_export


class ExpandedPDFMarkupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "invented-plan.pdf"
        self.runtime = load_pdf_runtime()
        self.make_pdf()

    def make_pdf(self, *, rotation=0, crop=False):
        if self.pdf.exists():
            self.pdf.unlink()
        with self.runtime.open() as doc:
            page = doc.new_page(width=600, height=800)
            page.insert_text((100, 130), "MAIN SCALE 1:2500", fontsize=12)
            page.insert_text((100, 200), "APPLICANT: INVENTED PLAN LTD.", fontsize=12)
            page.insert_text((100, 260), "AREA: 2.00 ha", fontsize=12)
            page.insert_text((100, 320), "RETAINED: 1.00 ha", fontsize=12)
            for x, value in ((100, "1"), (200, "500000.00"), (320, "6000000.00"), (450, "OC")):
                page.insert_text((x, 400), value, fontsize=12)
            if crop:
                page.set_cropbox(self.runtime.Rect(40, 60, 550, 720))
            page.set_rotation(rotation)
            doc.save(self.pdf)
        self.inventory = extract_pdf(self.pdf, include_vectors=False)
        self.sha = sha256(self.pdf.read_bytes()).hexdigest()
        self.report = review_inventory(self.inventory, {
            "land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC",
            "stage": "initial", "plan_type": "sketch", "purpose": "Invented", "subactivity": ""}, [])
        self.report["review_summary"] = {}

    def span(self, prefix):
        return next(s for s in self.inventory["spans"] if s["text"].startswith(prefix))

    def evidence(self, prefix):
        span = self.span(prefix)
        return {"page": span["page"], "bbox_points": list(span["bbox_points"]),
                "text": span["text"], "spans": [{k: deepcopy(v) for k, v in span.items()
                                                if k not in {"page", "page_size_points"}}]}

    def field(self, prefix, *, source_id="plan", source_kind="PLAN", digest=None):
        evidence = self.evidence(prefix)
        evidence.update(source_id=source_id, source_kind=source_kind,
                        source_sha256=digest or self.sha)
        return {"source_id": source_id, "source_sha256": digest or self.sha,
                "semantic_role": "applicant", "raw_value": evidence["text"], "evidence": evidence}

    def job(self, findings):
        return {"assessment_scope": "JOB_RECORD_AND_BALANCE_QA", "plan_source_sha256": self.sha,
                "overall_status": "REVIEW_REQUIRED", "findings": findings}

    def job_finding(self, identifier="applicant_form", **changes):
        finding = {"check_id": identifier, "kind": "applicant_name", "workbook_check_id": "C_1_2_2_1_02",
                   "assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE", "mechanical_status": "FAIL",
                   "execution_status": "EXECUTED", "status": "REVIEW_REQUIRED",
                   "reason": "The selected applicant differs from the supplied application form.",
                   "residual_review": "Confirm current records and the intended applicant.",
                   "evidence": [self.field("APPLICANT:")], "observed": ["INVENTED PLAN LTD.", "INVENTED FORM LTD."]}
        finding.update(changes)
        return finding

    def plan(self):
        return build_markup_plan(self.report, self.inventory, source_sha256=self.sha)

    def test_finished_failure_becomes_individual_note_and_printable_pdf_entry(self):
        span = self.span("MAIN SCALE")
        region = {"page": 1, "bbox_points": list(span["bbox_points"]), "role": "main plan scale"}
        # Include a small boundary margin so native support is fully selected.
        region["bbox_points"] = [v + d for v, d in zip(region["bbox_points"], [-1, -1, 1, 1])]
        spec = {"schema_version": 1, "source_sha256": self.sha, "prepared_by": "Invented reviewer", "checks": [
            {"id": "scale_job_expectation", "kind": "scale", "description": "Main scale comparison",
             "basis": "Invented job expects 1:5000", "expected_denominator": 5000, "regions": [region]}]}
        self.report["finished_plan_review"] = review_finished_plan(self.pdf, spec)
        before = self.pdf.read_bytes()
        data, manifest = build_annotated_pdf(self.pdf, self.report, self.inventory)
        notes = manifest["notes"]
        self.assertEqual(len(notes), 1)
        self.assertIn("scale_job_expectation", notes[0]["finding_id"])
        self.assertEqual(notes[0]["status"], "REVIEW_REQUIRED")
        self.assertIn("Mechanical result: FAIL", notes[0]["body"])
        self.assertIn("Expected: 5000", notes[0]["body"])
        self.assertEqual(notes[0]["anchor"], {"page": 1, "bbox_points": list(span["bbox_points"])})
        with self.runtime.open(stream=data, filetype="pdf") as doc:
            self.assertEqual(len(list(doc[0].annots())), 1)
            index = "\n".join(p.get_text() for p in list(doc)[1:])
            self.assertIn("scale_job_expectation", index)
            self.assertIn("not regulatory", index)
        self.assertEqual(self.pdf.read_bytes(), before)

    def test_job_plan_field_gets_marker_while_reference_locations_stay_context(self):
        reference = self.field("APPLICANT:", source_id="form", source_kind="APPLICATION_FORM", digest="1" * 64)
        finding = self.job_finding(evidence=[self.field("APPLICANT:"), reference])
        self.report["job_record_review"] = self.job([finding])
        note = self.plan()["notes"][0]
        self.assertEqual(note["anchor"]["bbox_points"], self.span("APPLICANT:")["bbox_points"])
        self.assertIn("form", note["body"])
        self.assertIn("C_1_2_2_1_02", note["body"])
        self.assertIn("INVENTED FORM LTD.", note["body"])
        finding["evidence"] = [reference]
        unlocated = self.plan()["notes"][0]
        self.assertIsNone(unlocated["anchor"])
        self.assertIsNone(unlocated["evidence_page"])

    def test_wrong_hash_or_wrong_source_role_cannot_borrow_plan_coordinates(self):
        for mutation in ("field_hash", "evidence_hash", "role", "source_id"):
            field = self.field("APPLICANT:")
            if mutation == "field_hash": field["source_sha256"] = "1" * 64
            if mutation == "evidence_hash": field["evidence"]["source_sha256"] = "1" * 64
            if mutation == "role": field["evidence"]["source_kind"] = "APPLICATION_FORM"
            if mutation == "source_id": field["evidence"]["source_id"] = "form"
            self.report["job_record_review"] = self.job([self.job_finding(evidence=[field])])
            with self.subTest(mutation=mutation):
                self.assertIsNone(self.plan()["notes"][0]["anchor"])

    def test_nested_stale_report_bindings_abort(self):
        for key, report in (("job_record_review", self.job([self.job_finding()])),
                            ("finished_plan_review", {"assessment_scope": "DRAWING_QC_ONLY", "source_sha256": "1" * 64,
                                                      "overall_status": "REVIEW_REQUIRED", "findings": []}),
                            ("regulatory_evidence_review", {"assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE",
                                                           "source_sha256": "1" * 64, "overall_status": "REVIEW_REQUIRED", "observations": []})):
            stale = deepcopy(report)
            if key == "job_record_review": stale["plan_source_sha256"] = "1" * 64
            with self.subTest(key=key):
                self.report[key] = stale
                with self.assertRaises(ValueError): self.plan()
                self.report.pop(key)

    def test_blocked_and_multiple_plan_locations_stay_complete_in_index(self):
        blocked = self.job_finding("missing_registry", mechanical_status="REVIEW_REQUIRED", execution_status="BLOCKED",
                                   evidence=[], reason="The client registry record is missing.")
        multiple = self.job_finding("area_balance", kind="parts_total", workbook_check_id=None,
                                    evidence=[self.field("AREA:"), self.field("RETAINED:")])
        passed = self.job_finding("clean_comparison", mechanical_status="PASS")
        self.report["job_record_review"] = self.job([blocked, multiple, passed])
        data, manifest = build_annotated_pdf(self.pdf, self.report, self.inventory)
        self.assertEqual(len(manifest["notes"]), 2)
        self.assertEqual(manifest["located_count"], 0)
        with self.runtime.open(stream=data, filetype="pdf") as doc:
            index = "\n".join(p.get_text() for p in list(doc)[1:])
            self.assertIn("missing_registry", index)
            self.assertIn("area_balance", index)
            self.assertNotIn("clean_comparison", index)

    def test_regulatory_alias_deduplicates_finished_finding_and_preserves_question(self):
        drawing = {"check_id": "territory_phrase", "kind": "required_text", "status": "FAIL",
                   "description": "Candidate territory phrase", "reason": "Expected phrase absent.",
                   "evidence": [self.evidence("MAIN SCALE")], "correction": "Review alternative wording."}
        self.report["finished_plan_review"] = {"assessment_scope": "DRAWING_QC_ONLY", "source_sha256": self.sha,
                                               "overall_status": "REVIEW_REQUIRED", "regulatory_status": "NOT_ASSESSED",
                                               "findings": [drawing]}
        self.report["regulatory_evidence_review"] = {
            "assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE", "source_sha256": self.sha,
            "overall_status": "REVIEW_REQUIRED", "observations": [
                {"workbook_check_id": "C_1_3_3_5_01", "status": "REVIEW_REQUIRED", "mechanical_status": "REVIEW_REQUIRED",
                 "execution_status": "EXECUTED", "reason": "Exact wording is not prescribed.",
                 "evidence": drawing["evidence"], "drawing_finding": deepcopy(drawing),
                 "residual_review": "Review alternative territory wording."}]}
        notes = self.plan()["notes"]
        self.assertEqual(len(notes), 1)
        self.assertIn("C_1_3_3_5_01", notes[0]["body"])
        self.assertIn("Clause observation: REVIEW_REQUIRED", notes[0]["body"])
        self.assertIn("Mechanical result: FAIL", notes[0]["body"])

    def test_hybrid_nested_source_fields_and_distinct_causes_preserve_accounting(self):
        locator = {"source_sha256": self.sha, "fields": {"northing": self.evidence("AREA:")}}
        observations = []
        for identifier in ("C_3_5_2_2_01", "C_3_5_2_2_02"):
            observations.append({"workbook_check_id": identifier, "mechanical_status": "FAIL", "execution_status": "EXECUTED",
                                 "status": "REVIEW_REQUIRED", "reason": "Invented coordinate formatting issue.",
                                 "evidence": [{"row_index": 1, "source_locator": deepcopy(locator)}]})
        self.report["regulatory_evidence_review"] = {"assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE",
            "source_sha256": self.sha, "overall_status": "REVIEW_REQUIRED", "observations": observations}
        notes = self.plan()["notes"]
        self.assertEqual(len(notes), 2)
        self.assertTrue(all(n["anchor"]["bbox_points"] == self.span("AREA:")["bbox_points"] for n in notes))
        self.assertEqual(len({n["finding_id"] for n in notes}), 2)

    def test_actual_rotated_and_cropped_markers_remain_on_original_source(self):
        for rotation in (0, 90, 180, 270):
            self.make_pdf(rotation=rotation, crop=True)
            self.report["job_record_review"] = self.job([self.job_finding()])
            before = self.pdf.read_bytes()
            data, manifest = build_annotated_pdf(self.pdf, self.report, self.inventory)
            with self.subTest(rotation=rotation), self.runtime.open(stream=data, filetype="pdf") as output, self.runtime.open(self.pdf) as source:
                # SDK annotation handles retain a weak reference to their page.
                # Keep it alive while reading rectangles or comment contents.
                output_page = output[0]
                source_page = source[0]
                comments = list(output_page.annots())
                self.assertEqual(len(comments), 1)
                expected = self.span("APPLICANT:")["bbox_points"]
                self.assertEqual(manifest["notes"][0]["anchor"]["bbox_points"], expected)
                # MuPDF includes the annotation's one-point border in rect.
                self.assertLess(max(abs(a-b) for a,b in zip(comments[0].rect, expected)), 1.01)
                self.assertEqual(output_page.rotation, source_page.rotation)
                self.assertEqual(list(output_page.cropbox), list(source_page.cropbox))
                self.assertEqual(output_page.get_text(), source_page.get_text())
                self.assertEqual(manifest["located_count"], 1)
            self.assertEqual(self.pdf.read_bytes(), before)

    def test_forged_or_reused_span_evidence_remains_unlocated(self):
        for mutation in ("text", "box", "no_spans", "clipped", "outside_region", "duplicate"):
            field = self.field("APPLICANT:")
            raw = field["evidence"]["spans"][0]
            if mutation == "text": raw["text"] = "FORGED COMPANY"
            if mutation == "box": raw["bbox_points"] = [1, 2, 3, 4]
            if mutation == "no_spans": field["evidence"]["spans"] = []
            if mutation == "clipped": raw["original_bbox_points"] = [-1, 2, 3, 4]
            if mutation == "outside_region": field["evidence"]["bbox_points"] = [1, 2, 3, 4]
            if mutation == "duplicate": field["evidence"]["spans"].append(deepcopy(raw))
            self.report["job_record_review"] = self.job([self.job_finding(evidence=[field])])
            with self.subTest(mutation=mutation): self.assertIsNone(self.plan()["notes"][0]["anchor"])

    def test_note_budget_and_invalid_status_fail_without_partial_export(self):
        self.report["job_record_review"] = self.job([self.job_finding("one"), self.job_finding("two")])
        with self.assertRaisesRegex(ValueError, "note limit"):
            build_markup_plan(self.report, self.inventory, source_sha256=self.sha, max_notes=1)
        for state in ("UNKNOWN", None):
            self.report["job_record_review"] = self.job([self.job_finding(mechanical_status=state)])
            with self.subTest(state=state), self.assertRaises(ValueError): self.plan()

    def test_actual_csv_mismatches_receive_complete_point_and_export_only_notes(self):
        csv = self.root / "invented-point-export.csv"
        csv.write_text("point_id,easting,northing,type\n1,500001.00,6000000.00,OC\n2,500002.00,6000000.00,OC\n")
        metadata = dict(crs_identifier="INVENTED_METRIC", coordinate_frame_id="INVENTED_GRID_FRAME",
                        coordinate_units="m", crs_verified=True, provenance_verified=True,
                        coordinate_roles_resolved=True, complete=True)
        table = {**metadata, "source_sha256": self.sha, "rows": [
            {"point_id": "1", "easting": "500000.00", "northing": "6000000.00", "type": "OC",
             "source_locator": {"source_sha256": self.sha, "fields": {
                 "point_id": self.evidence("1"), "easting": self.evidence("500000.00"),
                 "northing": self.evidence("6000000.00"), "type": self.evidence("OC")}}}]}
        spec = {**metadata, "schema_version": 1, "format": "CSV_POINT_EXPORT", "origin_kind": "GIS",
                "source_sha256": sha256(csv.read_bytes()).hexdigest()}
        export = compare_point_export(csv, spec, table)
        self.report["regulatory_evidence_review"] = {"assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE",
            "source_sha256": self.sha, "overall_status": "REVIEW_REQUIRED", "observations": [],
            "point_export_comparison": export}
        notes = self.plan()["notes"]
        self.assertEqual(len(notes), 2)
        coordinate = next(n for n in notes if "COORDINATES_DIFFER" in n["body"])
        extra = next(n for n in notes if "EXTRA_EXPORT_POINT" in n["body"])
        self.assertEqual(coordinate["anchor"]["bbox_points"], self.span("1")["bbox_points"])
        self.assertIsNone(extra["anchor"])
        self.assertIn("Point 1", coordinate["body"])
        self.assertTrue(all(n["status"] == "REVIEW_REQUIRED" for n in notes))
        export["plan_source_sha256"] = "1" * 64
        with self.assertRaises(ValueError): self.plan()


if __name__ == "__main__":
    unittest.main()
