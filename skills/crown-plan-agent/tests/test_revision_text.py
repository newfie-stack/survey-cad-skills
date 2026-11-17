"""Synthetic literal-span comparisons; these do not assess drawing geometry."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
try:
    import revision_text
except ModuleNotFoundError as exc:
    if exc.name != "revision_text":
        raise
    revision_text = None


def span(text, *, page=1, box=None):
    return {"text": text, "page": page,
            "bbox_points": [10, 20, 100, 35] if box is None else box,
            "page_size_points": [612, 792], "text_angle_degrees": 0}


def inventory(*spans, pages=2):
    return {"pages": pages, "spans": list(spans)}


class RevisionTextTests(unittest.TestCase):
    def compare(self, baseline, revised):
        self.assertIsNotNone(revision_text, "Literal text comparison is not implemented")
        return revision_text.compare_text_inventories(baseline, revised)

    def test_added_removed_and_repeated_count_groups_have_deterministic_ids(self):
        result = self.compare(inventory(span("OLD"), span("COUNT")),
                              inventory(span("NEW"), span("COUNT"), span("COUNT", page=2)))
        self.assertEqual([(r["change_id"], r["normalized_text"], r["change_status"],
                           r["before_count"], r["after_count"]) for r in result],
                         [("T00001", "COUNT", "COUNT_CHANGED", 1, 2),
                          ("T00002", "NEW", "ADDED", 0, 1),
                          ("T00003", "OLD", "REMOVED", 1, 0)])
        self.assertEqual(result[0]["revised_occurrences"][1]["page"], 2)
        self.assertEqual(result[1]["baseline_occurrences"], [])
        self.assertEqual(result[2]["revised_occurrences"], [])

    def test_whitespace_only_normalization_preserves_every_raw_occurrence(self):
        result = self.compare(inventory(), inventory(span(" \tSCALE\n1:5000 "),
                                                     span("SCALE\u00a01:5000")))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["normalized_text"], "SCALE 1:5000")
        self.assertEqual(result[0]["after_count"], 2)
        self.assertCountEqual([s["raw_text"] for s in result[0]["revised_occurrences"]],
                              [" \tSCALE\n1:5000 ", "SCALE\u00a01:5000"])
        self.assertEqual(self.compare(inventory(span("A\tB")), inventory(span(" A B "))), [])

    def test_case_numbers_punctuation_and_unicode_are_never_folded_or_paired(self):
        result = self.compare(inventory(span("Name 1.00 é"), span("Ａ")),
                              inventory(span("name 1.0 e\u0301"), span("A")))
        self.assertEqual([(r["normalized_text"], r["change_status"]) for r in result],
                         [("A", "ADDED"), ("Name 1.00 é", "REMOVED"),
                          ("name 1.0 e\u0301", "ADDED"), ("Ａ", "REMOVED")])

    def test_page_insertion_reordering_movement_and_rotation_do_not_edit_text(self):
        before = inventory(span("A"), span("B", page=2))
        moved = span("A", page=3, box=[100, 150, 200, 170])
        moved["text_angle_degrees"] = 90
        after = inventory(span("B", page=1), moved, pages=3)
        self.assertEqual(self.compare(before, after), [])

    def test_fragmented_spans_are_inventory_changes_without_fuzzy_pairing(self):
        result = self.compare(inventory(span("ABC DEF")), inventory(span("ABC"), span("DEF")))
        self.assertEqual([(r["normalized_text"], r["change_status"]) for r in result],
                         [("ABC", "ADDED"), ("ABC DEF", "REMOVED"), ("DEF", "ADDED")])

    def test_lost_text_layer_retains_all_old_occurrences_as_removed(self):
        result = self.compare(inventory(span("LABEL"), span("LABEL")), inventory())
        self.assertEqual((result[0]["change_status"], result[0]["before_count"],
                          result[0]["after_count"]), ("REMOVED", 2, 0))
        self.assertEqual(len(result[0]["baseline_occurrences"]), 2)

    def test_occurrences_are_source_bound_and_inputs_and_output_do_not_alias(self):
        source = inventory(span("LABEL", page=2))
        before = deepcopy(source)
        item = self.compare(inventory(), source)[0]["revised_occurrences"][0]
        self.assertEqual(item, {"raw_text": "LABEL", "page": 2,
                               "bbox_points": [10.0, 20.0, 100.0, 35.0],
                               "page_size_points": [612.0, 792.0],
                               "text_angle_degrees": 0.0,
                               "location_reason": "VALID_SOURCE_LOCATION"})
        self.assertEqual(source, before)
        item["bbox_points"][0] = 50
        self.assertEqual(source, before)

    def test_input_span_order_does_not_change_occurrence_or_group_order(self):
        source = inventory(span(" B ", page=2), span("B", page=1),
                           span("A"), span("B", page=1))
        reversed_source = deepcopy(source)
        reversed_source["spans"].reverse()
        self.assertEqual(self.compare(inventory(), source), self.compare(inventory(), reversed_source))

    def test_missing_page_dimensions_keep_text_but_not_invented_coordinates(self):
        item = span("UNLOCATED")
        item.pop("page_size_points")
        occurrence = self.compare(inventory(), inventory(item))[0]["revised_occurrences"][0]
        self.assertEqual(occurrence["raw_text"], "UNLOCATED")
        self.assertEqual(occurrence["page"], 1)
        self.assertIsNone(occurrence["bbox_points"])
        self.assertIsNone(occurrence["page_size_points"])
        self.assertIsNone(occurrence["text_angle_degrees"])
        self.assertTrue(occurrence["location_reason"])

    def test_bad_page_box_dimensions_or_angle_keep_unlocated_raw_text(self):
        cases = [("page", True), ("page", 0), ("page", 3), ("page", "1"),
                 ("bbox_points", None), ("bbox_points", [1, 2, 3]),
                 ("bbox_points", [1, 2, 1, 4]), ("bbox_points", [-1, 2, 3, 4]),
                 ("bbox_points", [1, 2, 700, 4]), ("bbox_points", [True, 2, 3, 4]),
                 ("bbox_points", [1, 2, float("nan"), 4]),
                 ("bbox_points", [1, 2, float("inf"), 4]),
                 ("page_size_points", [0, 792]), ("page_size_points", [612, float("inf")]),
                 ("page_size_points", [612, 10 ** 1000]),
                 ("text_angle_degrees", float("nan")), ("text_angle_degrees", True)]
        for key, value in cases:
            with self.subTest(key=key, value=str(value)[:100]):
                item = span("KEPT")
                item[key] = value
                occurrence = self.compare(inventory(), inventory(item))[0]["revised_occurrences"][0]
                self.assertEqual(occurrence["raw_text"], "KEPT")
                for field in ("bbox_points", "page_size_points", "text_angle_degrees"):
                    self.assertIsNone(occurrence[field])
                self.assertNotEqual(occurrence["location_reason"], "VALID_SOURCE_LOCATION")
                json.dumps(occurrence, allow_nan=False)

    def test_missing_optional_angle_does_not_invent_orientation(self):
        item = span("LABEL")
        item.pop("text_angle_degrees")
        occurrence = self.compare(inventory(), inventory(item))[0]["revised_occurrences"][0]
        self.assertEqual(occurrence["bbox_points"], [10.0, 20.0, 100.0, 35.0])
        self.assertIsNone(occurrence["text_angle_degrees"])

    def test_unknown_explicit_coordinate_frame_cannot_be_used_as_pdf_bounds(self):
        item = span("KEPT")
        item["coordinate_frame"] = "SURVEY_METRES"
        occurrence = self.compare(inventory(), inventory(item))[0]["revised_occurrences"][0]
        self.assertIsNone(occurrence["bbox_points"])
        self.assertEqual(occurrence["raw_text"], "KEPT")

    def test_malformed_inventory_or_span_is_rejected_without_silent_text_loss(self):
        bad = [None, [], {}, {"pages": True, "spans": []}, {"pages": 101, "spans": []},
               {"pages": 1, "spans": None}, inventory(None), inventory({"text": 123}),
               inventory({"text": ""})]
        for source in bad:
            for side in (0, 1):
                with self.subTest(source=source, side=side):
                    pair = [inventory(), inventory()]
                    pair[side] = source
                    with self.assertRaises((ValueError, TypeError)):
                        self.compare(*pair)

    def test_raw_text_overflow_is_rejected_before_whitespace_normalization(self):
        self.assertEqual(len(self.compare(inventory(), inventory(span("X" * 8192)))), 1)
        for value in ("X" * 8193, " " * 8192 + "X"):
            with self.subTest(kind=value[-1]):
                with self.assertRaisesRegex(ValueError, "[Tt]ext.*limit"):
                    self.compare(inventory(), inventory(span(value)))

    def test_per_source_span_limit_is_checked_before_processing_spans(self):
        for side in (0, 1):
            pair = [inventory(), inventory()]
            pair[side]["spans"] = [None] * 200001
            with self.assertRaisesRegex(ValueError, "[Ss]pan.*limit"):
                self.compare(*pair)

    def test_per_source_group_limit_is_incremental(self):
        items = [span(str(i)) for i in range(20001)] + [{"text": None}]
        for side in (0, 1):
            pair = [inventory(), inventory()]
            pair[side]["spans"] = items
            with self.assertRaisesRegex(ValueError, "[Gg]roup.*limit"):
                self.compare(*pair)

    def test_group_limit_allows_twenty_thousand_unchanged_groups(self):
        source = inventory(*[span(str(i)) for i in range(20000)])
        self.assertEqual(self.compare(source, source), [])

    def test_changed_group_limit_rejects_instead_of_truncating(self):
        source = inventory(*[span(str(i)) for i in range(10000)])
        self.assertEqual(len(self.compare(inventory(), source)), 10000)
        source["spans"].append(span("EXCESS"))
        with self.assertRaisesRegex(ValueError, "[Cc]hanged.*limit"):
            self.compare(inventory(), source)
        with self.assertRaisesRegex(ValueError, "[Cc]hanged.*limit"):
            self.compare(source, inventory())


if __name__ == "__main__":
    unittest.main()
