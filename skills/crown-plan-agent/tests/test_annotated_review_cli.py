"""Synthetic marked-up review CLI packets; never commit generated PDFs."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from review_cli import main
try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, 'PyMuPDF unavailable')
class AnnotatedReviewCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pdf = self.root / 'synthetic-plan.pdf'
        with fitz.open() as doc:
            page = doc.new_page(width=500, height=700)
            page.insert_text((40, 55), 'SKETCH PLAN SHOWING SYNTHETIC LAND')
            page.insert_text((40, 85), 'SCALE 1:5000')
            page.insert_text((40, 115), 'TOTAL AREA: 0.200 ha')
            doc.save(self.pdf)
        self.source_hash = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.scenario = self.root / 'scenario.json'
        self.scenario.write_text(json.dumps({'land_class': 'alberta_crown',
            'regulator': 'AER', 'disposition': 'LOC', 'stage': 'initial',
            'plan_type': 'sketch', 'purpose': 'Invented purpose', 'subactivity': ''}))
        self.markdown = self.root / 'review.md'
        self.markup = self.root / 'review-copy.pdf'
        self.base_args = [str(self.pdf), '--scenario', str(self.scenario),
                          '--output', str(self.markdown), '--reference-cache', str(self.root / 'empty-cache')]

    def invoke(self, extra=()):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main([*self.base_args, *extra])
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_optional_flag_creates_traceable_private_review_copy(self):
        code, _, error = self.invoke(['--annotated-pdf', str(self.markup)])
        self.assertEqual(code, 0, error)
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), self.source_hash)
        self.assertTrue(self.markdown.is_file())
        with fitz.open(self.markup) as doc:
            self.assertGreater(doc.page_count, 1)
            self.assertTrue(list(doc[0].annots() or []))
        text = self.markdown.read_text()
        self.assertIn('Marked-up PDF', text)
        self.assertIn(self.source_hash, text)
        self.assertIn(hashlib.sha256(self.markup.read_bytes()).hexdigest(), text)

    def test_default_does_not_create_an_extra_pdf(self):
        code, _, error = self.invoke()
        self.assertEqual(code, 0, error)
        self.assertTrue(self.markdown.exists())
        self.assertFalse(self.markup.exists())
        self.assertNotIn('Marked-up PDF', self.markdown.read_text())

    def test_existing_packet_member_is_rejected_before_refresh_or_extraction(self):
        for path in (self.markdown, self.markup):
            with self.subTest(path=path.name):
                path.write_bytes(b'PREEXISTING')
                with patch('review_cli.refresh_table_a2') as refresh, patch('review_cli.extract_pdf') as extract:
                    code, _, error = self.invoke(['--annotated-pdf', str(self.markup), '--refresh-table-a2'])
                self.assertEqual(code, 2)
                self.assertIn('already exists', error.casefold())
                refresh.assert_not_called(); extract.assert_not_called()
                self.assertEqual(path.read_bytes(), b'PREEXISTING')
                self.assertFalse((self.markup if path == self.markdown else self.markdown).exists())
                path.unlink()

    def test_original_cannot_be_the_markup_destination(self):
        code, _, error = self.invoke(['--annotated-pdf', str(self.pdf)])
        self.assertEqual(code, 2)
        self.assertNotIn('unrecognized arguments', error)
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), self.source_hash)
        self.assertFalse(self.markdown.exists())

    def test_skill_directory_is_not_a_private_pdf_destination(self):
        target = Path(__file__).resolve().parents[1] / ('synthetic-' + uuid4().hex + '.pdf')
        self.addCleanup(target.unlink, missing_ok=True)
        code, _, error = self.invoke(['--annotated-pdf', str(target)])
        self.assertEqual(code, 2)
        self.assertIn('outside', error.casefold())
        self.assertFalse(target.exists())
        self.assertFalse(self.markdown.exists())

    def test_dangling_markup_symlink_is_not_followed(self):
        self.markup.symlink_to(self.root / 'do-not-create.pdf')
        code, _, error = self.invoke(['--annotated-pdf', str(self.markup)])
        self.assertEqual(code, 2)
        self.assertIn('already exists', error.casefold())
        self.assertTrue(self.markup.is_symlink())
        self.assertFalse((self.root / 'do-not-create.pdf').exists())
        self.assertFalse(self.markdown.exists())

    def test_publication_failure_leaves_no_incomplete_packet(self):
        import os
        real_link = os.link
        def link(source, destination, *args, **kwargs):
            if Path(destination) == self.markup:
                raise OSError('Synthetic packet publication failure')
            return real_link(source, destination, *args, **kwargs)
        with patch('artifact_publication.os.link', side_effect=link):
            code, _, error = self.invoke(['--annotated-pdf', str(self.markup)])
        self.assertEqual(code, 2)
        self.assertIn('Synthetic packet publication failure', error)
        self.assertFalse(self.markdown.exists())
        self.assertFalse(self.markup.exists())
        self.assertFalse(list(self.root.glob('.cpa-review-*')))
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), self.source_hash)

    def test_source_change_after_render_cancels_publication(self):
        from pdf_markup import build_annotated_pdf
        changed_bytes = b'SYNTHETIC EXTERNAL SOURCE CHANGE'
        def render(*args, **kwargs):
            prepared = build_annotated_pdf(*args, **kwargs)
            self.pdf.write_bytes(changed_bytes)
            return prepared
        with patch('pdf_markup.build_annotated_pdf', side_effect=render):
            code, _, error = self.invoke(['--annotated-pdf', str(self.markup)])
        self.assertEqual(code, 2)
        self.assertIn('Source PDF changed', error)
        self.assertEqual(self.pdf.read_bytes(), changed_bytes)
        self.assertFalse(self.markdown.exists())
        self.assertFalse(self.markup.exists())


if __name__ == '__main__':
    unittest.main()
