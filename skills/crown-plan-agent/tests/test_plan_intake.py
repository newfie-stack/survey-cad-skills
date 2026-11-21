"""Actual-PDF intake and bounded source-selection regressions; invented plans."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime
from finished_plan_review import review_finished_plan
from plan_intake import discover_plan, prepare_finished_plan


class PlanIntakeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.pdf = Path(self.directory.name) / "invented.pdf"
        self.fitz = load_pdf_runtime()

    def sheet(self, rows, *, image=False, rotation=0):
        with self.fitz.open() as document:
            page = document.new_page(width=500, height=300)
            for x, y, text in rows:
                page.insert_text((x, y), text, fontsize=11)
            if image:
                tile = page.get_pixmap(clip=self.fitz.Rect(450, 250, 470, 270))
                page.insert_image(self.fitz.Rect(30, 80, 200, 120), pixmap=tile)
            page.set_rotation(rotation)
            document.save(self.pdf)

    def spec(self, regions, *, kind="required_text", expected="CPA-7"):
        check = {"id": "current_job", "kind": kind, "description": "Invented current job",
                 "basis": "Explicitly reviewed current titleblock context", "regions": regions}
        if kind == "required_text":
            check["expected"] = expected
        if kind == "scale":
            check["expected_denominator"] = 5000
        return {"schema_version": 1, "source_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                "prepared_by": "Invented reviewer", "checks": [check]}

    def context(self, box=(30, 75, 250, 125), label="Job:"):
        value = {"page": 1, "bbox_points": list(box), "role": "reviewed current titleblock"}
        if label is not None:
            value["label"] = label
        return value

    def test_overlap_closure_prepares_whole_native_lines_without_manual_adjustment(self):
        self.sheet([(40, 100, "Job: CPA-7"), (40, 112, "Date: 2026-11-21")])
        original = self.spec([self.context()])
        prepared = prepare_finished_plan(self.pdf, original)
        ready = prepared["spec"]
        self.assertIsNotNone(ready)
        self.assertEqual(prepared["resolutions"][0]["status"], "READY")
        record = prepared["resolutions"][0]["regions"][0]
        self.assertEqual(record["context_bbox_points"], [30, 75, 250, 125])
        self.assertLess(record["selected_bbox_points"][3], record["support_bbox_points"][3])
        self.assertEqual(len(record["matching_candidate_ids"]), 1)
        finding = review_finished_plan(self.pdf, ready)["findings"][0]
        self.assertEqual(finding["status"], "PASS")
        self.assertIn("Date:", finding["evidence"][0]["text"])
        self.assertEqual(original, self.spec([self.context()]))

    def test_context_boundary_is_not_automatically_expanded(self):
        self.sheet([(40, 100, "Job: CPA-7"), (40, 112, "Date: 2026-11-21")])
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context((30, 87, 250, 104))]))
        self.assertIsNone(prepared["spec"])
        self.assertIn("context", prepared["resolutions"][0]["reason"].lower())
        self.assertTrue(prepared["visual_tasks"])

    def test_duplicate_labels_keep_every_candidate_and_do_not_choose_expected(self):
        self.sheet([(40, 90, "CURRENT ISSUE"), (40, 110, "Job: CPA-8"),
                    (40, 150, "REVISION HISTORY"), (40, 170, "Job: CPA-7")])
        broad = self.spec([self.context((30, 75, 250, 180))])
        prepared = prepare_finished_plan(self.pdf, broad)
        self.assertIsNone(prepared["spec"])
        record = prepared["resolutions"][0]["regions"][0]
        self.assertEqual(len(record["matching_candidate_ids"]), 2)
        self.assertEqual({c["text"] for c in record["matching_candidates"]}, {"Job: CPA-7", "Job: CPA-8"})
        broad["checks"][0]["expected"] = "CPA-8"
        self.assertEqual(record["matching_candidate_ids"],
                         prepare_finished_plan(self.pdf, broad)["resolutions"][0]["regions"][0]["matching_candidate_ids"])

    def test_explicit_current_context_does_not_substitute_history(self):
        self.sheet([(40, 100, "Job: CPA-8"), (40, 170, "Job: CPA-7")])
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context()]))
        self.assertIsNotNone(prepared["spec"])
        observed = review_finished_plan(self.pdf, prepared["spec"])["findings"][0]["observed"]
        self.assertEqual(observed, ["CPA-8"])

    def test_main_and_inset_scales_need_an_explicit_label(self):
        self.sheet([(40, 100, "MAIN SCALE 1:5000"), (40, 114, "INSET SCALE 1:100")])
        broad = self.spec([self.context(label=None)], kind="scale")
        self.assertIsNone(prepare_finished_plan(self.pdf, broad)["spec"])
        broad["checks"][0]["regions"][0]["label"] = "MAIN SCALE"
        prepared = prepare_finished_plan(self.pdf, broad)
        self.assertEqual(review_finished_plan(self.pdf, prepared["spec"])["findings"][0]["observed"], [5000])

    def test_prefix_boundary_and_stacked_or_blank_label_are_unresolved(self):
        for rows, label in [([(40, 90, "Job:"), (40, 110, "CPA-7")], "Job:"),
                            ([(40, 100, "Job: CPA-7")], "Jo")]:
            with self.subTest(rows=rows):
                self.sheet(rows)
                prepared = prepare_finished_plan(self.pdf, self.spec([self.context(label=label)]))
                self.assertIsNone(prepared["spec"])
                self.assertTrue(prepared["visual_tasks"])

    def test_separate_columns_must_not_be_silently_merged(self):
        self.sheet([(40, 100, "Job: CPA-7"), (128, 100, "Revision: 2")])
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context()]))
        # A complete Job native line can be selected safely, or merging must abstain.
        if prepared["spec"] is not None:
            observed = review_finished_plan(self.pdf, prepared["spec"])["findings"][0]["observed"]
            self.assertEqual(observed, ["CPA-7"])
        else:
            self.assertIn("REVIEW_REQUIRED", prepared["resolutions"][0]["status"])

    def test_derived_rectangles_never_inherit_completeness(self):
        self.sheet([(40, 100, "Job: CPA-7")])
        region = self.context()
        region["coverage_review"] = {"status": "TEXT_COMPLETE", "reviewer": "Invented reviewer",
                                     "method": "VISUAL_TO_TEXT_COMPARISON", "statement": "Original context read."}
        prepared = prepare_finished_plan(self.pdf, self.spec([region]))
        self.assertNotIn("coverage_review", prepared["spec"]["checks"][0]["regions"][0])
        record = prepared["resolutions"][0]["regions"][0]
        self.assertEqual(record["coverage_review_handling"], "NOT_TRANSFERRED_TO_DERIVED_REGION")

    def test_raster_and_native_page_clipping_remain_blockers(self):
        self.sheet([(40, 100, "Job: CPA-7")], image=True)
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context()]))
        self.assertIsNone(prepared["spec"])
        self.assertIn("Raster", prepared["resolutions"][0]["reason"])
        self.sheet([(2, 5, "Job: CPA-7")])
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context((0, 0, 250, 35))]))
        self.assertIsNone(prepared["spec"])
        self.assertIn("Clipped", prepared["resolutions"][0]["reason"])

    def test_empty_or_outlined_context_routes_to_visual_review(self):
        with self.fitz.open() as document:
            page = document.new_page(width=500, height=300)
            page.draw_rect(self.fitz.Rect(40, 90, 100, 110))
            document.save(self.pdf)
        inventory = discover_plan(self.pdf)
        self.assertEqual(inventory["line_candidates"], [])
        self.assertEqual(inventory["pages"][0]["size_points"], [500.0, 300.0])
        self.assertTrue(inventory["visual_tasks"])
        self.assertIsNone(prepare_finished_plan(self.pdf, self.spec([self.context()]))["spec"])

    def test_discovery_is_source_bound_portable_and_reports_actual_sheet_images(self):
        self.sheet([(40, 100, "Job: CPA-7")], image=True, rotation=90)
        original = self.pdf.read_bytes()
        result = discover_plan(self.pdf)
        self.assertEqual(result["source_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["pages"][0]["rotation_degrees"], 90)
        self.assertTrue(result["pages"][0]["image_rectangles"])
        self.assertTrue(result["line_candidates"][0]["span_ids"])
        self.assertEqual(result["line_candidates"][0]["id"], discover_plan(self.pdf)["line_candidates"][0]["id"])
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertNotIn(str(self.pdf.parent), json.dumps(result))

    def test_opposed_and_oblique_text_near_north_are_separate_native_candidates(self):
        with self.fitz.open() as document:
            page = document.new_page(width=500, height=300)
            for index, angle in enumerate((-10, 10, 170, 190)):
                point = self.fitz.Point(60 + index * 100, 150)
                page.insert_text(point, f"Job: CPA-{index}", morph=(point, self.fitz.Matrix(angle)))
            page.insert_text((240, 60), "N")
            document.save(self.pdf)
        result = discover_plan(self.pdf)
        jobs = [line for line in result["line_candidates"] if line["text"].startswith("Job:")]
        self.assertEqual(len(jobs), 4)
        self.assertGreater(len({tuple(line["text_direction"]) for line in jobs}), 2)
        self.assertNotIn("350", json.dumps(result["visual_tasks"]))
        self.assertTrue(all("drafting_violation" not in line for line in jobs))

    def test_bad_contexts_and_digest_are_rejected_before_native_pdf_parsing(self):
        self.sheet([(40, 100, "Job: CPA-7")])
        spec = self.spec([self.context()])
        spec["source_sha256"] = "0" * 64
        with patch("plan_intake.load_pdf_runtime", side_effect=AssertionError("native parse")):
            with self.assertRaisesRegex(ValueError, "digest|SHA"):
                prepare_finished_plan(self.pdf, spec)
        spec = self.spec([self.context()])
        spec["checks"][0]["unexpected"] = True
        with patch("plan_intake.load_pdf_runtime", side_effect=AssertionError("native parse")):
            with self.assertRaisesRegex(ValueError, "Unknown"):
                prepare_finished_plan(self.pdf, spec)

    def test_outside_and_nonexistent_page_contexts_are_rejected(self):
        self.sheet([(40, 100, "Job: CPA-7")])
        for region in [self.context((0, 0, 501, 200)), {**self.context(), "page": 2}]:
            with self.subTest(region=region):
                with self.assertRaises(ValueError):
                    prepare_finished_plan(self.pdf, self.spec([region]))

    def test_every_request_survives_and_only_ready_checks_enter_spec(self):
        self.sheet([(40, 100, "Job: CPA-7")])
        spec = self.spec([self.context()])
        missing = copy.deepcopy(spec["checks"][0])
        missing["id"] = "missing"
        missing["regions"][0]["label"] = "Date:"
        spec["checks"].append(missing)
        prepared = prepare_finished_plan(self.pdf, spec)
        self.assertEqual(len(prepared["resolutions"]), 2)
        self.assertEqual([c["id"] for c in prepared["spec"]["checks"]], ["current_job"])
        self.assertEqual(prepared["resolutions"][1]["request"], missing)

    def test_oblique_opposing_fields_near_north_remain_independent(self):
        with self.fitz.open() as document:
            page = document.new_page(width=500, height=300)
            for point, angle in [(self.fitz.Point(80, 150), -10), (self.fitz.Point(420, 150), 170)]:
                page.insert_text(point, "Job: CPA-7", morph=(point, self.fitz.Matrix(angle)))
            page.insert_text((248, 60), "N")
            document.save(self.pdf)
        regions = [self.context((20, 100, 200, 220)), self.context((300, 100, 480, 220))]
        prepared = prepare_finished_plan(self.pdf, self.spec(regions, kind="same_text"))
        self.assertIsNotNone(prepared["spec"])
        finding = review_finished_plan(self.pdf, prepared["spec"])["findings"][0]
        self.assertEqual(finding["status"], "PASS")
        self.assertEqual(finding["observed"], ["CPA-7", "CPA-7"])

    def test_unsupported_affine_geometry_routes_to_visual_review(self):
        with self.fitz.open() as document:
            page = document.new_page(width=5000, height=5000)
            point = self.fitz.Point(2500, 2500)
            page.insert_text(point, "Job: CPA-7", morph=(point, self.fitz.Matrix(10, 0.05) * self.fitz.Matrix(35)))
            document.save(self.pdf)
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context((0, 0, 5000, 5000))]))
        self.assertIsNone(prepared["spec"])
        self.assertIn("geometry", prepared["resolutions"][0]["reason"])

    def test_overlap_closure_has_a_hard_iteration_bound(self):
        self.sheet([(40, 80, "Job: CPA-7")] + [(40, 92 + i * 12, f"Field{i}: observed") for i in range(8)])
        spec = self.spec([self.context((30, 60, 250, 210))])
        with patch("plan_intake.MAX_CLOSURE_ROUNDS", 1):
            prepared = prepare_finished_plan(self.pdf, spec)
        self.assertIsNone(prepared["spec"])
        self.assertIn("iteration limit", prepared["resolutions"][0]["reason"])

    def test_wrapped_labelled_value_is_not_truncated_to_a_ready_field(self):
        self.sheet([(40, 90, "Job: CPA-"), (40, 102, "7")])
        prepared = prepare_finished_plan(self.pdf, self.spec([self.context()]))
        self.assertIsNone(prepared["spec"])
        self.assertIn("wrapped", prepared["resolutions"][0]["reason"])

    def test_indented_wrapped_values_cannot_falsely_clear_conflicting_job_ids(self):
        self.sheet([(40, 100, "Job: CPA-"), (65, 112, "7"),
                    (280, 100, "Job: CPA-"), (305, 112, "8")])
        regions = [self.context((25, 75, 200, 130)), self.context((265, 75, 440, 130))]
        spec = self.spec(regions, kind="same_text")
        # The legacy label reader sees equal first-line fragments. Preparation
        # must recognize uncertainty before supplying those fragments as fields.
        legacy = review_finished_plan(self.pdf, spec)["findings"][0]
        self.assertEqual(legacy["status"], "PASS")
        self.assertEqual(legacy["observed"], ["CPA-", "CPA-"])
        prepared = prepare_finished_plan(self.pdf, spec)
        self.assertIsNone(prepared["spec"])
        self.assertEqual(prepared["resolutions"][0]["status"], "REVIEW_REQUIRED")
        self.assertTrue(all("wrapped" in r["reason"] for r in prepared["resolutions"][0]["regions"]))
        self.assertEqual(len([t for t in prepared["visual_tasks"] if t.get("check_id") == "current_job"]), 2)

    def test_indented_explicit_neighboring_fields_still_prepare_independently(self):
        self.sheet([(40, 100, "Job: CPA-7"), (65, 112, "REV 1"),
                    (280, 100, "Job: CPA-7"), (305, 112, "REV 2")])
        regions = [self.context((25, 75, 200, 130)), self.context((265, 75, 440, 130))]
        spec = self.spec(regions, kind="same_text")
        revision = copy.deepcopy(spec["checks"][0])
        revision["id"] = "revision"
        for region in revision["regions"]:
            region["label"] = "REV"
        spec["checks"].append(revision)
        prepared = prepare_finished_plan(self.pdf, spec)
        self.assertEqual([r["status"] for r in prepared["resolutions"]], ["READY", "READY"])
        findings = review_finished_plan(self.pdf, prepared["spec"])["findings"]
        self.assertEqual([f["status"] for f in findings], ["PASS", "FAIL"])
        self.assertEqual(findings[0]["observed"], ["CPA-7", "CPA-7"])

    def test_duplicate_or_blank_total_fields_remain_visible_followups(self):
        for totals in [["TOTAL: 0.300 ha", "TOTAL: 0.400 ha"], ["TOTAL: 0.300 ha", "TOTAL:"]]:
            with self.subTest(totals=totals):
                self.sheet([(40, 60, "PART A: 0.100 ha"), (40, 90, "PART B: 0.200 ha")] +
                           [(40, 140 + i * 20, text) for i, text in enumerate(totals)])
                regions = [self.context((30, 40, 250, 75), "PART A:"),
                           self.context((30, 75, 250, 105), "PART B:"),
                           self.context((30, 120, 250, 180), "TOTAL:")]
                spec = self.spec(regions, kind="decimal_sum")
                spec["checks"][0].update(unit="ha", tolerance="0.000")
                prepared = prepare_finished_plan(self.pdf, spec)
                self.assertIsNone(prepared["spec"])
                total = prepared["resolutions"][0]["regions"][-1]
                self.assertEqual(len(total["matching_candidate_ids"]), 2)
                self.assertEqual({c["text"] for c in total["matching_candidates"]}, set(totals))

    def test_declared_labels_in_the_same_panel_distinguish_independent_fields(self):
        self.sheet([(40, 90, "Job CPA-7"), (40, 102, "DWG-42"), (40, 114, "Rev 2")])
        spec = self.spec([self.context(label="Job")])
        for identifier, label in [("drawing", "DWG-"), ("revision", "Rev")]:
            check = copy.deepcopy(spec["checks"][0])
            check["id"] = identifier
            check["regions"][0]["label"] = label
            spec["checks"].append(check)
        prepared = prepare_finished_plan(self.pdf, spec)
        self.assertEqual([r["status"] for r in prepared["resolutions"]], ["READY"] * 3)

    def test_oversized_context_keeps_a_followup_without_copying_all_candidates(self):
        self.sheet([(40, 80, "Job: CPA-7"), (40, 100, "Date: today"), (40, 120, "Rev: 2")])
        with patch("plan_intake.MAX_CONTEXT_SPANS", 2):
            prepared = prepare_finished_plan(self.pdf, self.spec([self.context((30, 60, 250, 150))]))
        record = prepared["resolutions"][0]["regions"][0]
        self.assertIsNone(prepared["spec"])
        self.assertEqual(record["candidate_listing"], "REFER_TO_INTAKE_CONTEXT_LIMIT")
        self.assertEqual(record["context_candidate_count"], 3)
        self.assertEqual(record["matching_candidate_count"], 1)
        self.assertEqual(record["matching_candidates"], [])


if __name__ == "__main__":
    unittest.main()
