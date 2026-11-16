"""Synthetic source-bound note planning; no actual plan or accepted findings."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))
try:
    from pdf_markup_plan import build_markup_plan
except ModuleNotFoundError as exc:
    if exc.name != "pdf_markup_plan":
        raise
    build_markup_plan = None

from deficiency_report import build_ledger
from inventory_review import inventory_review
from pdf_inspector import extract_pdf
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory

try:
    import pymupdf
except ImportError:
    pymupdf = None


class PdfMarkupPlanTests(unittest.TestCase):
    def setUp(self):
        self.digest = sha256(b"INVENTED immutable PDF snapshot").hexdigest()
        self.box = [20.0, 30.0, 100.0, 44.0]
        self.text = "SCALE 1:5000"
        self.inventory = {"source_filename": "invented.pdf", "source_sha256": self.digest,
                          "pages": 1, "status": "TEXT_INVENTORY_ONLY", "spans": [
                              {"page": 1, "text": self.text, "bbox_points": list(self.box),
                               "page_size_points": [612.0, 792.0]}]}
        self.report = build_ledger({}, [
            {"requirement_id": "INVENTED-SCALE", "evidence_key": "scale",
             "summary": "Confirm the numerical scale", "citation": {
                 "publication_title": "Invented reference", "version_date": "2026-01-01",
                 "section": "TEST-1", "page": 88, "source_url": "https://example.invalid/reference"},
             "review_instruction": "Confirm the scale applies to the main plan."}], {
            "scale": {"present": True, "page": 1, "bbox_points": list(self.box),
                      "observation": self.text, "source_text": self.text,
                      "source_filename": "invented.pdf", "candidate_count": 1}})
        self.report["source_sha256"] = self.digest

    def plan(self, report=None, inventory=None, **kwargs):
        self.assertIsNotNone(build_markup_plan, "Source-bound PDF markup planning is not implemented")
        return build_markup_plan(report if report is not None else self.report,
                                 inventory if inventory is not None else self.inventory,
                                 source_sha256=self.digest, **kwargs)

    def test_unique_raw_span_is_located_and_inputs_are_unchanged(self):
        before = deepcopy((self.report, self.inventory))
        result = self.plan()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["source_sha256"], self.digest)
        self.assertEqual(result["coordinate_frame"], "UNROTATED_CROP_RELATIVE_PDF_POINTS")
        note = result["notes"][0]
        self.assertEqual(note["anchor"], {"page": 1, "bbox_points": self.box})
        self.assertEqual(note["evidence_page"], 1)
        self.assertEqual(note["finding_id"], "INVENTED-SCALE")
        self.assertEqual(note["status"], "REVIEW_REQUIRED")
        self.assertEqual(note["citation"]["page"], 88)
        self.assertEqual((self.report, self.inventory), before)

    def test_identical_bytes_under_another_filename_remain_bound(self):
        inventory = deepcopy(self.inventory)
        inventory["source_filename"] = "renamed-copy.pdf"
        self.assertEqual(self.plan(inventory=inventory)["notes"][0]["anchor"]["page"], 1)

    def test_missing_mismatched_or_malformed_hashes_abort(self):
        self.assertIsNotNone(build_markup_plan, "Source binding is not implemented")
        for target in ("report", "inventory", "argument"):
            for value in (None, "0" * 64, "x" * 64, self.digest.upper()):
                with self.subTest(target=target, value=value):
                    report, inventory = deepcopy(self.report), deepcopy(self.inventory)
                    argument = self.digest
                    if target == "report": report["source_sha256"] = value
                    elif target == "inventory": inventory["source_sha256"] = value
                    else: argument = value
                    with self.assertRaises(ValueError):
                        build_markup_plan(report, inventory, source_sha256=argument)

    def test_multiple_candidates_do_not_use_the_first_box(self):
        report = deepcopy(self.report)
        report["requirements"][0]["candidate_count"] = 2
        note = self.plan(report)["notes"][0]
        self.assertIsNone(note["anchor"])
        self.assertEqual(note["location_reason"], "MULTIPLE_CANDIDATES")
        self.assertEqual(note["evidence_page"], 1)

    def test_visual_unknown_and_absent_evidence_are_unlocated(self):
        for status in ("VISUAL_CHECK_REQUIRED", "UNKNOWN", "NOT_OBSERVED_IN_SUPPLIED_EVIDENCE"):
            with self.subTest(status=status):
                report = deepcopy(self.report)
                report["requirements"][0]["evidence_status"] = status
                note = self.plan(report)["notes"][0]
                self.assertIsNone(note["anchor"])
                self.assertEqual(note["status"], "REVIEW_REQUIRED")

    def test_invalid_boxes_and_missing_provenance_stay_in_index(self):
        for box in (None, [5, 1, 1, 10], [1, 2, 3], [0, 0, 0, 5],
                    [-1, 2, 100, 20], [20, 30, 700, 44], [True, 30, 100, 44],
                    [20, 30, float("nan"), 44], [20, 30, float("inf"), 44]):
            with self.subTest(box=box):
                report = deepcopy(self.report)
                report["requirements"][0]["bbox_points"] = box
                report["requirements"][0]["input_evidence"]["bbox_points"] = box
                self.assertIsNone(self.plan(report)["notes"][0]["anchor"])
        report = deepcopy(self.report)
        report["requirements"][0]["input_evidence"] = None
        self.assertIsNone(self.plan(report)["notes"][0]["anchor"])

    def test_disagreeing_or_nonunique_source_span_is_not_an_anchor(self):
        for mutation in ("raw_text", "input_box", "page", "input_page_bool", "duplicate_span"):
            with self.subTest(mutation=mutation):
                report, inventory = deepcopy(self.report), deepcopy(self.inventory)
                if mutation == "raw_text": report["requirements"][0]["input_evidence"]["source_text"] = "OTHER"
                elif mutation == "input_box": report["requirements"][0]["input_evidence"]["bbox_points"] = [21, 30, 100, 44]
                elif mutation == "page": report["requirements"][0]["page"] = 88
                elif mutation == "input_page_bool": report["requirements"][0]["input_evidence"]["page"] = True
                else: inventory["spans"].append(deepcopy(inventory["spans"][0]))
                self.assertIsNone(self.plan(report, inventory)["notes"][0]["anchor"])

    def test_semantic_table_label_uses_separate_raw_cell_text(self):
        report, inventory = deepcopy(self.report), deepcopy(self.inventory)
        entry = report["requirements"][0]
        entry["observation"] = "0.020 ha (Total column)"
        entry["input_evidence"]["source_text"] = "0.020"
        inventory["spans"][0]["text"] = "0.020"
        note = self.plan(report, inventory)["notes"][0]
        self.assertIsNotNone(note["anchor"])
        self.assertIn("0.020 ha (Total column)", note["body"])

    def test_global_notes_are_deduplicated_unlocated_and_actions_are_grouped(self):
        report = deepcopy(self.report)
        report["review_summary"] = {
            "needs_attention": ["Current source needs review.", "Current source needs review."],
            "not_checked": ["Current source needs review.", "Reconstruction did not run."],
            "context_question": "What activity applies?", "next_steps": ["Confirm source edition."]}
        notes = self.plan(report)["notes"]
        global_notes = [n for n in notes if n["kind"] == "GLOBAL_REVIEW"]
        self.assertEqual(len(global_notes), 3)
        self.assertTrue(all(n["anchor"] is None and n["evidence_page"] is None for n in global_notes))
        self.assertEqual(sum(n["body"] == "Current source needs review." for n in global_notes), 1)
        actions = [n for n in global_notes if "What activity applies?" in n["body"]]
        self.assertEqual(len(actions), 1)
        self.assertIn("Confirm source edition.", actions[0]["body"])

    def test_ids_are_deterministic_and_duplicate_findings_are_rejected(self):
        report = deepcopy(self.report)
        second = deepcopy(report["requirements"][0]); second["requirement_id"] = "AAAA-INVENTED"
        report["requirements"].append(second)
        first = self.plan(report)
        report["requirements"].reverse()
        self.assertEqual(first, self.plan(report))
        self.assertEqual([n["note_id"] for n in first["notes"]], ["R001", "R002"])
        report["requirements"][1]["requirement_id"] = "AAAA-INVENTED"
        with self.assertRaises(ValueError): self.plan(report)

    def test_status_limits_and_oversized_text_are_rejected_without_dropping_notes(self):
        for limit in (0, 201, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError): self.plan(max_notes=limit)
        report = deepcopy(self.report)
        report["review_summary"] = {"needs_attention": ["An additional global review item."]}
        with self.assertRaises(ValueError): self.plan(report, max_notes=1)
        for field, value in (("status", "PASS"), ("requirement_summary", "X" * 513),
                             ("review_instruction", "X" * 4097), ("source_url", "X" * 4097)):
            with self.subTest(field=field):
                report = deepcopy(self.report); report["requirements"][0][field] = value
                with self.assertRaises(ValueError): self.plan(report)

    def test_empty_requirements_create_no_fabricated_notes(self):
        report = deepcopy(self.report);report["requirements"] = []
        self.assertEqual(self.plan(report)["notes"], [])

    def test_source_inventory_page_and_span_limits_remain_bounded(self):
        inventory = deepcopy(self.inventory);inventory["pages"] = 101
        with self.assertRaises(ValueError): self.plan(inventory=inventory)
        inventory = deepcopy(self.inventory);inventory["spans"] = [None] * 200001
        with self.assertRaises(ValueError): self.plan(inventory=inventory)

    def test_note_budget_stops_before_consuming_further_summary_items(self):
        class UnexpectedTail(list):
            def __iter__(self):
                yield "First global item."
                yield "Second global item exceeds the remaining note budget."
                raise AssertionError("Consumed summary data after the note budget was exhausted")
        report = deepcopy(self.report)
        report["review_summary"] = {"needs_attention": UnexpectedTail([0, 1, 2])}
        with self.assertRaisesRegex(ValueError, "note limit"):
            self.plan(report, max_notes=2)

    def test_action_text_budget_stops_before_consuming_further_items(self):
        class UnexpectedTail(list):
            def __iter__(self):
                yield "A" * 3000
                yield "B" * 2000
                raise AssertionError("Consumed actions after the combined text budget was exhausted")
        report = deepcopy(self.report)
        report["review_summary"] = {"next_steps": UnexpectedTail([0, 1, 2])}
        with self.assertRaisesRegex(ValueError, "text limit"):
            self.plan(report)

    def test_summary_input_counts_are_bounded_even_for_duplicate_items(self):
        for field in ("needs_attention", "not_checked", "next_steps"):
            with self.subTest(field=field):
                report = deepcopy(self.report)
                report["review_summary"] = {field: ["Repeated source review item."] * 201}
                with self.assertRaisesRegex(ValueError, "item limit"):
                    self.plan(report)

    def test_grouped_action_deduplication_preserves_first_seen_order(self):
        report = deepcopy(self.report)
        report["review_summary"] = {"context_question": "Confirm source?",
                                    "next_steps": ["First action.", "First action.",
                                                   "Second action.", "Confirm source?"]}
        global_notes = [note for note in self.plan(report)["notes"] if note["kind"] == "GLOBAL_REVIEW"]
        self.assertEqual([note["body"] for note in global_notes],
                         ["Confirm source?\nFirst action.\nSecond action."])

    def test_oversized_text_is_rejected_before_whitespace_processing(self):
        class OversizedText(str):
            def strip(self, *args, **kwargs):
                raise AssertionError("Processed text beyond its declared limit")
        report = deepcopy(self.report)
        report["review_summary"] = {"needs_attention": [OversizedText("X" * 4097)]}
        with self.assertRaises(ValueError): self.plan(report)

    @unittest.skipUnless(pymupdf is not None, "PyMuPDF unavailable")
    def test_immutable_extraction_hash_and_raw_table_cell_reach_the_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-table.pdf"
            with pymupdf.open() as doc:
                page = doc.new_page(width=612, height=792)
                for point, text in [((124, 130), "Total"), ((100, 150), "ha"),
                                    ((160, 150), "ac"), ((92, 170), "0.020"), ((152, 170), "0.049")]:
                    page.insert_text(point, text)
                doc.save(path)
            expected = sha256(path.read_bytes()).hexdigest()
            inventory = extract_pdf(path, include_vectors=False)
            self.assertEqual(inventory.get("source_sha256"), expected)
            scenario = {"land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
                        "disposition": "LOC", "plan_type": "sketch", "purpose": "Invented", "subactivity": ""}
            report = review_inventory(inventory, scenario, load_candidate_catalog(ENGINE / "candidate_requirements.json"))
            self.assertEqual(report.get("source_sha256"), expected)
            entry = next(e for e in report["requirements"] if e["requirement_id"] == "CANDIDATE-TOTAL-AREA")
            self.assertEqual(entry["observation"], "0.020 ha (Total column)")
            self.assertEqual(entry["input_evidence"].get("source_text"), "0.020")
            result = build_markup_plan(report, inventory, source_sha256=expected)
            note = next(n for n in result["notes"] if n["finding_id"] == "CANDIDATE-TOTAL-AREA")
            self.assertIsNotNone(note["anchor"])


if __name__ == "__main__":
    unittest.main()
