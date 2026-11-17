"""Invented snapshot races; every parser and packet builder remains real."""
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ENGINE = Path(__file__).resolve().parents[1] / 'engine'
sys.path.insert(0, str(ENGINE))
import fitz
import revision_cli
from table_a2_rows import extract_a2_rows


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def synthetic_a2(definition):
    """Invented cells and layout satisfy the extractor's structural contract."""
    with fitz.open() as doc:
        for index in range(18):
            page = doc.new_page(width=1800, height=850)
            if index == 0:
                page.insert_text((25, 25), 'Public Lands Administration Regulation Table A2 '
                                 'October 28, 2026 Alberta Energy Regulator', fontsize=9)
            if not 3 <= index < 17:
                continue
            count = 5 if index == 16 else 10
            height = (5 + count) * 35
            for column in range(28):
                page.draw_line((20 + column * 65, 30), (20 + column * 65, 30 + height))
            for row in range(6 + count):
                page.draw_line((20, 30 + row * 35), (1775, 30 + row * 35))
            for row in range(count):
                number = (index - 3) * 10 + row + 1
                cells = {0: f'{number}.', 3: 'LOC', 7: 'Invented purpose',
                         9: definition, 10: 'No', 13: 'No', 17: 'N/A', 20: 'Sketch'}
                for column, text in cells.items():
                    page.insert_text((23 + column * 65, 50 + (row + 5) * 35),
                                     text, fontsize=7)
        return doc.tobytes()


class RevisionSnapshotInputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plan = self.root / 'invented.pdf'
        with fitz.open() as doc:
            doc.new_page().insert_text((40, 60), 'SCALE 1:5000')
            doc.save(self.plan)
        self.scenario = {'land_class': 'alberta_crown', 'regulator': 'AER',
                         'disposition': 'LOC', 'stage': 'initial', 'plan_type': 'sketch',
                         'purpose': 'Invented purpose', 'applicant_name': 'SNAPSHOT A'}
        self.scenario_path = self.root / 'scenario.json'
        self.scenario_path.write_bytes(canonical(self.scenario))
        self.catalogue = self.root / 'catalogue.json'
        self.catalogue.write_bytes((ENGINE / 'candidate_requirements.json').read_bytes())
        self.markdown = self.root / 'comparison.md'
        self.record = self.root / 'comparison.json'

    def run_api(self, **kwargs):
        revision_cli.run_comparison(self.plan, self.plan, self.markdown, self.record,
                                    self.scenario, self.catalogue, **kwargs)
        return json.loads(self.record.read_text())

    def swap_after_snapshot_restore_before_inspection(self, path, replacement):
        original = path.read_bytes()
        read = revision_cli.read_bounded_file
        inspect = revision_cli.inspect_original_pdf
        captured = False

        def swapped(selected, limit):
            nonlocal captured
            result = read(selected, limit)
            if Path(selected) == path and not captured:
                captured = True
                path.write_bytes(replacement)
            return result

        def restored(selected):
            path.write_bytes(original)
            return inspect(selected)

        return (patch.object(revision_cli, 'read_bounded_file', side_effect=swapped),
                patch.object(revision_cli, 'inspect_original_pdf', side_effect=restored))

    def test_catalogue_definition_and_fingerprint_use_retained_snapshot(self):
        original = self.catalogue.read_bytes()
        data = json.loads(original)
        expected = data['requirements'][0]['summary']
        expected_hash = sha256(canonical(data['requirements'])).hexdigest()
        data['requirements'][0]['summary'] = 'TRANSIENT CATALOGUE B'
        swap, restore = self.swap_after_snapshot_restore_before_inspection(
            self.catalogue, canonical(data))
        with swap, restore:
            result = self.run_api()
        self.assertEqual(self.catalogue.read_bytes(), original)
        self.assertIn({'name': 'catalogue_input', 'sha256': sha256(original).hexdigest()},
                      result['basis']['references'])
        finding = next(row for row in result['requirements']
                       if row['requirement_id'] == data['requirements'][0]['requirement_id'])
        self.assertEqual(finding['requirement_summary'], expected)
        self.assertEqual(result['basis']['catalogue_sha256'], expected_hash)

    def test_cli_scenario_context_and_fingerprint_use_retained_snapshot(self):
        original = self.scenario_path.read_bytes()
        replacement = {**self.scenario, 'applicant_name': 'TRANSIENT SCENARIO B'}
        swap, restore = self.swap_after_snapshot_restore_before_inspection(
            self.scenario_path, canonical(replacement))
        args = [str(self.plan), str(self.plan), '--scenario', str(self.scenario_path),
                '--catalogue', str(self.catalogue), '--output', str(self.markdown),
                '--json-output', str(self.record), '--offline']
        with swap, restore, redirect_stdout(io.StringIO()):
            self.assertEqual(revision_cli.main(args), 0)
        result = json.loads(self.record.read_text())
        expected = {**self.scenario, 'activity': 'LOC'}
        self.assertEqual(self.scenario_path.read_bytes(), original)
        self.assertEqual(result['review_context'], expected)
        self.assertEqual(result['basis']['scenario_sha256'], sha256(canonical(expected)).hexdigest())

    def test_a2_packet_consumes_retained_pdf_snapshot(self):
        reference = self.root / 'invented-a2.pdf'
        original = synthetic_a2('SNAPSHOT A')
        reference.write_bytes(original)
        swap, restore = self.swap_after_snapshot_restore_before_inspection(
            reference, synthetic_a2('TRANSIENT B'))
        review = revision_cli.review_inventory
        supplied_definitions = []

        def capture_review(*args, **kwargs):
            supplied_definitions.append(kwargs['table_a2_rows'][0]['definition'])
            return review(*args, **kwargs)

        with swap, restore, patch.object(revision_cli, 'review_inventory',
                                        side_effect=capture_review):
            result = self.run_api(a2_pdf=reference)
        self.assertEqual(reference.read_bytes(), original)
        self.assertIn({'name': 'table_a2', 'sha256': sha256(original).hexdigest()},
                      result['basis']['references'])
        self.assertEqual(supplied_definitions, ['SNAPSHOT A', 'SNAPSHOT A'])

    def test_a2_parser_accepts_retained_stream_and_keeps_path_api(self):
        reference = self.root / 'invented-a2.pdf'
        original = synthetic_a2('SNAPSHOT A')
        reference.write_bytes(synthetic_a2('PATH B'))
        try:
            rows = extract_a2_rows(original)
        except fitz.FileNotFoundError:
            raise AssertionError('Retained PDF bytes were treated as a filesystem path') from None
        self.assertEqual(len(rows), 135)
        self.assertEqual(rows[0]['definition'], 'SNAPSHOT A')
        self.assertEqual(rows[-1]['row'], 135)
        self.assertEqual(extract_a2_rows(reference)[0]['definition'], 'PATH B')

    def test_strict_scenario_snapshot_rejects_nonfinite_and_depth_overflow(self):
        for raw in (b'{"value":NaN}', b'{"value":1e999}', b'[' * 70 + b'0' + b']' * 70):
            with self.subTest(raw=raw):
                self.scenario_path.write_bytes(raw)
                args = [str(self.plan), str(self.plan), '--scenario', str(self.scenario_path),
                        '--output', str(self.markdown), '--json-output', str(self.record)]
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    revision_cli.main(args)
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(self.record.exists())

    def test_strict_catalogue_snapshot_rejects_invalid_json_before_pdf_inspection(self):
        for raw in (b'{"requirements":[],"requirements":[]}', b'{"value":NaN}',
                    b'{"value":1e999}', b'[' * 70 + b'0' + b']' * 70,
                    b'{"value":"\xff"}', b' ' * (2 * 1024 * 1024 + 1)):
            with self.subTest(prefix=raw[:60]):
                self.catalogue.write_bytes(raw)
                with patch.object(revision_cli, 'inspect_original_pdf') as inspect:
                    with self.assertRaises(ValueError):
                        self.run_api()
                inspect.assert_not_called()
                self.assertFalse(self.record.exists())


if __name__ == '__main__':
    unittest.main()
