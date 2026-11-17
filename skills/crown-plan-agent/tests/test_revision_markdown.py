"""Synthetic fixed-contract tests for review-only revision Markdown."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

try:
    from revision_markdown import render_comparison_markdown
except ModuleNotFoundError:
    render_comparison_markdown = None


STATES = (
    "SAME_OBSERVED_TEXT", "OBSERVED_TEXT_CHANGED", "NEWLY_OBSERVED_TEXT",
    "PREVIOUS_OBSERVATION_NOT_FOUND", "AMBIGUOUS", "NOT_COMPARED",
)


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def fixture():
    def side(text, page):
        return {"source_text": text, "observation": text + " observation",
                "evidence_status": "OBSERVED_CANDIDATE", "source_status": "REVIEW_REQUIRED",
                "candidate_count": 1, "anchor": {"page": page, "bbox_points": [1, 2, 3, 4]},
                "location_reason": None}

    def summary(label):
        return {"status": "REVIEW_REQUIRED", "headline": label + " needs review",
                "checked": [label + " extracted text checked"],
                "needs_attention": [label + " authority needs confirmation"],
                "not_checked": [label + " manual geometry unchecked"],
                "next_steps": [label + " inspect original"],
                "context_question": label + " which land class?",
                "input_requests": [{"field": "land_class", "question": label + " confirm class?"}]}

    context = {"regulator": "AER", "stage": "initial", "purpose": "Synthetic sketch review",
               "nested": {"labels": ["alpha", "beta"], "year": 2026}}
    return {
        "schema_version": 1, "comparison_type": "CROWN_PLAN_REVISION_TEXT_REVIEW",
        "overall_status": "REVIEW_REQUIRED", "assessment_type": "REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE",
        "basis": {"engine_version": "0.6.0", "engine_sha256": "a" * 64,
                  "scenario_sha256": canonical_digest(context), "catalogue_sha256": "c" * 64,
                  "basis_sha256": "d" * 64,
                  "references": [{"name": "Synthetic authority", "sha256": "e" * 64}]},
        "review_context": context,
        "baseline": {"source_filename": "before.pdf", "source_sha256": "1" * 64, "pages": 3},
        "revised": {"source_filename": "after.pdf", "source_sha256": "2" * 64, "pages": 4},
        "identical_source_bytes": False,
        "requirements": [{"requirement_id": "SYNTH-" + str(i), "requirement_summary": "Synthetic label",
                          "comparison_status": state, "baseline": side("BEFORE COMPANY", 2),
                          "revised": side("AFTER COMPANY", 3), "location_changed": True,
                          "citation": {"title": "Manual", "version": "2026", "section": "4.1",
                                       "page": 18, "url": "https://example.invalid/manual"}}
                         for i, state in enumerate(STATES)],
        "text_changes": [{"change_id": "T00001", "normalized_text": "Company name",
                          "change_status": "COUNT_CHANGED", "before_count": 1, "after_count": 2,
                          "baseline_occurrences": [{"raw_text": "Company name", "page": 2,
                                                    "bbox_points": [1, 2, 3, 4], "page_size_points": [100, 200],
                                                    "text_angle_degrees": 0}],
                          "revised_occurrences": [{"raw_text": "Company name", "page": None,
                                                   "bbox_points": None, "page_size_points": None,
                                                   "text_angle_degrees": None, "location_reason": "unresolved source bounds"}]}],
        "summary": {"finding_counts": {state: 1 for state in STATES}, "changed_text_groups": 1},
        "baseline_review_summary": summary("Baseline"), "revised_review_summary": summary("Revised"),
        "limitations": ["Manual and visual review required", "Span fragmentation can produce differences"],
    }


class RevisionMarkdownTests(unittest.TestCase):
    def render(self, data=None):
        self.assertIsNotNone(render_comparison_markdown, "comparison renderer is not implemented")
        return render_comparison_markdown(fixture() if data is None else data)

    def real_packet(self, directory):
        from revision_cli import run_comparison
        scenario = {'land_class': 'alberta_crown', 'regulator': 'AER', 'disposition': 'LOC',
                    'stage': 'initial', 'plan_type': 'sketch', 'purpose': 'Invented purpose',
                    'subactivity': ''}
        run_comparison(directory / 'baseline.pdf', directory / 'revised.pdf',
                       directory / 'comparison.md', directory / 'comparison.json', scenario,
                       Path(__file__).resolve().parents[1] / 'engine/candidate_requirements.json')
        return (json.loads((directory / 'comparison.json').read_text()),
                (directory / 'comparison.md').read_text())

    def test_real_table_cell_reassignment_reports_candidate_change_without_literal_changes(self):
        import fitz
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name, selected, other in [('baseline.pdf', '0.200', '0.300'),
                                           ('revised.pdf', '0.300', '0.200')]:
                with fitz.open() as document:
                    page = document.new_page(width=500, height=700)
                    for cx, y, text in [(150, 50, 'Total'), (130, 70, 'ha'), (170, 70, 'ac'),
                                        (130, 90, selected), (170, 90, '0.494'), (330, 300, other)]:
                        page.insert_text((cx - fitz.get_text_length(text, fontsize=11) / 2, y), text)
                    document.save(directory / name)
            model, output = self.real_packet(directory)
        row = next(row for row in model['requirements'] if row['requirement_id'] == 'CANDIDATE-TOTAL-AREA')
        self.assertEqual(row['comparison_status'], 'OBSERVED_TEXT_CHANGED')
        self.assertEqual(row['baseline']['source_text'], '0.200')
        self.assertEqual(row['revised']['source_text'], '0.300')
        self.assertEqual(model['text_changes'], [])
        self.assertNotIn('No changes found in the supported text comparison.', output)
        self.assertIn('No literal text groups or occurrence counts changed.', output)

    def test_real_rotation_preserves_text_equality_and_renders_both_source_frames(self):
        import fitz
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with fitz.open() as document:
                document.new_page(width=500, height=700).insert_text((40, 85), 'SCALE 1:5000')
                document.save(directory / 'baseline.pdf')
            with fitz.open(directory / 'baseline.pdf') as document:
                document[0].set_rotation(90)
                document.save(directory / 'revised.pdf')
            model, output = self.real_packet(directory)
        row = next(row for row in model['requirements'] if row['requirement_id'] == 'CANDIDATE-PLAN-SCALE')
        self.assertEqual(row['comparison_status'], 'SAME_OBSERVED_TEXT')
        self.assertEqual(model['text_changes'], [])
        self.assertIs(row['location_changed'], True)
        self.assertEqual(row['baseline']['page_frame']['rotation'], 0)
        self.assertEqual(row['revised']['page_frame']['rotation'], 90)
        self.assertEqual(row['revised']['page_frame']['display_rect_points'], [0, 0, 700, 500])
        for text in ('Baseline PDF page rotation (degrees): 0', 'Revised PDF page rotation (degrees): 90',
                     'Baseline MediaBox (points):', 'Revised CropBox (points):',
                     'Revised display rect (points):', 'Publication page: 7'):
            self.assertIn(text, output)

    def test_real_metadata_rewrite_with_equal_frames_has_unchanged_location_and_catalogue_actions(self):
        import fitz
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with fitz.open() as document:
                document.new_page(width=500, height=700).insert_text((40, 85), 'SCALE 1:5000')
                document.save(directory / 'baseline.pdf')
            with fitz.open(directory / 'baseline.pdf') as document:
                document.set_metadata({'title': 'Invented metadata change'})
                document.save(directory / 'revised.pdf')
            model, output = self.real_packet(directory)
        scale = next(row for row in model['requirements'] if row['requirement_id'] == 'CANDIDATE-PLAN-SCALE')
        bar = next(row for row in model['requirements'] if row['requirement_id'] == 'CANDIDATE-SCALE-BAR')
        self.assertIs(scale['location_changed'], False)
        self.assertFalse(model['identical_source_bytes'])
        self.assertEqual(model['text_changes'], [])
        self.assertIn('No changes found in the supported text comparison.', output)
        self.assertEqual(scale.get('review_instruction'),
                         'Confirm the candidate is the main plan scale in the title block. Check permitted scales and exceptions under section 1.1.4 and applicable activity provisions.')
        self.assertEqual(bar.get('review_instruction'),
                         'Visually confirm the title-block scale bar. Section 1.3.7.2 exempts detail views from the scale-bar requirement.')
        self.assertIn('Check permitted scales and exceptions under section 1&#46;1&#46;4', output)
        self.assertIn('exempts detail views from the scale&#45;bar requirement', output)
        self.assertIn('Verify current source clause and applicability', output)

    def test_actions_and_unknown_source_frames_are_rendered_literally(self):
        data = fixture()
        hostile = '![map](https://example.invalid) <img src="x">\n```'
        data['requirements'][0].update(review_instruction=hostile, correction=hostile)
        output = self.render(data)
        self.assertIn('- Review instruction: &#33;&#91;map&#93;', output)
        self.assertIn('- Correction / review action: &#33;&#91;map&#93;', output)
        self.assertIn('- Baseline PDF page rotation (degrees): unknown', output)
        self.assertIn('- Revised source frame status: UNKNOWN', output)
        for active in ('![', 'https://', '<img', '```'):
            self.assertNotIn(active, output)

    def test_summary_first_includes_all_six_states_and_source_basis_hashes(self):
        output = self.render()
        self.assertLess(output.index("## Comparison summary"), output.index("## Source and basis"))
        for state in STATES:
            self.assertIn("Comparison state: " + state, output)
        for char in "acde12":
            self.assertIn(char * 64, output)
        self.assertIn(fixture()["basis"]["scenario_sha256"], output)
        self.assertIn("REVIEW_REQUIRED", output)
        self.assertIn("Changed text groups: 1", output)

    def test_summary_uses_plain_language_state_labels(self):
        output = self.render()
        summary = output.split("## Comparison summary", 1)[1].split("## Scope", 1)[0]
        for label in ("Same observed text", "Text changed", "Newly observed",
                      "Previous observation not found", "Ambiguous", "Not compared"):
            self.assertIn("| " + label + " | 1 |", summary)
        for state in STATES:
            self.assertNotIn("| " + state + " |", summary)

    def test_common_application_context_shows_values_and_nested_json_deterministically(self):
        data = fixture()
        output = self.render(data)
        self.assertIn("## Common application context", output)
        self.assertIn("- regulator: AER", output)
        self.assertIn("- stage: initial", output)
        self.assertIn("- purpose: Synthetic sketch review", output)
        self.assertIn("&#123;&#34;labels&#34;&#58;&#91;&#34;alpha&#34;&#44;&#34;beta&#34;&#93;", output)
        data["review_context"] = dict(reversed(list(data["review_context"].items())))
        self.assertEqual(output, self.render(data))

    def test_context_hostile_keys_and_nested_values_are_literal(self):
        data = fixture()
        hostile = '![map](https://example.invalid) <img src="x">\n```'
        data["review_context"] = {hostile: {"labels": [hostile], "unicode": "測量"}}
        data["basis"]["scenario_sha256"] = canonical_digest(data["review_context"])
        output = self.render(data)
        self.assertIn("&#91;map&#93;", output)
        self.assertIn("&#60;img", output)
        self.assertIn("測量", output)
        for active in ("![", "https://", "<img", "```", hostile):
            self.assertNotIn(active, output)

    def test_rejects_context_missing_or_not_bound_to_scenario_hash(self):
        for mutation in ("missing", "changed", "not-object"):
            with self.subTest(mutation=mutation):
                data = fixture()
                if mutation == "missing":
                    data.pop("review_context")
                elif mutation == "changed":
                    data["review_context"]["regulator"] = "another regulator"
                else:
                    data["review_context"] = ["AER"]
                with self.assertRaises(ValueError):
                    self.render(data)

    def test_before_after_and_separate_source_and_publication_pages(self):
        data = fixture()
        data["requirements"][0]["revised"]["anchor"] = None
        data["requirements"][0]["revised"]["location_reason"] = "ambiguous source anchor"
        output = self.render(data)
        for text in ("BEFORE COMPANY", "AFTER COMPANY", "Baseline source page: 2",
                     "Revised source page: unknown", "Publication page: 18",
                     "ambiguous source anchor", "Location changed: yes"):
            self.assertIn(text, output)
        self.assertNotIn("Revised source page: 18", output)

    def test_literal_groups_show_counts_raw_text_and_each_sides_locations(self):
        data = fixture()
        for status, counts in (("ADDED", (0, 1)), ("REMOVED", (1, 0)), ("COUNT_CHANGED", (1, 2))):
            data["text_changes"][0].update(change_status=status, before_count=counts[0], after_count=counts[1])
            output = self.render(data)
            self.assertIn("Literal text status: " + status, output)
            self.assertIn(f"Baseline count: {counts[0]}; Revised count: {counts[1]}", output)
            self.assertIn("Raw text: Company name", output)
            self.assertIn("Baseline source page: 2", output)
            self.assertIn("Revised source page: unknown", output)
            self.assertIn("unresolved source bounds", output)

    def test_unchanged_text_does_not_claim_identical_plans_or_approval(self):
        data = fixture()
        data["text_changes"] = []
        data["summary"]["changed_text_groups"] = 0
        output = self.render(data)
        self.assertIn("No literal text groups or occurrence counts changed.", output)
        self.assertNotIn("No changes found in the supported text comparison", output)
        self.assertIn("Source PDF bytes differ", output)
        self.assertNotIn("plans are identical", output.lower())
        self.assertNotIn("automatically fixed", output.lower())
        data["identical_source_bytes"] = True
        data["revised"]["source_sha256"] = data["baseline"]["source_sha256"]
        output = self.render(data)
        self.assertIn("Source PDF bytes are identical", output)
        self.assertIn("does not establish regulatory acceptance", output)

    def test_preserves_unresolved_context_and_manual_work_on_both_sides(self):
        output = self.render()
        for label in ("Baseline", "Revised"):
            for text in ("manual geometry unchecked", "which land class", "confirm class", "inspect original"):
                self.assertIn(label + " " + text, output)

    def test_hostile_source_values_are_literal_in_every_section(self):
        data = fixture()
        hostile = '![map](https://example.invalid/x) <img src="https://example.invalid/y">\n```\n# forged\n[click](javascript:go) https://example.invalid & &#91; \u202e'
        data["requirements"][0]["baseline"]["source_text"] = hostile
        data["requirements"][0]["citation"]["url"] = hostile
        data["text_changes"][0]["normalized_text"] = hostile
        data["baseline_review_summary"]["context_question"] = hostile
        data["basis"]["references"][0]["name"] = hostile
        data["limitations"] = [hostile]
        output = self.render(data)
        for active in ("![", "[click]", "<img", "```", "https://", "javascript:", "\u202e"):
            self.assertNotIn(active, output)
        self.assertIn("&#91;map&#93;", output)
        self.assertIn("&#60;img", output)
        self.assertIn("&#96;&#96;&#96;", output)
        self.assertIn("&#38; &#38;&#35;91&#59;", output)
        self.assertIn("&#92;u202e", output)

    def test_output_is_deterministic_and_does_not_mutate_model(self):
        data = fixture()
        saved = copy.deepcopy(data)
        self.assertEqual(self.render(data), self.render(data))
        self.assertEqual(data, saved)

    def test_rejects_non_review_models_and_unknown_states(self):
        for key, value in (("overall_status", "APPROVED"), ("assessment_type", "COMPLIANCE"),
                           ("schema_version", 2), ("identical_source_bytes", "yes")):
            data = fixture()
            data[key] = value
            with self.assertRaises(ValueError):
                self.render(data)
        data = fixture()
        data["requirements"][0]["comparison_status"] = "FIXED"
        with self.assertRaises(ValueError):
            self.render(data)

    def test_rejects_structured_source_fields_instead_of_flattening_them(self):
        data = fixture()
        data["requirements"][0]["baseline"]["source_text"] = ["unexpected"] * 1000
        with self.assertRaises(ValueError):
            self.render(data)

    def test_rejects_oversize_fields_collections_and_utf8_output(self):
        data = fixture()
        data["requirements"][0]["baseline"]["source_text"] = "x" * 8193
        with self.assertRaisesRegex(ValueError, "limit"):
            self.render(data)
        data = fixture()
        data["text_changes"] = [data["text_changes"][0]] * 10001
        with self.assertRaisesRegex(ValueError, "limit"):
            self.render(data)
        data = fixture()
        entry = data["requirements"][0]
        entry["baseline"]["source_text"] = "\U0001f4d0" * 8192
        entry["revised"]["source_text"] = "\U0001f4d0" * 8192
        data["requirements"] = [entry] * 340
        with self.assertRaisesRegex(ValueError, "20 MiB"):
            self.render(data)

    def test_validation_bounds_aggregate_input_before_ignoring_extra_fields(self):
        data = fixture()
        data["unused"] = ["x" * 8192] * 3000
        with self.assertRaisesRegex(ValueError, "20 MiB"):
            self.render(data)

    def test_literal_entity_expansion_is_capped_before_final_join(self):
        data = fixture()
        entry = data["requirements"][0]
        entry["baseline"]["source_text"] = "!" * 8192
        entry["revised"]["source_text"] = "!" * 8192
        data["requirements"] = [entry] * 340
        with self.assertRaisesRegex(ValueError, "Markdown exceeds the 20 MiB UTF-8"):
            self.render(data)

    def test_multibyte_literal_values_survive_utf8_output(self):
        data = fixture()
        data["requirements"][0]["baseline"]["source_text"] = "測量 π 公司"
        output = self.render(data)
        self.assertIn("測量 π 公司", output)
        self.assertLessEqual(len(output.encode("utf-8")), 20 * 1024 * 1024)

    def _real_model(self, scenario):
        from inventory_review import inventory_review
        from revision_comparison import build_comparison

        rules = [{"requirement_id": "SYNTH-SCALE", "evidence_key": "scale",
                  "summary": "Review scale", "check_method": "numerical_scale"}]
        inventories = [{"source_filename": label + ".pdf", "source_sha256": digit * 64,
                        "pages": 1, "status": "TEXT_INVENTORY_ONLY", "spans": [
                            {"text": text, "page": 1, "bbox_points": [10, 20, 100, 40],
                             "page_size_points": [612, 792], "text_angle_degrees": 0}]}
                       for label, digit, text in (("baseline", "1", "SCALE 1:5000"),
                                                  ("revised", "2", "SCALE 1:2500"))]
        reports = []
        for inventory in inventories:
            report = inventory_review(inventory, scenario, rules)
            report.update(source_filename=inventory["source_filename"], pages=1,
                          review_summary={"status": "REVIEW_REQUIRED", "not_checked": ["Manual source inspection remains"]})
            report["requirements"][0].update(candidate_count=None, evidence_status="UNKNOWN",
                                              observation="Conflicting synthetic evidence")
            reports.append(report)
        basis = {"engine_version": "0.6.0", "engine_sha256": "a" * 64,
                 "scenario_sha256": canonical_digest(scenario), "catalogue_sha256": "b" * 64,
                 "references": []}
        basis["basis_sha256"] = canonical_digest(basis)
        return build_comparison(inventories[0], reports[0], inventories[1], reports[1], basis=basis)

    def test_renders_real_comparison_with_unknown_count_and_partial_review_summary(self):
        model = self._real_model({"purpose": "Synthetic renderer integration"})
        output = self.render(model)
        self.assertIn("Comparison state: AMBIGUOUS", output)
        self.assertIn("Candidate count: unknown", output)
        self.assertIn("Manual source inspection remains", output)
        self.assertIn("SCALE 1&#58;2500", output)

    def test_renders_real_model_contexts_with_65_and_200_fields(self):
        for count in (65, 200):
            with self.subTest(fields=count):
                context = {"field" + str(index): "synthetic value" for index in range(count)}
                model = self._real_model(context)
                self.assertEqual(len(model["review_context"]), count)
                output = self.render(model)
                self.assertIn("- field" + str(count - 1) + ": synthetic value", output)

    def test_renders_real_model_context_with_positive_and_negative_1024_bit_integers(self):
        largest = (1 << 1024) - 1
        model = self._real_model({"large": largest, "negative": -largest})
        output = self.render(model)
        self.assertIn("- large: " + str(largest), output)
        self.assertIn("- negative: &#45;" + str(largest), output)

    def test_context_limits_match_producer_object_and_integer_limits(self):
        for context in ({"field" + str(index): "synthetic" for index in range(201)},
                        {"integer": 1 << 1024}):
            with self.subTest(fields=len(context)):
                with self.assertRaises(ValueError):
                    self._real_model(context)
                data = fixture()
                data["review_context"] = context
                data["basis"]["scenario_sha256"] = canonical_digest(context)
                with self.assertRaisesRegex(ValueError, "limit"):
                    self.render(data)


if __name__ == "__main__":
    unittest.main()
