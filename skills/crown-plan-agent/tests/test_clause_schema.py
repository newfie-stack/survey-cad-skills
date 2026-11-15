"""Strict invented catalogue boundaries; no real manual is enabled here."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from clause_schema import (ADAPTER_IDS, CONTEXT_FIELDS, is_valid_fact_value,
                           load_bounded_json, load_clause_catalogue,
                           validate_clause_catalogue, validate_fact_definitions,
                           validate_predicate)

FIXTURES = Path(__file__).resolve().parent


class ClauseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = json.loads((FIXTURES / "synthetic_clause_catalogue.json").read_text())

    def definitions(self):
        return {fact["id"]: fact for fact in self.catalogue["facts"]}

    def test_invented_catalogue_loads_without_promoting_authority_or_mutating(self):
        before = copy.deepcopy(self.catalogue)
        result = validate_clause_catalogue(self.catalogue)
        self.assertIs(result, self.catalogue)
        self.assertEqual(result, before)
        self.assertEqual(result["source"]["classification"], "INVENTED")
        self.assertEqual(result["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(load_clause_catalogue(FIXTURES / "synthetic_clause_catalogue.json"), before)
        self.assertIsInstance(ADAPTER_IDS, frozenset)
        self.assertIsInstance(CONTEXT_FIELDS, frozenset)

    def test_unknown_keys_and_forged_source_status_fail_at_nested_boundaries(self):
        paths = [(), ("source",), ("facts", 0), ("clauses", 0),
                 ("clauses", 0, "citation"), ("clauses", 0, "checks", 0),
                 ("clauses", 4, "overrides", 0)]
        for path in paths:
            data = copy.deepcopy(self.catalogue)
            target = data
            for key in path:
                target = target[key]
            target["unexpected"] = True
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        self.catalogue["source_status"] = "VERIFIED_CURRENT"
        with self.assertRaises(ValueError):
            validate_clause_catalogue(self.catalogue)

    def test_source_fields_are_typed_and_bounded_without_inferring_currency(self):
        invalid = [("version_date", "2000-02-30"), ("version_date", "20000101"),
                   ("url", "http://example.org/manual"), ("url", "https://name:secret@example.org/a"),
                   ("url", "https://localhost/manual"), ("url", "https://127.0.0.1/manual"),
                   ("url", " https://example.org/manual"),
                   ("url", "https://example.org/a\nmanual"), ("url", "https://0177.0.0.1/manual"),
                   ("page_count", True), ("page_count", 0), ("classification", "VERIFIED")]
        for field, value in invalid:
            data = copy.deepcopy(self.catalogue)
            data["source"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_clause_catalogue(data)

    def test_fact_definition_types_domains_and_unique_ids_are_checked(self):
        invalid = [("type", "float"), ("minimum", 0), ("maximum", "-1"),
                   ("allowed_values", ["one"]), ("provenance_required", 1),
                   ("purpose", "law_verified")]
        for field, value in invalid:
            data = copy.deepcopy(self.catalogue)
            data["facts"][1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        for mutate in (lambda data: data["facts"].append(copy.deepcopy(data["facts"][0])),
                       lambda data: data["facts"][0].update(unit="m"),
                       lambda data: data["facts"][2].update(provenance_required=False)):
            data = copy.deepcopy(self.catalogue)
            mutate(data)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                validate_clause_catalogue(data)

    def test_fact_value_scalar_domains_do_not_coerce(self):
        definitions = self.definitions()
        boolean = definitions["has_details"]
        decimal = definitions["length_m"]
        integer = {**decimal, "type": "integer", "minimum": 1, "maximum": 3}
        enum = {**boolean, "type": "enum", "allowed_values": ["small", "large"]}
        cases = [(boolean, False, True), (boolean, 0, False), (boolean, "false", False),
                 (integer, 1, True), (integer, 3, True), (integer, True, False),
                 (integer, 1.0, False), (integer, 0, False), (integer, 4, False),
                 (decimal, "0", True), (decimal, "10.01", True), (decimal, "-1", False),
                 (decimal, 10, False), (decimal, True, False), (decimal, "01", False),
                 (decimal, "+1", False), (decimal, "1e1", False), (decimal, "NaN", False),
                 (decimal, " 1", False), (decimal, "1.", False),
                 (decimal, "1" * 50, True), (decimal, "1" * 51, False),
                 (enum, "small", True), (enum, "other", False), (enum, True, False)]
        for definition, value, expected in cases:
            with self.subTest(type=definition["type"], value=value):
                self.assertIs(is_valid_fact_value(definition, value), expected)

    def test_optional_exclusive_bounds_are_numeric_domain_constraints(self):
        decimal = self.catalogue["facts"][1]
        self.assertTrue(is_valid_fact_value(decimal, "0"))
        decimal["exclusive_minimum"] = True
        self.assertFalse(is_valid_fact_value(decimal, "0"))
        self.assertTrue(is_valid_fact_value(decimal, "0.0001"))
        validate_clause_catalogue(self.catalogue)
        integer = {**decimal, "type": "integer", "minimum": 0, "maximum": 3,
                   "exclusive_maximum": True}
        self.assertFalse(is_valid_fact_value(integer, 0))
        self.assertTrue(is_valid_fact_value(integer, 1))
        self.assertFalse(is_valid_fact_value(integer, 3))
        for field, value in (("exclusive_minimum", 1), ("exclusive_maximum", False)):
            data = copy.deepcopy(self.catalogue)
            data["facts"][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        self.catalogue["facts"][0]["exclusive_minimum"] = False
        with self.assertRaises(ValueError):
            validate_clause_catalogue(self.catalogue)

    def test_predicates_validate_references_literals_and_operator_shape(self):
        invalid = [{"const": 1}, {"const": True, "not": {"const": False}},
                   {"all": []}, {"any": "condition"}, {"unknown": True},
                   {"eq": {"fact": "missing", "value": True}},
                   {"eq": {"fact": "has_details", "value": "true"}},
                   {"gt": {"fact": "has_details", "value": True}},
                   {"eq": {"context": "unknown", "value": "x"}},
                   {"eq": {"context": "plan_type", "value": None}},
                   {"gt": {"context": "plan_type", "value": "survey_plan"}},
                   {"eq": {"fact": "length_m", "context": "plan_type", "value": "1"}},
                   {"in": {"fact": "length_m", "value": ["1"]}},
                   {"in": {"fact": "length_m", "values": []}},
                   {"in": {"fact": "length_m", "values": ["1", "1.0"]}}]
        for predicate in invalid:
            with self.subTest(predicate=predicate), self.assertRaises(ValueError):
                validate_predicate(predicate, self.definitions())
        # Literal compatibility is independent of fact-input bounds.
        self.catalogue["facts"][1]["exclusive_minimum"] = True
        validate_predicate({"gt": {"fact": "length_m", "value": "0"}}, self.definitions())
        validate_predicate({"in": {"context": "plan_type", "values": ["future_type"]}}, self.definitions())

    def test_predicate_node_depth_and_string_limits_apply_to_direct_api(self):
        predicate = {"const": True}
        for _ in range(15):
            predicate = {"not": predicate}
        validate_predicate(predicate, self.definitions())
        with self.assertRaises(ValueError):
            validate_predicate({"not": predicate}, self.definitions())
        validate_predicate({"all": [{"const": True}] * 255}, self.definitions())
        with self.assertRaises(ValueError):
            validate_predicate({"all": [{"const": True}] * 256}, self.definitions())
        with self.assertRaises(ValueError):
            validate_predicate({"eq": {"context": "plan_type", "value": "x" * 4097}}, self.definitions())

    def test_clause_ids_citations_kinds_checks_and_adapters_are_strict(self):
        changes = [("id", "not-numbered"), ("kind", "mandatory"),
                   ("citation", {"section": "1.1.2", "page": 1}),
                   ("citation", {"section": "1.1.1", "page": 4}),
                   ("citation", {"section": "1.1.1", "page": True}), ("checks", [])]
        for field, value in changes:
            data = copy.deepcopy(self.catalogue)
            data["clauses"][0][field] = value
            if field == "id":
                data["clauses"][0]["citation"]["section"] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        for field, value in [("kind", "mixed"), ("questions", []),
                             ("adapter_links", ["UNKNOWN"]),
                             ("adapter_links", ["CANDIDATE-PLAN-HEADING"] * 2),
                             ("id", "x" * 129)]:
            data = copy.deepcopy(self.catalogue)
            data["clauses"][1 if field == "id" else 0]["checks"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        data["clauses"][1]["checks"][0]["id"] = "ordinary_heading"
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        data["clauses"][4]["checks"].append(copy.deepcopy(data["clauses"][0]["checks"][1]))
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)

    def test_optional_and_permission_clauses_cannot_hide_required_children(self):
        for clause_kind in ("optional", "permission"):
            data = copy.deepcopy(self.catalogue)
            data["clauses"][2]["kind"] = clause_kind
            data["clauses"][2]["checks"][0]["kind"] = "required"
            with self.subTest(kind=clause_kind), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        # A qualified source-required clause may contain atomic guidance.
        self.catalogue["clauses"][2]["kind"] = "conditional_required"
        validate_clause_catalogue(self.catalogue)

    def test_definition_mapping_and_enum_metadata_are_validated_for_direct_callers(self):
        mapping = self.definitions()
        self.assertIs(validate_fact_definitions(mapping), mapping)
        with self.assertRaises(ValueError):
            validate_fact_definitions({"different_id": mapping["has_details"]})
        enum = {**mapping["has_details"], "type": "enum", "allowed_values": ["one", "two"]}
        validate_fact_definitions({enum["id"]: enum})
        for values in (None, [], ["one", "one"], [1]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_fact_definitions({enum["id"]: {**enum, "allowed_values": values}})
        with self.assertRaises(ValueError):
            validate_predicate({"eq": {"fact": "has_details", "value": "three"}},
                               {enum["id"]: enum})
        self.assertFalse(is_valid_fact_value({}, True))
        self.assertFalse(is_valid_fact_value(None, True))

    def test_fact_ids_cannot_collide_with_internal_context_issue_names(self):
        fact = {**self.catalogue["facts"][0], "id": "context:review_scope"}
        with self.assertRaises(ValueError):
            validate_fact_definitions({fact["id"]: fact})
        self.catalogue["facts"].append(fact)
        with self.assertRaises(ValueError):
            validate_clause_catalogue(self.catalogue)
        self.assertFalse(is_valid_fact_value(fact, True))

    def test_override_targets_and_controller_graph_fail_closed(self):
        for targets in (["missing"], ["compiled_exemption"],
                        ["ordinary_heading", "ordinary_heading"], ["compiled_certificate"]):
            data = copy.deepcopy(self.catalogue)
            data["clauses"][4]["overrides"][0]["targets"] = targets
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        data["clauses"][4]["overrides"].append({"action": "replace", "targets": ["ordinary_heading"]})
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        data["clauses"][0]["overrides"] = [{"action": "replace", "targets": ["compiled_exemption"]}]
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        # Distinct controllers may share a target; the resolver handles conflicts.
        self.catalogue["clauses"][5]["overrides"][0]["targets"] = ["ordinary_heading"]
        validate_clause_catalogue(self.catalogue)

    def test_resource_limits_reject_large_and_cyclic_programmatic_data(self):
        data = copy.deepcopy(self.catalogue)
        data["facts"] += [{**data["facts"][0], "id": f"new_fact_{i}"} for i in range(198)]
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        template = data["clauses"][0]
        data["clauses"] = []
        for i in range(501):
            clause = copy.deepcopy(template)
            clause["id"] = clause["citation"]["section"] = f"1.{i + 1}.1"
            for j, check in enumerate(clause["checks"]):
                check["id"] = f"check_{i}_{j}"
            data["clauses"].append(clause)
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        data["clauses"][0]["checks"] = [{**data["clauses"][0]["checks"][0],
                                          "id": f"extra_check_{i}"} for i in range(4999)]
        data["clauses"][0]["checks"].extend([
            {**data["clauses"][0]["checks"][0], "id": "ordinary_heading"},
            {**data["clauses"][0]["checks"][0], "id": "ordinary_certificate"}])
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        data = copy.deepcopy(self.catalogue)
        clause = data["clauses"][0]
        data["clauses"] = []
        for i in range(499):
            item = copy.deepcopy(clause)
            item["id"] = item["citation"]["section"] = f"1.{i + 1}.1"
            item["checks"] = [{**item["checks"][0], "id": f"check_{i}",
                               "questions": ["x" * 4096]}]
            item["summary"] = "x" * 4096
            data["clauses"].append(item)
        with self.assertRaises(ValueError):
            validate_clause_catalogue(data)
        cyclic = copy.deepcopy(self.catalogue)
        cyclic["clauses"][0]["when"]["not"] = cyclic["clauses"][0]["when"]
        with self.assertRaises(ValueError):
            validate_clause_catalogue(cyclic)

    def test_loader_rejects_duplicate_keys_nonfinite_json_and_oversize_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue.json"
            text = json.dumps(self.catalogue)
            path.write_text(text.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1))
            with self.assertRaises(ValueError):
                load_clause_catalogue(path)
            path.write_text(text.replace('"minimum": null', '"minimum": NaN', 1))
            with self.assertRaises(ValueError):
                load_clause_catalogue(path)
            path.write_text(text + " " * (2 * 1024 * 1024))
            with self.assertRaises(ValueError):
                load_clause_catalogue(path)

    def test_generic_bounded_json_loader_is_not_a_catalogue_or_fact_coercer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "facts.json"
            data = {"length_m": {"value": "10.01", "provenance": None}}
            path.write_text(json.dumps(data))
            self.assertEqual(load_bounded_json(path), data)
            for text in ('{"fact":{"value":true,"value":false}}', 'NaN', 'Infinity', '-Infinity'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    load_bounded_json(path)
            path.write_bytes(b'"\xff"')
            with self.assertRaises(ValueError):
                load_bounded_json(path)


if __name__ == "__main__":
    unittest.main()
