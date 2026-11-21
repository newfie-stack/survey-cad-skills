"""Invented native PDFs exercise printed-number parsing through actual review."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_review import review_finished_plan
from runtime_security import load_pdf_runtime


class PrintedNumberReviewTests(unittest.TestCase):
    def setUp(self):
        self.pdf_runtime = load_pdf_runtime()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "invented-printed-numbers.pdf"

    def region(self, page, box, label=None, complete=True):
        value = {"page": page, "bbox_points": list(box), "role": "invented printed amount"}
        if label is not None:
            value["label"] = label
        if complete:
            value["coverage_review"] = {
                "status": "TEXT_COMPLETE", "method": "VISUAL_TO_TEXT_COMPARISON",
                "reviewer": "invented fixture author",
                "statement": "This synthetic field was compared with its complete printed native text."}
        return value

    def amounts(self, totals=("3,000.30 ha.",), *, a=("1,000.10 ha.",), b="2,000.20 ha.",
                unit="ha", tolerance="0.00", complete=True, total_label="TOTAL:", raster=False):
        with self.pdf_runtime.open() as document:
            page = document.new_page(width=600, height=400)
            for index, amount in enumerate(a):
                page.insert_text((40, 40 + index * 20), "PART A: " + amount)
            page.insert_text((40, 100), "PART B: " + b)
            for index, amount in enumerate(totals):
                page.insert_text((40, 160 + index * 20), (total_label or "") + " " + amount)
            if raster:
                blank = page.get_pixmap(clip=self.pdf_runtime.Rect(500, 300, 510, 310))
                page.insert_image(self.pdf_runtime.Rect(350, 145, 365, 165), pixmap=blank)
            document.save(self.pdf)
        return self.spec({"id": "sum", "kind": "decimal_sum", "unit": unit, "tolerance": tolerance,
                          "regions": [self.region(1, [30, 20, 550, 80], "PART A:"),
                                      self.region(1, [30, 80, 550, 120], "PART B:"),
                                      self.region(1, [30, 140, 550, 260], total_label, complete)]})

    def spec(self, check):
        return {"schema_version": 1, "source_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                "prepared_by": "invented printed-number fixture author", "checks": [{
                    "description": "Compare selected printed values",
                    "basis": "Invented drawing arithmetic only; no regulatory or survey calculation", **check}]}

    def review(self, spec):
        original = self.pdf.read_bytes()
        original_spec = copy.deepcopy(spec)
        report = review_finished_plan(self.pdf, spec)
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertEqual(spec, original_spec)
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["regulatory_status"], "NOT_ASSESSED")
        self.assertEqual(report["source_sha256"], spec["source_sha256"])
        return report["findings"][0]

    def test_route_sentence_period_compares_independent_sheet_totals(self):
        with self.pdf_runtime.open() as document:
            for _ in range(2):
                page = document.new_page(width=600, height=400)
                page.insert_text((40, 100), "150.00 m")
                page.insert_text((40, 200), "HISTORY: Rev 0 - route total 290.00 m.")
                page.insert_text((40, 220), "CURRENT ISSUE: Rev 1 - route total 300.00 m.")
            document.save(self.pdf)
        spec = self.spec({"id": "route", "kind": "decimal_sum", "unit": "m", "tolerance": "0.00",
                          "regions": [self.region(1, [30, 80, 300, 120]),
                                      self.region(2, [30, 80, 300, 120]),
                                      self.region(1, [30, 180, 500, 240], "CURRENT ISSUE: Rev 1 - route total")]})
        result = self.review(spec)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["observed"], ["150.00", "150.00", "300.00"])
        self.assertIn("HISTORY: Rev 0", result["evidence"][-1]["text"])
        self.assertIn("300.00 m.", result["evidence"][-1]["text"])

    def test_grouped_amounts_compare_without_losing_printed_evidence(self):
        result = self.review(self.amounts())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["expected"], "3000.30")
        self.assertEqual(result["difference"], "0.00")
        self.assertEqual(result["evidence"][-1]["spans"][0]["text"], "TOTAL: 3,000.30 ha.")

    def test_grouped_wrong_sum_reports_exact_decimal_difference(self):
        result = self.review(self.amounts(("3,000.31 ha.",)))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["difference"], "0.01")
        self.assertEqual(result["expected"], "3000.30")

    def test_terminal_period_wrong_sum_reports_exact_decimal_difference(self):
        result = self.review(self.amounts(("0.301 ha.",), a=("0.100 ha.",), b="0.200 ha."))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["difference"], "0.001")

    def test_space_and_nonbreaking_space_grouping_are_ordinary_formats(self):
        for separator in (" ", "\u00a0"):
            with self.subTest(separator=repr(separator)):
                result = self.review(self.amounts((f"3{separator}000.30 ha.",),
                                                 a=(f"1{separator}000.10 ha.",), b=f"2{separator}000.20 ha."))
                self.assertEqual(result["status"], "PASS")

    def test_squared_units_keep_the_declared_dimension(self):
        for unit in ("m2", "m\u00b2", "m^2"):
            with self.subTest(unit=unit):
                result = self.review(self.amounts((f"3,000.30 {unit}.",), a=(f"1,000.10 {unit}.",),
                                                 b=f"2,000.20 {unit}.", unit="m2"))
                self.assertEqual(result["status"], "PASS")

    def test_grouped_arithmetic_uses_the_declared_exact_tolerance(self):
        result = self.review(self.amounts(("3,000.31 ha.",), tolerance="0.01"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["difference"], "0.01")

    def test_distinct_formatted_totals_fail_even_within_sum_tolerance(self):
        result = self.review(self.amounts(("3,000.30 ha.", "3 000.31 ha."), tolerance="0.01"))
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("difference", result)
        self.assertEqual(len(result["evidence"][-1]["spans"]), 2)

    def test_equivalent_formatted_totals_agree_without_removing_equal_parts(self):
        result = self.review(self.amounts(("2,000.20 ha.", "2 000.200 ha."), b="1,000.10 ha."))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["expected"], "2000.20")
        self.assertEqual(result["observed"][:2], ["1000.10", "1000.10"])
        self.assertEqual(len(result["evidence"][-1]["spans"]), 2)

    def test_multiple_formatted_totals_require_complete_labelled_context(self):
        for kwargs in ({"complete": False}, {"total_label": None}):
            with self.subTest(kwargs=kwargs):
                result = self.review(self.amounts(("3,000.30 ha.", "3 000.31 ha."), **kwargs))
                self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_blank_competing_field_prevents_a_formatted_conflict_verdict(self):
        for kwargs in ({"totals": ("3,000.30 ha.", "3 000.31 ha.", "")},
                       {"totals": ("3,000.30 ha.", "3 000.31 ha."), "a": ("1,000.10 ha.", "")}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.review(self.amounts(**kwargs))["status"], "REVIEW_REQUIRED")

    def test_malformed_or_wrong_unit_candidates_remain_unresolved(self):
        for total in ("3,00.30 ha.", "3,000 000 ha.", "3e3 ha.", "3,000.30 m2.",
                      "3,000.30 ha. APPROXIMATE", "3,000.30 ha. 4,000.30 ha."):
            with self.subTest(total=total):
                self.assertEqual(self.review(self.amounts((total,)))["status"], "REVIEW_REQUIRED")

    def test_formatted_candidates_cannot_bypass_clipping_gate(self):
        spec = self.amounts(("3,000.30 ha.", "3,000.31 ha."))
        spec["checks"][0]["regions"][-1]["bbox_points"][3] = 180
        result = self.review(spec)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIn("Clipped", result["reason"])

    def test_formatted_candidates_cannot_bypass_raster_gate(self):
        result = self.review(self.amounts(("3,000.30 ha.", "3,000.31 ha."), raster=True))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIn("Raster", result["reason"])

    def scale(self, text, expected, complete=True, label=None):
        with self.pdf_runtime.open() as document:
            page = document.new_page(width=600, height=300)
            page.insert_text((40, 80), text)
            document.save(self.pdf)
        return self.spec({"id": "scale", "kind": "scale", "expected_denominator": expected,
                          "regions": [self.region(1, [30, 60, 550, 100], label=label, complete=complete)]})

    def test_terminal_period_scale_uses_the_complete_denominator(self):
        for text in ("SCALE 1:2,500.", "SCALE 1:2500."):
            with self.subTest(text=text):
                result = self.review(self.scale(text, 2500))
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["observed"], [2500])

    def test_malformed_scale_prefixes_cannot_false_clear(self):
        for text, previous_prefix in (("1:2,50", 2), ("1:2,500.0", 2), ("1:2,500,00", 2500),
                                      ("1:2,500 000", 2500000), ("1:2 50", 2)):
            with self.subTest(text=text):
                result = self.review(self.scale("SCALE " + text, previous_prefix))
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["observed"], [])

    def test_numeric_continuations_after_delimiters_cannot_false_clear(self):
        for tail in (" : 2", " / 500", "(000)", " (000)", " [000]", " {000}",
                     " / -500", " : .2", " ( [ 000 ] )"):
            with self.subTest(tail=tail):
                result = self.review(self.scale("MAIN SCALE 1:2500" + tail, 2500, label="MAIN SCALE"))
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["observed"], [])

    def test_delimited_separate_ratios_and_word_annotations_keep_their_bounds(self):
        for text in ("MAIN SCALE 1:2500 / 1:100", "MAIN SCALE 1:2500 (1:100)"):
            with self.subTest(text=text):
                result = self.review(self.scale(text, 2500, label="MAIN SCALE"))
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["observed"], [2500, 100])
        for text in ("MAIN SCALE 1:2500 (AT A3)", "MAIN SCALE (1:2500.) @ A3",
                     "MAIN SCALE 1:2500; MAIN VIEW"):
            with self.subTest(text=text):
                result = self.review(self.scale(text, 2500, label="MAIN SCALE"))
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["observed"], [2500])

    def test_recognized_unsupported_scale_is_not_a_confirmed_omission(self):
        for text in ("SCALE 1:", "SCALE 2:500", "SCALE 1:0", "SCALE 1:2e3"):
            with self.subTest(text=text):
                self.assertEqual(self.review(self.scale(text, 2500))["status"], "REVIEW_REQUIRED")
        self.assertEqual(self.review(self.scale("SCALE OMITTED", 2500))["status"], "FAIL")
        self.assertEqual(self.review(self.scale("SCALE OMITTED", 2500, complete=False))["status"], "REVIEW_REQUIRED")

    def test_multiple_formatted_scales_remain_unresolved(self):
        result = self.review(self.scale("MAIN 1:2,500.; INSET 1:500", 2500))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["observed"], [2500, 500])


if __name__ == "__main__":
    unittest.main()
