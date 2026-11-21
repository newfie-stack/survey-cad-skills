"""Regenerate four published synthetic inputs, without repeating model review.

The differing near-north label directions are constructed test data. They do
not establish an angular drafting rule; an exact 350-degree cutoff remains
unconfirmed and is not tested here.
"""
import hashlib
import importlib.util
import json
import math
import platform
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime

pdf = load_pdf_runtime()
TRUTH_PATH = Path(__file__).parent / "fixtures" / "intake_forward_truth.json"
FONTS = {
    "DejaVuSans.ttf": "57f73e11f51999432bf7ab22ce55b6f945d5eca1bf824404cfa9ec2e3718c84e",
    "DejaVuSans-Bold.ttf": "a4c5bc453ca281d90ea079e596da7ae0dfeb5777497c29ec254e76d97ff6f890",
}
RECORDED_RUNTIME = (
    platform.system() == "Linux" and platform.machine() == "x86_64"
    and sys.version_info[:3] == (3, 12, 16)
    and pdf.VersionBind == "2.1" and pdf.VersionFitz == "1.28.6"
    and all((Path("/usr/share/fonts/truetype/dejavu") / name).is_file()
            and hashlib.sha256((Path("/usr/share/fonts/truetype/dejavu") / name).read_bytes()).hexdigest() == digest
            for name, digest in FONTS.items())
)


class IntakeForwardLayoutFixtureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("intake_forward_layouts"),
                             "Preserved intake forward-layout generator is not published")
        import intake_forward_layouts
        self.factory = intake_forward_layouts
        self.truth = json.loads(TRUTH_PATH.read_text())
        self.cases = {case["case_id"]: case
                      for case in self.truth["original_oracle"]["content"]["cases"]}
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def packet(self, case_id, suffix=""):
        destination = self.root / (case_id + suffix)
        self.factory.write_case(destination, case_id)
        return destination

    def test_all_four_packets_are_deterministic_renderable_and_answer_free(self):
        self.assertEqual(self.factory.CASE_IDS, ("L38", "P72", "R46", "U91"))
        for case_id in self.factory.CASE_IDS:
            with self.subTest(case=case_id):
                hashes = []
                for suffix in ("-first", "-second"):
                    folder = self.root / (case_id + suffix)
                    result = self.factory.write_case(folder, case_id)
                    self.assertEqual({path.name for path in folder.iterdir()},
                                     {"plan.pdf", "job-brief.md"})
                    actual = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                              for name in ("plan.pdf", "job-brief.md")}
                    self.assertEqual(result, {"case_id": case_id,
                                              "inputs": ["plan.pdf", "job-brief.md"],
                                              "sha256": actual})
                    hashes.append(actual)
                    brief = (folder / "job-brief.md").read_text()
                    for answer in ("known_defects", "defect_ids", "expected_verdict",
                                   "is_clean", "source_sha256", "MR-IDENTITY", "WB-MAIN-SCALE"):
                        self.assertNotIn(answer, brief)
                self.assertEqual(hashes[0], hashes[1])
                with pdf.open(folder / "plan.pdf") as document:
                    portrait = case_id in ("L38", "R46")
                    self.assertEqual(len(document), 2 if portrait else 1)
                    for page in document:
                        self.assertEqual((page.rect.width, page.rect.height),
                                         (842.0, 1191.0) if portrait else (1191.0, 842.0))
                        self.assertIn("SYNTHETIC REVIEW", page.get_text())
                        pixels = page.get_pixmap(matrix=pdf.Matrix(.25, .25), alpha=False)
                        self.assertGreater(pixels.width * pixels.height, 0)

    def test_mica_identity_and_sum_mutations_retain_schedule_and_context_controls(self):
        for case_id, subject, total in (("L38", "SYN-MR-831", "3,150.30"),
                                        ("R46", "SYN-MR-813", "3,250.30")):
            with self.subTest(case=case_id), pdf.open(self.packet(case_id) / "plan.pdf") as document:
                title, view = [" ".join(page.get_text().split()) for page in document]
                self.assertIn(f"SUBJECT FILE {subject}", title)
                self.assertIn(f"1,250.10 m. + 2,000.20 m. = {total} m.", title)
                self.assertIn("A–B 345°00′00″ 1,250.10 m. 0+000.00 1+250.10", title)
                self.assertIn("B–C 355°00′00″ 2,000.20 m. 1+250.10 3+250.30", title)
                self.assertIn("CURRENT SUBJECT SYN-MR-813 Job MR-813", view)
                for control in ("Total 3,250.30 m.", "HT-4 — historical trail",
                                "Historical trail HT-4", "30.00 m.", "MAIN VIEW 1:12,500"):
                    self.assertIn(control, view)

    def test_near_north_native_labels_retain_differing_constructed_directions(self):
        expected = {"345°00′00″   1,250.10 m.": 285,
                    "355°00′00″   2,000.20 m.": 95}
        for case_id in ("L38", "R46"):
            folder = self.packet(case_id)
            self.assertIn("There is no job-specified angular cutoff for a label-direction change.",
                          (folder / "job-brief.md").read_text())
            with self.subTest(case=case_id), pdf.open(folder / "plan.pdf") as document:
                found = {}
                for block in document[1].get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        value = "".join(span["text"] for span in line["spans"])
                        if value in expected:
                            found[value] = line["dir"]
                self.assertEqual(set(found), set(expected))
                for value, degrees in expected.items():
                    radians = math.radians(degrees)
                    self.assertAlmostEqual(found[value][0], math.cos(radians), places=4)
                    self.assertAlmostEqual(found[value][1], -math.sin(radians), places=4)

    def test_bench_scale_mutation_retain_inset_historical_and_title_controls(self):
        for case_id, scale in (("P72", "Scale 1:2500"), ("U91", "Scale 1:2,50")):
            with self.subTest(case=case_id), pdf.open(self.packet(case_id) / "plan.pdf") as document:
                sheet = " ".join(document[0].get_text().split())
                self.assertIn(scale, sheet)
                self.assertIn("Scale 1:500", sheet)
                for control in ("H-17 — historical sketch alignment (context only)",
                                "Historical sketch Simulated Zone 11N; context",
                                "Sta. 0+145.00", "SYN-WB-624 / 1", "2026-09-18 / AS SHOWN",
                                "18.00 m width", "230.00 m centreline"):
                    self.assertIn(control, sheet)
                self.assertNotIn("NAD83", sheet)
                if case_id == "U91":
                    self.assertNotIn("Scale 1:2500", sheet)

    def test_bench_note_panel_remains_image_only_beside_dense_native_field_notes(self):
        hashes = {}
        for case_id in ("P72", "U91"):
            with self.subTest(case=case_id), pdf.open(self.packet(case_id) / "plan.pdf") as document:
                page = document[0]
                panel = pdf.Rect(645, 500, 1151, 735)
                self.assertEqual(page.get_text(clip=panel), "")
                self.assertEqual(page.get_text("words", clip=panel), [])
                self.assertGreater(len(page.get_text("words", clip=pdf.Rect(40, 500, 626, 735))), 60)
                images = page.get_images(full=True)
                self.assertEqual(len(images), 1)
                self.assertEqual(images[0][2:4], (1518, 705))
                rectangles = page.get_image_rects(images[0][0])
                self.assertEqual(len(rectangles), 1)
                # The original aspect-preserving insertion rounds by < .01 pt.
                for actual, expected in zip(rectangles[0], panel):
                    self.assertAlmostEqual(actual, expected, delta=.01)
                hashes[case_id] = hashlib.sha256(pdf.Pixmap(document, images[0][0]).samples).hexdigest()
        self.assertNotEqual(hashes["P72"], hashes["U91"])
        if RECORDED_RUNTIME:
            self.assertEqual(hashes, {case_id: asset["pixels_sha256"]
                                     for case_id, asset in self.truth["original_note_assets"].items()})

    @unittest.skipUnless(RECORDED_RUNTIME, "Byte identity recorded on Linux x86_64, Python 3.12.16, "
                         "PyMuPDF 2.1 / MuPDF 1.28.6 and the recorded DejaVu font files")
    def test_pdf_bytes_match_all_four_frozen_original_sources(self):
        for case_id, truth in self.cases.items():
            with self.subTest(case=case_id):
                folder = self.packet(case_id)
                self.assertEqual(hashlib.sha256((folder / "plan.pdf").read_bytes()).hexdigest(),
                                 truth["source_sha256"])

    @unittest.skipUnless(RECORDED_RUNTIME, "Original synthetic raster bytes depend on the recorded runtime and fonts")
    def test_regenerated_note_png_bytes_match_original_synthetic_assets(self):
        for case_id, asset in self.truth["original_note_assets"].items():
            with self.subTest(case=case_id):
                image = self.factory.raster_notes(case_id == "U91")
                self.assertEqual(len(image), asset["original_bytes"])
                self.assertEqual(hashlib.sha256(image).hexdigest(), asset["original_sha256"])

    def test_brief_bytes_match_frozen_inputs_on_every_supported_runtime(self):
        for case_id, truth in self.cases.items():
            with self.subTest(case=case_id):
                folder = self.packet(case_id)
                self.assertEqual(hashlib.sha256((folder / "job-brief.md").read_bytes()).hexdigest(),
                                 truth["brief_sha256"])

    def test_native_metadata_and_absent_original_trailer_id_are_preserved(self):
        for case_id in self.factory.CASE_IDS:
            with self.subTest(case=case_id), pdf.open(self.packet(case_id) / "plan.pdf") as document:
                self.assertEqual(document.xref_get_key(-1, "ID"), ("null", "null"))
                self.assertEqual({key: document.metadata[key] for key in self.truth["original_pdf_metadata"]},
                                 self.truth["original_pdf_metadata"])

    def test_frozen_oracle_retains_four_cases_and_portable_original_provenance(self):
        artifact = self.truth["original_oracle"]
        canonical = json.dumps(artifact["content"], ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), artifact["canonical_content_sha256"])
        original = (json.dumps(artifact["content"], ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(len(original), artifact["original_bytes"])
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "2c5b46875f46f484076a06b33c1bbc6d91abf121abc377bddca1b49e3fc1f80c")
        self.assertEqual(artifact["original_sha256"],
                         "2c5b46875f46f484076a06b33c1bbc6d91abf121abc377bddca1b49e3fc1f80c")
        self.assertEqual(self.truth["source_commit"], "3a3e5697ccf4e48f75032054131131ed3a7f3ea9")
        self.assertEqual(set(self.cases), {"L38", "P72", "R46", "U91"})
        self.assertEqual({case: value["is_clean"] for case, value in self.cases.items()},
                         {"L38": False, "P72": True, "R46": True, "U91": False})
        self.assertEqual({case: [defect["id"] for defect in value["defects"]]
                          for case, value in self.cases.items()},
                         {"L38": ["MR-IDENTITY", "MR-LENGTH-SUM"], "P72": [], "R46": [],
                          "U91": ["WB-SUBJECT-ZONE", "WB-MAIN-SCALE"]})
        self.assertTrue(all(len(value["clean_controls"]) == 4 for value in self.cases.values()))
        for host_path in ("/workspace/", "/tmp/", "C:\\\\", "review-freeze", "grading/"):
            self.assertNotIn(host_path, TRUTH_PATH.read_text())

    def test_unknown_case_is_rejected_without_creating_destination(self):
        for case_id in ("unknown", "../L38", "", None, [], {}):
            destination = self.root / "unknown"
            with self.subTest(case=case_id), self.assertRaises(ValueError):
                self.factory.write_case(destination, case_id)
            self.assertFalse(destination.exists())

    def test_existing_directory_and_file_are_preserved(self):
        folder = self.packet("L38")
        before = {path.name: path.read_bytes() for path in folder.iterdir()}
        with self.assertRaises(FileExistsError):
            self.factory.write_case(folder, "U91")
        self.assertEqual({path.name: path.read_bytes() for path in folder.iterdir()}, before)
        existing = self.root / "existing-file"
        existing.write_bytes(b"retain caller data")
        with self.assertRaises(FileExistsError):
            self.factory.write_case(existing, "P72")
        self.assertEqual(existing.read_bytes(), b"retain caller data")


if __name__ == "__main__":
    unittest.main()
