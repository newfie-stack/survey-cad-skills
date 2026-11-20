"""Keep the published former-holdout fixtures reproducible and answer-free."""
import hashlib
import importlib.util
import json
import platform
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


class UnfamiliarLayoutFixtureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("unfamiliar_layouts"),
                             "Former-holdout fixture generator is not published")
        import unfamiliar_layouts
        self.factory = unfamiliar_layouts
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_all_eight_packets_are_renderable_reproducible_and_have_no_answer_fields(self):
        self.assertEqual(set(self.factory.CASE_IDS), {"01", "02", "03", "04", "05", "06", "07", "08"})
        self.assertEqual(set(self.factory.INITIAL_CASE_IDS), {"01", "02", "03", "04", "05", "06"})
        self.assertEqual(set(self.factory.RESERVED_CASE_IDS), {"07", "08"})
        dimensions, rotations, raster_pages = set(), set(), 0
        for cid in self.factory.CASE_IDS:
            with self.subTest(case=cid):
                outputs = []
                for repeat in ("a", "b"):
                    folder = self.root / f"{cid}-{repeat}"
                    meta = self.factory.write_case(folder, cid)
                    self.assertEqual(set(p.name for p in folder.iterdir()), {"plan.pdf", "job-brief.md", "REVIEW.md"})
                    self.assertEqual(meta["case_id"], cid)
                    actual = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                              for name in ("plan.pdf", "job-brief.md", "REVIEW.md")}
                    self.assertEqual(meta["sha256"], actual)
                    outputs.append(actual)
                    for name in ("job-brief.md", "REVIEW.md"):
                        text = (folder / name).read_text()
                        for field in ("known_defects", "defect_ids", "expected_verdict", "frozen-truth"):
                            self.assertNotIn(field, text)
                self.assertEqual(outputs[0], outputs[1])
                with pymupdf.open(self.root / f"{cid}-a" / "plan.pdf") as document:
                    self.assertGreaterEqual(len(document), 1)
                    self.assertTrue(any(word in document[0].get_text().upper() for word in ("INVENTED", "SYNTHETIC")))
                    for page in document:
                        dimensions.add((page.rect.width, page.rect.height))
                        rotations.add(page.rotation)
                        raster_pages += bool(page.get_images())
                        pixels = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5))
                        self.assertGreater(pixels.width * pixels.height, 0)
        self.assertGreaterEqual(len(dimensions), 3)
        self.assertTrue(rotations - {0})
        self.assertGreaterEqual(raster_pages, 2)

    @unittest.skipUnless(
        platform.system() == "Linux" and platform.machine() == "x86_64"
        and sys.version_info[:2] == (3, 12) and pymupdf.__version__ == "2.1"
        and pymupdf.VersionFitz == "1.28.6",
        "Study PDF byte identity was recorded on Linux x86_64, Python 3.12, "
        "PyMuPDF 2.1 and MuPDF 1.28.6.",
    )
    def test_packets_match_frozen_study_hashes(self):
        path = Path(__file__).parent / "fixtures" / "unfamiliar_layouts_truth.json"
        truth = json.loads(path.read_text())
        pdf_hashes = {case["case_id"]: case["source_sha256"] for case in truth["cases"]}
        # These hashes come from the pre-review input index. Paired drawings share a brief.
        briefs = [
            (("01", "04"), "99afd74866d70298b0abb8780f2497e4cea2ee1b781c4b9b815ec95c38e597a9"),
            (("02", "06"), "e2c4e377638bc1da9ff5223f1c10f6c7d1dddab268e5a11b69f45d40d3ad4251"),
            (("03", "05"), "c9f044d9bd86c408042a52d5332c6b4289c4a1bf3832e5f3932074c0fa283320"),
            (("07", "08"), "17708972d2c50a84779c3843fb5b228921d7e11566356a365b7580f5b216c806"),
        ]
        review_hash = "f7edebe5669ebc45be63cfab7bfaf6f545e9285e22d3fab292b02b508476005d"
        for cases, brief_hash in briefs:
            for case in cases:
                packet = self.root / case
                self.factory.write_case(packet, case)
                expected = {"plan.pdf": pdf_hashes[case], "job-brief.md": brief_hash,
                            "REVIEW.md": review_hash}
                for name, digest in expected.items():
                    with self.subTest(case=case, source=name):
                        self.assertEqual(hashlib.sha256((packet / name).read_bytes()).hexdigest(), digest)

    def test_paired_job_expectations_do_not_reveal_which_version_has_errors(self):
        for first, second in (("01", "04"), ("02", "06"), ("03", "05"), ("07", "08")):
            with self.subTest(pair=(first, second)):
                a, b = self.root / first, self.root / second
                self.factory.write_case(a, first)
                self.factory.write_case(b, second)
                self.assertEqual((a / "job-brief.md").read_bytes(), (b / "job-brief.md").read_bytes())
                self.assertEqual((a / "REVIEW.md").read_bytes(), (b / "REVIEW.md").read_bytes())

    def printed_pages(self, case_id):
        packet = self.root / case_id
        self.factory.write_case(packet, case_id)
        with pymupdf.open(packet / "plan.pdf") as document:
            return [" ".join(page.get_text().split()) for page in document]

    def test_printed_route_identifier_and_crossing_note(self):
        for case, route_id, register in (("03", "LOC-RG-471", "UR-59148"),
                                        ("05", "LOC-RG-417", "UR-59184")):
            with self.subTest(case=case):
                sheet, = self.printed_pages(case)
                self.assertIn(f"PROJECT RG-17 ROUTE ID {route_id} ISSUE R2", sheet)
                self.assertIn(f"Crossing notes 4. C1 crosses utility register {register}.", sheet)

    def test_printed_lease_revision_and_area_schedule(self):
        for case, gate_rev, net in (("01", "C3", "4.150"), ("04", "C2", "4.250")):
            with self.subTest(case=case):
                overview, gate, schedule = self.printed_pages(case)
                for index, (sheet, rev) in enumerate(((overview, "C3"), (gate, gate_rev),
                                                       (schedule, "C3")), start=1):
                    self.assertIn("Issue history C2 Earlier office issue", sheet)
                    self.assertIn(f"MSL-HF-296 CURRENT REV {rev} SHEET {index} of 3", sheet)
                self.assertIn(f"Gross lease 4.800 Excluded 0.650 Net lease {net}", schedule)
                self.assertIn("REFERENCE PARCEL / hectares Gross 1.400 Excluded 0.000 Net 1.400",
                              schedule)

    def test_printed_west_plot_label_and_service_detail_scale(self):
        for case, west_label, detail_scale in (("07", "6.250", "1:500"), ("08", "6.520", "1:750")):
            with self.subTest(case=case):
                sheet, = self.printed_pages(case)
                self.assertIn("LAND SCHEDULE West plot 6.250 ha Service plot 1.750 ha "
                              "Combined 8.000 ha", sheet)
                self.assertIn(f"INDEX / 1:2,500 West plot {west_label} ha", sheet)
                self.assertIn(f"SERVICE DETAIL / {detail_scale} 17,500 sq m", sheet)

    def test_unknown_case_does_not_write_a_packet(self):
        destination = self.root / "invalid"
        with self.assertRaises(ValueError):
            self.factory.write_case(destination, "unknown")
        self.assertFalse(destination.exists())

    def test_existing_packet_is_preserved(self):
        destination = self.root / "packet"
        self.factory.write_case(destination, "01")
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
        with self.assertRaises(FileExistsError):
            self.factory.write_case(destination, "04")
        self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir()}, before)

    def test_published_truth_retains_all_cases_and_separate_trial_phases(self):
        path = Path(__file__).parent / "fixtures" / "unfamiliar_layouts_truth.json"
        truth = json.loads(path.read_text())
        self.assertEqual({c["case_id"] for c in truth["cases"]}, set(self.factory.CASE_IDS))
        self.assertEqual({c["case_id"] for c in truth["cases"] if c["phase"] == "initial"},
                         set(self.factory.INITIAL_CASE_IDS))
        self.assertEqual({c["case_id"] for c in truth["cases"] if c["phase"] == "reserved"},
                         set(self.factory.RESERVED_CASE_IDS))
        for case in truth["cases"]:
            self.assertEqual(len(case["source_sha256"]), 64)
            for defect in case["defects"]:
                self.assertTrue(all(defect.get(key) for key in ("id", "category", "expected", "observed", "location")))


if __name__ == "__main__":
    unittest.main()
