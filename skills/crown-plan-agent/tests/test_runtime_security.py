"""Security floor and provider-isolation tests; PDF fixtures are invented."""
import sys
from contextlib import contextmanager
from importlib import metadata
import hashlib
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))


class RuntimeSecurityTests(unittest.TestCase):
    @contextmanager
    def supported_runtime(self, *, providers=None, python=(3, 12, 16),
                          binding="2.1", native="1.28.6"):
        import runtime_security
        versions = {"pymupdf-lite": "2.1"} if providers is None else providers

        def installed(name):
            if name not in versions:
                raise metadata.PackageNotFoundError(name)
            return versions[name]

        module = SimpleNamespace(VersionBind=binding, VersionFitz=native)
        with patch.object(sys, "version_info", python), \
                patch.object(runtime_security.metadata, "version", side_effect=installed), \
                patch.object(runtime_security.importlib, "import_module", return_value=module) as imported:
            yield runtime_security, module, imported

    def test_old_python_cannot_open_an_invented_pdf(self):
        import pymupdf
        from pdf_inspector import extract_pdf
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invented.pdf"
            with pymupdf.open() as document:
                document.new_page().insert_text((40, 40), "INVENTED NOTE")
                document.save(path)
            with patch.object(sys, "version_info", (3, 12, 14)):
                with self.assertRaisesRegex(RuntimeError, "Python"):
                    extract_pdf(path, include_vectors=False)

    def test_all_supported_python_branches_enforce_their_own_patch_floor(self):
        for branch, floor in (((3, 11), 18), ((3, 12), 16), ((3, 13), 18),
                              ((3, 14), 10), ((3, 15), 2)):
            with self.subTest(branch=branch):
                with self.supported_runtime(python=(*branch, floor)) as (guard, module, imported):
                    self.assertIs(guard.load_pdf_runtime(), module)
                    imported.assert_called_once_with("pymupdf")
                with self.supported_runtime(python=(*branch, floor - 1)) as (guard, _, imported):
                    with self.assertRaisesRegex(RuntimeError, "Python security update"):
                        guard.load_pdf_runtime()
                    imported.assert_not_called()

    def test_old_or_unknown_python_branch_is_not_a_numerical_shortcut(self):
        for version in ((3, 10, 99), (3, 13, 0), (3, 16, 0), (4, 0, 0),
                        (3, 12, 16, "candidate", 1)):
            with self.subTest(version=version), self.supported_runtime(python=version) as (guard, _, imported):
                with self.assertRaisesRegex(RuntimeError, "Python"):
                    guard.load_pdf_runtime()
                imported.assert_not_called()

    def test_newer_security_patch_on_supported_branch_remains_usable(self):
        with self.supported_runtime(python=(3, 12, 17)) as (guard, module, _):
            self.assertIs(guard.load_pdf_runtime(), module)

    def test_old_or_prerelease_provider_is_rejected_before_native_import(self):
        for version in ("1.26.6", "1.28.2", "2.0", "2.1rc1", "2.1.dev1",
                        "3.0", "unknown", "2.1+unreviewed"):
            with self.subTest(version=version), \
                    self.supported_runtime(providers={"pymupdf-lite": version}) as (guard, _, imported):
                with self.assertRaisesRegex(RuntimeError, "PyMuPDF"):
                    guard.load_pdf_runtime()
                imported.assert_not_called()

    def test_each_official_provider_is_supported_when_installed_alone(self):
        for provider in ("pymupdf-lite", "PyMuPDF"):
            with self.subTest(provider=provider), \
                    self.supported_runtime(providers={provider: "2.1"}) as (guard, module, _):
                self.assertIs(guard.load_pdf_runtime(), module)
                self.assertEqual(guard.runtime_status()["provider"], provider)

    def test_missing_and_overlapping_providers_fail_before_import(self):
        for providers in ({}, {"pymupdf-lite": "2.1", "PyMuPDF": "2.1"},
                          {"pymupdf-lite": "2.1", "PyMuPDF": "1.26.6"}):
            with self.subTest(providers=providers), self.supported_runtime(providers=providers) as (guard, _, imported):
                with self.assertRaisesRegex(RuntimeError, "missing|Conflicting"):
                    guard.load_pdf_runtime()
                imported.assert_not_called()

    def test_loaded_binding_must_match_provider_metadata(self):
        with self.supported_runtime(binding="2.0") as (guard, _, _):
            with self.assertRaisesRegex(RuntimeError, "metadata and loaded binding"):
                guard.load_pdf_runtime()

    def test_native_mupdf_has_its_own_floor(self):
        for native in ("1.26.11", "1.28.5", "1.28.6rc1", None):
            with self.subTest(native=native), self.supported_runtime(native=native) as (guard, _, _):
                with self.assertRaisesRegex(RuntimeError, "MuPDF"):
                    guard.load_pdf_runtime()

    def test_runtime_report_keeps_advisory_review_separate(self):
        with self.supported_runtime(binding="2.1.0") as (guard, _, _):
            status = guard.runtime_status()
        self.assertEqual(status["minimum_runtime_policy"], "SATISFIED")
        self.assertEqual(status["python"], "3.12.16")
        self.assertEqual(status["provider_version"], "2.1")
        self.assertEqual(status["mupdf_version"], "1.28.6")
        self.assertEqual(status["assessment_scope"], "MINIMUM_RUNTIME_VERSIONS_ONLY")
        self.assertTrue(status["advisory_review_required"])

    def test_every_pdf_entrypoint_rejects_unsupported_runtime(self):
        import pymupdf
        from pdf_inspector import extract_pdf
        from table_a2_rows import extract_a2_rows
        from revision_sources import inspect_original_pdf
        from finished_plan_review import review_finished_plan
        from pdf_markup import build_annotated_pdf
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invented.pdf"
            with pymupdf.open() as document:
                document.new_page().insert_text((40, 40), "INVENTED NOTE")
                document.save(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            spec = {"schema_version": 1, "source_sha256": digest, "prepared_by": "invented fixture",
                    "checks": [{"id": "visual", "kind": "visual", "description": "Invented region",
                                "basis": "Invented regression", "regions": [
                                    {"page": 1, "bbox_points": [0, 0, 100, 100], "role": "invented"}]}]}
            calls = [lambda: extract_pdf(path, include_vectors=False),
                     lambda: extract_a2_rows(path.read_bytes()),
                     lambda: inspect_original_pdf(path),
                     lambda: review_finished_plan(path, spec),
                     lambda: build_annotated_pdf(path, {}, {})]
            for index, call in enumerate(calls):
                with self.subTest(entrypoint=index), patch.object(sys, "version_info", (3, 12, 14)):
                    with self.assertRaisesRegex(RuntimeError, "Python security update"):
                        call()


if __name__ == "__main__":
    unittest.main()
