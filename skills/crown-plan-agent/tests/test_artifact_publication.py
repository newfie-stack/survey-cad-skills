"""Exclusive multi-output publication with synthetic byte payloads only."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
try:
    from artifact_publication import publish_artifacts
except ModuleNotFoundError as exc:
    if exc.name != 'artifact_publication':
        raise
    publish_artifacts = None


class ArtifactPublicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def publish(self, artifacts):
        self.assertIsNotNone(publish_artifacts, 'Exclusive review-packet publication is not implemented')
        return publish_artifacts(artifacts)

    def test_both_complete_outputs_are_created_without_staging_files(self):
        outputs = {self.root / 'review.md': b'# Invented review',
                   self.root / 'review.pdf': b'%PDF-invented-payload'}
        self.publish(outputs)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()},
                         {p.name: content for p, content in outputs.items()})

    def test_existing_output_is_preserved_without_creating_other_outputs(self):
        existing = self.root / 'review.pdf'
        existing.write_bytes(b'PREEXISTING')
        with self.assertRaises(FileExistsError):
            self.publish({self.root / 'review.md': b'new', existing: b'replacement'})
        self.assertEqual(existing.read_bytes(), b'PREEXISTING')
        self.assertEqual(list(self.root.iterdir()), [existing])

    def test_second_publication_failure_removes_only_owned_outputs(self):
        import os
        real_link = os.link
        first, second = self.root / 'review.md', self.root / 'review.pdf'
        def link(source, destination, *args, **kwargs):
            if Path(destination) == second:
                raise OSError('Synthetic filesystem publication failure')
            return real_link(source, destination, *args, **kwargs)
        self.assertIsNotNone(publish_artifacts)
        with patch('artifact_publication.os.link', side_effect=link):
            with self.assertRaises(OSError):
                self.publish({first: b'markdown', second: b'pdf'})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_racing_output_is_not_overwritten_or_removed(self):
        import os
        real_link = os.link
        first, second = self.root / 'review.md', self.root / 'review.pdf'
        def link(source, destination, *args, **kwargs):
            if Path(destination) == second:
                second.write_bytes(b'OTHER WRITER')
                raise FileExistsError('Synthetic competing writer')
            return real_link(source, destination, *args, **kwargs)
        self.assertIsNotNone(publish_artifacts)
        with patch('artifact_publication.os.link', side_effect=link):
            with self.assertRaises(FileExistsError):
                self.publish({first: b'markdown', second: b'pdf'})
        self.assertEqual(second.read_bytes(), b'OTHER WRITER')
        self.assertEqual(list(self.root.iterdir()), [second])

    def test_dangling_symlink_destination_is_rejected(self):
        link = self.root / 'review.pdf'
        link.symlink_to(self.root / 'absent.pdf')
        with self.assertRaises(FileExistsError):
            self.publish({self.root / 'review.md': b'markdown', link: b'pdf'})
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.root / 'review.md').exists())

    def test_aliases_and_nonbyte_payloads_fail_before_any_output(self):
        for outputs in ({self.root / 'a.md': b'x', self.root / 'child/../a.md': b'y'},
                        {self.root / 'a.md': 'not bytes'}):
            with self.subTest(outputs=list(map(str, outputs))):
                with self.assertRaises((TypeError, ValueError)):
                    self.publish(outputs)
                self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
