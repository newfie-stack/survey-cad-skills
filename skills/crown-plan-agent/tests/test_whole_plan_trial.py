"""Regenerate the preserved whole-plan packets, without repeating model review."""
import hashlib
import importlib.util
import platform
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime

pdf = load_pdf_runtime()
RECORDED_RUNTIME = (platform.system() == "Linux" and platform.machine() == "x86_64"
                    and sys.version_info[:2] == (3, 12)
                    and pdf.VersionBind == "2.1" and pdf.VersionFitz == "1.28.6")


class WholePlanTrialFixtureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("whole_plan_trial"),
                             "Preserved whole-plan fixture generator is not published")
        import whole_plan_trial
        self.factory = whole_plan_trial
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def packet(self, case_id, suffix=""):
        folder = self.root / (case_id + suffix)
        self.factory.write_case(folder, case_id)
        return folder

    def pages(self, case_id):
        with pdf.open(self.packet(case_id) / "plan.pdf") as document:
            return [" ".join(page.get_text().split()) for page in document]

    def test_all_twelve_packets_are_deterministic_renderable_and_answer_free(self):
        expected = {"K27", "M84", "Q19", "S63", "V42", "X95",
                    "B76", "D31", "F58", "H90", "N24", "T67"}
        self.assertEqual(set(self.factory.CASE_IDS), expected)
        dimensions = set()
        for case_id in self.factory.CASE_IDS:
            with self.subTest(case=case_id):
                hashes = []
                for repeat in ("-first", "-second"):
                    folder = self.root / (case_id + repeat)
                    meta = self.factory.write_case(folder, case_id)
                    self.assertEqual(set(p.name for p in folder.iterdir()),
                                     {"plan.pdf", "job-brief.md"})
                    actual = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                              for name in ("plan.pdf", "job-brief.md")}
                    self.assertEqual(meta, {"case_id": case_id,
                                           "inputs": ["plan.pdf", "job-brief.md"],
                                           "sha256": actual})
                    hashes.append(actual)
                    brief = (folder / "job-brief.md").read_text()
                    for field in ("known_defects", "defect_ids", "expected_verdict", "is_clean",
                                  "frozen-truth", "source_sha256"):
                        self.assertNotIn(field, brief)
                self.assertEqual(hashes[0], hashes[1])
                with pdf.open(folder / "plan.pdf") as document:
                    self.assertIn(len(document), (1, 2))
                    for page in document:
                        self.assertIn("SYNTHETIC", page.get_text())
                        dimensions.add((page.rect.width, page.rect.height))
                        pixels = page.get_pixmap(matrix=pdf.Matrix(0.35, 0.35), alpha=False)
                        self.assertGreater(pixels.width * pixels.height, 0)
        self.assertEqual(dimensions, {(1190.0, 842.0), (842.0, 1190.0),
                                      (595.0, 842.0), (842.0, 595.0), (1100.0, 520.0)})

    def test_access_package_current_identity_preserves_historical_and_neighbour_controls(self):
        for case_id, drawing, location in (("M84", "HV-5882", "NE 14-58-8 W5M"),
                                           ("Q19", "HV-6027", "NE 14-56-8 W5M")):
            with self.subTest(case=case_id):
                overview, details = self.pages(case_id)
                self.assertIn("Archived drawing HV-5882", overview)
                self.assertIn("Adjoining: NW 14-56-8 W5M", overview)
                self.assertIn("Adjacent parcel: SE 15-56-8 W5M", overview)
                self.assertIn("Drawing: HV-6027 Revision: C", overview)
                self.assertIn(f"Drawing: {drawing} Revision: C", details)
                self.assertIn(f"LOCATION {location} Alberta", details)
                for scale in ("1:2,500", "1:10,000"):
                    self.assertIn(scale, overview)
                for scale in ("1:500", "1:1,000"):
                    self.assertIn(scale, details)

    def test_cabin_raster_notes_remain_image_only_and_north_is_scoped_to_each_view(self):
        image_hashes = {}
        for case_id, main_north in (("K27", True), ("X95", False)):
            with self.subTest(case=case_id):
                with pdf.open(self.packet(case_id) / "plan.pdf") as document:
                    page = document[0]
                    images = page.get_images(full=True)
                    self.assertEqual(len(images), 1)
                    self.assertEqual(images[0][2:4], (2205, 534))
                    self.assertEqual(page.get_text(clip=pdf.Rect(30, 684, 812, 874)), "")
                    self.assertNotIn("Coordinate reference", page.get_text())
                    image_hashes[case_id] = hashlib.sha256(pdf.Pixmap(document, images[0][0]).samples).hexdigest()
                    for clip, present in (((460, 130, 535, 230), main_north),
                                          ((750, 120, 810, 220), True)):
                        region = pdf.Rect(clip)
                        self.assertEqual("GRID N" in page.get_text(clip=region), present)
                        drawings = [drawing for drawing in page.get_drawings()
                                    if region.contains(drawing["rect"])]
                        self.assertEqual(bool(drawings), present)
                        if RECORDED_RUNTIME:
                            rendered = page.get_pixmap(matrix=pdf.Matrix(1, 1), clip=region,
                                                       alpha=False)
                            key = "main" if clip[0] == 460 else "locator"
                            self.assertEqual(hashlib.sha256(rendered.samples).hexdigest(),
                                             NORTH_RENDER_HASHES[case_id][key])
                    native = " ".join(page.get_text().split())
                    self.assertIn("NE 14-62-11 W5M (adjoining)", native)
                    self.assertIn("History: Rev 1 / 2026-09-24 / preliminary", native)
        self.assertNotEqual(image_hashes["K27"], image_hashes["X95"])
        if RECORDED_RUNTIME:
            self.assertEqual(image_hashes, RASTER_NOTE_HASHES)

    def test_area_categories_and_exclusion_scope_do_not_collapse_into_the_total(self):
        for case_id, access, borrow, exclusion in (("S63", "0.480", "0.160", "0.100"),
                                                  ("V42", "0.420", "0.220", "0.080")):
            with self.subTest(case=case_id):
                sheet, = self.pages(case_id)
                self.assertIn("NEW ACCESS 0.420 ha", sheet)
                self.assertIn("BORROW 0.220 ha", sheet)
                self.assertIn(f"Staging pad 0.620 New access {access} Borrow {borrow} "
                              "ACTIVITY SUBTOTAL 1.260", sheet)
                self.assertIn("Road allowance / excluded 0.080 GROSS ENVELOPE 1.480 "
                              "NET CROWN REQUEST 1.260", sheet)
                self.assertIn("Road allowance overlap 0.080 ha - excluded", sheet)
                self.assertIn(f"0.140 ha of existing shared track and {exclusion} ha "
                              "of road allowance overlap", sheet)

    def test_portrait_plan_total_and_current_work_instruction_retain_history(self):
        for case_id, total, instruction in (("N24", "210.75", "WI-326"),
                                            ("T67", "211.75", "WI-263")):
            with self.subTest(case=case_id):
                sheet, = self.pages(case_id)
                self.assertIn("A 124.50 m + B 86.25 m", sheet)
                self.assertIn(f"TOTAL ACCESS LENGTH = {total} m", sheet)
                self.assertIn(f"Stockpile operating limits follow work instruction {instruction}.", sheet)
                self.assertIn("Rev 1, 2026-09-18: WI-281 retained in archive", sheet)
                self.assertIn("EXTRACTION BLOCK Q-2", sheet)
                self.assertIn("STOCKPILE S-1", sheet)

    def test_route_sheet_identity_retain_match_lines_separate_crossings_and_quarters(self):
        for case_id, east_job, east_number in (("D31", "BTP-26-597", "1"),
                                              ("F58", "BTP-26-579", "2")):
            with self.subTest(case=case_id):
                west, east = self.pages(case_id)
                self.assertIn("Job BTP-26-579", west)
                self.assertIn(f"Job {east_job}", east)
                self.assertIn("Sheet 1 of 2", west)
                self.assertIn(f"Sheet {east_number} of 2", east)
                self.assertIn("SE 24-064-09 W5M", west)
                self.assertIn("NE 24-064-09 W5M", east)
                self.assertIn("Crossing C-04", west)
                self.assertIn("Crossing C-05", east)
                for sheet in (west, east):
                    self.assertIn("MATCH A at 0+150", sheet)
                    self.assertIn("alignment CF-A superseded", sheet)
                    self.assertIn("alignment CF-B, route total 300.00 m", sheet)

    def test_oblique_native_width_and_edge_note_zone_retain_distinct_view_controls(self):
        for case_id, width, zone in (("B76", "18.00 m", "12N"),
                                    ("H90", "1.80 m", "11N")):
            with self.subTest(case=case_id):
                with pdf.open(self.packet(case_id) / "plan.pdf") as document:
                    page = document[0]
                    self.assertIn(width, page.get_text(clip=pdf.Rect(648, 198, 729, 240)))
                    note = " ".join(page.get_text(clip=pdf.Rect(42, 403, 391, 477)).split())
                    self.assertIn(f"Basis of bearings: NAD83(CSRS), UTM Zone {zone}.", note)
                    sheet = " ".join(page.get_text().split())
                    self.assertIn("Standard corridor: 18.00 m Basis: NAD83(CSRS), UTM Zone 12N", sheet)
                    for control in ("PARCEL P-6 / NW 08", "PARCEL P-7 / NE 08", "DETAIL B / 1:300",
                                    "Nominal view scale 1:1500", "Rev 2, 2026-09-29"):
                        self.assertIn(control, sheet)

    @unittest.skipUnless(RECORDED_RUNTIME, "Original byte identity recorded on Linux x86_64, "
                         "Python 3.12, PyMuPDF 2.1 / MuPDF 1.28.6")
    def test_packets_preserve_original_frozen_source_and_brief_hashes(self):
        for case_id, expected in ORIGINAL_HASHES.items():
            with self.subTest(case=case_id):
                folder = self.packet(case_id)
                actual = tuple(hashlib.sha256((folder / name).read_bytes()).hexdigest()
                               for name in ("plan.pdf", "job-brief.md"))
                self.assertEqual(actual, expected)

    def test_brief_bytes_match_frozen_inputs_on_every_supported_runtime(self):
        for case_id, (_, expected) in ORIGINAL_HASHES.items():
            with self.subTest(case=case_id):
                folder = self.packet(case_id)
                self.assertEqual(hashlib.sha256((folder / "job-brief.md").read_bytes()).hexdigest(),
                                 expected)

    def test_unknown_case_is_rejected_without_creating_destination(self):
        for case_id in ("unknown", "../K27", "", None):
            destination = self.root / "invalid"
            with self.subTest(case=case_id), self.assertRaises(ValueError):
                self.factory.write_case(destination, case_id)
            self.assertFalse(destination.exists())

    def test_existing_directory_and_file_are_preserved(self):
        folder = self.packet("K27")
        before = {path.name: path.read_bytes() for path in folder.iterdir()}
        with self.assertRaises(FileExistsError):
            self.factory.write_case(folder, "X95")
        self.assertEqual({path.name: path.read_bytes() for path in folder.iterdir()}, before)
        file = self.root / "existing-file"
        file.write_bytes(b"preserve this file")
        with self.assertRaises(FileExistsError):
            self.factory.write_case(file, "K27")
        self.assertEqual(file.read_bytes(), b"preserve this file")


# Values independently recorded from the immutable pre-review synthetic inputs.
ORIGINAL_HASHES = {
    "B76": (
        "d060bec75a9c2567672b4ac15321eb87b6d26bb465a953767cccc398242c7d67",
        "0834ee7016bdf9d9b1fb97595efb17049b9d55623fce3f5026aeadec708106f0",
    ),
    "D31": (
        "eaaa7dcea44c50f28dd1531edf8318f5261a2c734f401b42a80a3190b1dd761f",
        "6b196851ec5dd78374d2fad802b8ac84a63a8222fd3dad859ac73882c620544a",
    ),
    "F58": (
        "97cbfcae4376cb9976f1836dd0c1e50b0b2e5b0889439a8543339fefb376f113",
        "6b196851ec5dd78374d2fad802b8ac84a63a8222fd3dad859ac73882c620544a",
    ),
    "H90": (
        "84ad402792b9c43ae8c3b64ac422346f6c3ea66671f41e324a3b52322fd34c0b",
        "0834ee7016bdf9d9b1fb97595efb17049b9d55623fce3f5026aeadec708106f0",
    ),
    "K27": (
        "5e188db555c8b61d805cbf9bf8f929512f2b462e21ad4439e8d45a1090d60e89",
        "7a20adddfe93e6fbd7da98f348a1e334ec95ffd9e0c9f9d10c365c8c563dd3c5",
    ),
    "M84": (
        "01f066aa72ee3e1adb85dea630e6966d90689bb943fe9de5bdaf9764b1502761",
        "4df09cb6c57b44507278022ad1ef21266cfebe4d8c46f1e886566fba4d69ff6b",
    ),
    "N24": (
        "c05daefa0e48ae05cedb8e6e4853f47738efb226a515a39acc406cab6b836ef0",
        "c1edacd0f5227bd247169bd8ee5634297a955df1cf9c9f6d75c8bc205ece1890",
    ),
    "Q19": (
        "b409e8b316d7ae7c6918b508bd1f95c23030500de0b8d9414c5b13648645e63c",
        "d4b08c635e5f5761c702b9dc996acdf4095d1b2534b82597fc00b0d176928a35",
    ),
    "S63": (
        "9aac4c37ab909410d374fa1ecd9d709d95dcd64b6668e1de276fb7ecc862bbfc",
        "360d70a62fc859796e8286347f2b9bedbfd2970f10b650b014b41f6b0cb8999e",
    ),
    "T67": (
        "d740f2556f00aaf7b5dbafe30502dfed9ddfaacf900067e07b8f3ccb256e2ee2",
        "c1edacd0f5227bd247169bd8ee5634297a955df1cf9c9f6d75c8bc205ece1890",
    ),
    "V42": (
        "57a120fc32f7b32862d3034b6100ad7c34bd2c79c7858a7141bc3eca35e7575c",
        "ac3cdbcf7c13f0be6971f2589a9125afa4796d0f6265a524c57bd4183c8a8d24",
    ),
    "X95": (
        "3c66ccd302cf5053d838be05e52010aeacd50bf55bfc2c426e3051352fa68d7c",
        "666db60ec54eff815e56d4c480572064affd2c090e388eb86a088c9434d186b8",
    ),
}
RASTER_NOTE_HASHES = {
    "K27": "bbcaa1e31b025e2f5a7ef0d9eb0df350adf6c93ef6bd07d99a19193e69010e4b",
    "X95": "dc31816ffb0e78f8a6e0a10b14ef19098b9ee6b71a7f5e62fcd5266f356ea256",
}
NORTH_RENDER_HASHES = {
    "K27": {
        "main": "ac75372f720c05fb7f01b8313f7af8824b9778bfd36b5a06fce34f22503bfa79",
        "locator": "9fae75b44944d54cf34229400ae897e8c8defc9c9d11abd9214698b99406fd7a",
    },
    "X95": {
        "main": "d344ba69e1dda110c277e8e148b3845ea5eaaa2a58fce821984589e06c2206d8",
        "locator": "9fae75b44944d54cf34229400ae897e8c8defc9c9d11abd9214698b99406fd7a",
    },
}


if __name__ == "__main__":
    unittest.main()
