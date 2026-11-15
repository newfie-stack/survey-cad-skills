"""Synthetic regressions for coherent area evidence and inclusive tolerances."""
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry_review import review_survey_geometry
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory
from review_cli import run_review


def span(text, page=1, bbox=(10, 10, 150, 20)):
    return {"text": text, "page": page, "bbox_points": list(bbox)}


def table(value="0.300", page=1):
    return [span(text, page, box) for text, box in (
        ("Total", (100, 80, 160, 90)),
        ("ha", (100, 100, 110, 110)),
        ("ac", (150, 100, 160, 110)),
        (value, (90, 120, 120, 130)),
        ("0.741", (140, 120, 170, 130)),
    )]


class AreaConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json")

    def setUp(self):
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER", "activity": "PLA", "stage": "initial",
                         "plan_type": "sketch", "purpose": "synthetic"}
        self.survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                       "crs_identifier": "SYNTHETIC_METRIC", "crs_verified": True,
                       "closed_ring": True,
                       "vertices": [[0, 0], [100, 0], [100, 20], [0, 20], [0, 0]]}

    def test_conflicting_totals_cannot_agree_with_selected_survey_area(self):
        selected = span("TOTAL AREA: 0.200 ha")
        cases = [
            ([selected, span("TOTAL AREA: 0.300 ha", bbox=(10, 30, 150, 40))], {}),
            ([selected, span("TOTAL AREA: 0.300 ha", page=2)], {}),
            ([selected] + table(), {}),
            (table("0.200") + [span("TOTAL AREA: 0.300 ha")],
             {"source": "table_total", "text": "0.200"}),
            (table("0.200") + table("0.300", page=2),
             {"source": "table_total", "text": "0.200"}),
            (table("0.200") + table("0.200", page=2),
             {"source": "table_total", "text": "0.200"}),
        ]
        for spans, selection in cases:
            with self.subTest(spans=spans, selection=selection):
                survey = {**self.survey, "area_label": {
                    "page": 1, "text": selected["text"], "tolerance_ha": 0, **selection}}
                report = review_inventory({"spans": spans}, self.scenario,
                                          self.catalogue, survey_geometry=survey)
                total = next(entry for entry in report["requirements"]
                             if entry["requirement_id"] == "CANDIDATE-TOTAL-AREA")
                self.assertEqual(total["evidence_status"], "UNKNOWN")
                comparison = report["survey_geometry_review"]["area_comparison"]
                self.assertEqual(comparison["comparison"], "AREA_LABEL_UNRESOLVED")
                self.assertNotIn("calculated_ha", comparison)
                self.assertNotIn("WITHIN_SUPPLIED_TOLERANCE", report["report_markdown"])

    def test_consistent_totals_and_distinct_component_area_can_be_compared(self):
        spans = [span("TOTAL AREA: 0.200 ha"),
                 span("TOTAL ACTIVITY AREA: 0.200 ha", page=2),
                 span("AREA WITHIN EXISTING DISPOSITIONS: 0.100 ha", page=2)]
        survey = {**self.survey, "area_label": {
            "page": 1, "text": spans[0]["text"], "tolerance_ha": 0}}
        result = review_survey_geometry(survey, plan_spans=spans)
        self.assertEqual(result["area_comparison"]["comparison"], "WITHIN_SUPPLIED_TOLERANCE")

    def test_projected_decimal_area_respects_inclusive_tolerance(self):
        # 100 m x 30.1 m = 0.301 ha, exactly 0.001 ha from 0.302.
        for x, y, right, top in ((0, 0, 100, 30.1),
                                  (500000, 5600000, 500100, 5600030.1),
                                  (500000.1, 5600000.1, 500100.1, 5600030.2)):
            for label, tolerance, expected in (
                ("AREA 0.302 ha", 0.001, "WITHIN_SUPPLIED_TOLERANCE"),
                ("AREA 0.301 ha", 0, "WITHIN_SUPPLIED_TOLERANCE"),
                ("AREA 0.3020000000001 ha", 0.001, "OUTSIDE_SUPPLIED_TOLERANCE"),
            ):
                with self.subTest(origin=(x, y), label=label):
                    survey = {**self.survey,
                              "vertices": [[x, y], [right, y], [right, top],
                                           [x, top], [x, y]],
                              "area_label": {"page": 1, "text": label,
                                             "tolerance_ha": tolerance}}
                    area = review_survey_geometry(survey, plan_spans=[span(label)])[
                        "area_comparison"]
                    self.assertEqual(area["comparison"], expected)

    def test_pdf_to_report_keeps_conflicting_totals_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "synthetic.pdf", root / "review.md"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((50, 50), "TOTAL AREA: 0.200 ha")
                page.insert_text((50, 80), "TOTAL AREA: 0.300 ha")
                document.save(source)
            survey = {**self.survey, "area_label": {
                "page": 1, "text": "TOTAL AREA: 0.200 ha", "tolerance_ha": 0}}
            run_review(source, output, self.scenario,
                       Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json",
                       survey_geometry=survey)
            report = output.read_text(encoding="utf-8")
            self.assertRegex(report, r"CANDIDATE-TOTAL-AREA \|[^\n]+UNKNOWN")
            self.assertIn("Comparison: AREA_LABEL_UNRESOLVED", report)
            self.assertNotIn("WITHIN_SUPPLIED_TOLERANCE", report)

    def test_decimal_polygon_measurements_remain_json_serializable(self):
        import json
        survey = {**self.survey,
                  "vertices": [[500000, 5600000], [500100, 5600000],
                               [500100, 5600030.1], [500000, 5600030.1],
                               [500000, 5600000]]}
        polygon = json.loads(json.dumps(review_survey_geometry(survey)))["polygon"]
        self.assertEqual(polygon["area_m2"], 3010)
        self.assertEqual(polygon["area_ha"], 0.301)


if __name__ == "__main__":
    unittest.main()
