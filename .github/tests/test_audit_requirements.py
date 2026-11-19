"""Audit coverage contract; no network calls or Crown runtime dependencies."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_requirements.py"
audit = None
if SCRIPT.is_file():
    spec = importlib.util.spec_from_file_location("audit_requirements", SCRIPT)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


class AuditRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(audit, "Independent requirement-to-audit coverage checking is missing")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / "requirements.txt"
        self.output = self.directory / "audit.json"

    def write(self, text, name="requirements.txt"):
        path = self.directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def pin(self, name, version, marker=""):
        return f"{name}=={version}{marker} --hash=sha256:{'a' * 64}\n"

    def report(self, rows):
        return {"dependencies": [{"name": name, "version": version, "vulns": []}
                                 for name, version in rows], "fixes": []}

    def test_complete_hash_inputs_include_bootstrap_packages_and_canonical_names(self):
        first = self.write("--only-binary=:all:\n" + self.pin("pip", "26.3")
                           + self.pin("Packaging", "26.0"))
        second = self.write(self.pin("pip_audit", "2.10.1")
                            + self.pin("PIP", "26.3.0"), "tools.txt")
        self.assertEqual(audit.expected_dependencies([first, second]),
                         {"pip": "26.3", "packaging": "26", "pip-audit": "2.10.1"})

    def test_marker_and_continuation_hash_parsing_keeps_exact_active_graph(self):
        text = ("# generated lock\n--only-binary :all:\n--require-hashes\n"
                "Demo_Pkg[extra]==1.0 ; python_version >= \"3\" \\\n"
                f"    --hash=sha256:{'a' * 64} \\\n"
                f"    --hash sha256:{'b' * 64}\n    # via declared extra\n"
                + self.pin("not-current", "2.0", '; python_version < "0"'))
        self.assertEqual(audit.expected_dependencies([self.write(text)]), {"demo-pkg": "1"})

    def test_complete_audit_compares_normalized_versions(self):
        expected = {"pip": "26.3", "packaging": "26", "pip-audit": "2.10.1"}
        report = self.report([("PIP", "26.3.0"), ("packaging", "26.0"), ("pip_audit", "2.10.1")])
        self.assertEqual(audit.verify_coverage(expected, report), 3)

    def test_missing_pip_or_packaging_cannot_be_a_successful_audit(self):
        expected = {"pip": "26.3", "packaging": "26", "pip-audit": "2.10.1"}
        for missing in ("pip", "packaging", "both"):
            with self.subTest(missing=missing):
                rows = [(name, version) for name, version in expected.items()
                        if name != missing and not (missing == "both" and name in {"pip", "packaging"})]
                with self.assertRaises(ValueError):
                    audit.verify_coverage(expected, self.report(rows))

    def test_wrong_versions_skips_extras_duplicates_and_vulnerabilities_fail(self):
        mutations = [
            self.report([("pip", "26.2")]),
            {"dependencies": [{"name": "pip", "version": "26.3", "vulns": [],
                               "skip_reason": "unsupported package"}]},
            self.report([("pip", "26.3"), ("unexpected", "1")]),
            self.report([("pip", "26.3"), ("PIP", "26.3")]),
            {"dependencies": [{"name": "pip", "version": "26.3", "vulns": [{"id": "invented"}]}]},
            {"dependencies": "not a dependency list"},
            {"dependencies": [{"name": "pip", "version": 26.3, "vulns": []}]},
        ]
        for report in mutations:
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    audit.verify_coverage({"pip": "26.3"}, report)

    def test_unpinned_urls_includes_and_other_options_are_rejected(self):
        for line in ("demo>=1", "demo==1.*", "demo===arbitrary", "demo @ https://example.invalid/demo.whl",
                     "-r other.txt", "--requirement other.txt", "-c constraints.txt",
                     "--index-url https://example.invalid/simple", "--trusted-host example.invalid",
                     "--only-binary=:none:", "demo==1 --global-option=unsafe"):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):
                    audit.expected_dependencies([self.write(line + f" --hash=sha256:{'a' * 64}\n")])

    def test_missing_or_malformed_hashes_are_rejected_even_for_inactive_markers(self):
        for line in ("demo==1", "demo==1 --hash=sha256:short", "demo==1 --hash=md5:" + "a" * 32,
                     "demo==1 --hash=sha256:" + "z" * 64,
                     'demo==1 ; python_version < "0"'):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):
                    audit.expected_dependencies([self.write(line + "\n")])

    def test_conflicting_duplicate_pins_are_rejected(self):
        first = self.write(self.pin("demo_pkg", "1.0"))
        second = self.write(self.pin("demo-pkg", "2.0"), "second.txt")
        with self.assertRaises(ValueError):
            audit.expected_dependencies([first, second])

    def test_cli_disables_resolver_and_verifies_a_complete_report(self):
        self.write(self.pin("pip", "26.3") + self.pin("packaging", "26.0"))
        def run(command, **kwargs):
            self.assertEqual(command[:3], [sys.executable, "-m", "pip_audit"])
            for flag in ("--disable-pip", "--strict", "--require-hashes"):
                self.assertIn(flag, command)
            self.assertIn("--cache-dir", command)
            cache = Path(command[command.index("--cache-dir") + 1])
            scratch = Path(command[command.index("--output") + 1])
            self.assertEqual(cache.parent, scratch.parent)
            self.assertNotEqual(cache, scratch)
            self.assertEqual(command[command.index("--vulnerability-service") + 1], "pypi")
            self.assertEqual(command[command.index("--progress-spinner") + 1], "off")
            self.assertEqual(command[command.index("--format") + 1], "json")
            self.assertEqual(command[command.index("-r") + 1], str(self.path))
            Path(command[command.index("--output") + 1]).write_text(
                json.dumps(self.report([("pip", "26.3"), ("packaging", "26.0")])))
            return subprocess.CompletedProcess(command, 0)
        with patch.object(audit.subprocess, "run", side_effect=run):
            result = audit.main(["--output", str(self.output), "-r", str(self.path)])
        self.assertEqual(result, 0)
        self.assertEqual(len(json.loads(self.output.read_text())["dependencies"]), 2)

    def test_cli_rejects_missing_packages_even_when_auditor_returns_zero(self):
        self.write(self.pin("pip", "26.3") + self.pin("packaging", "26.0"))
        def run(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_text(json.dumps(self.report([])))
            return subprocess.CompletedProcess(command, 0)
        with patch.object(audit.subprocess, "run", side_effect=run):
            result = audit.main(["--output", str(self.output), "-r", str(self.path)])
        self.assertNotEqual(result, 0)
        self.assertTrue(self.output.is_file())

    def test_cli_preserves_auditor_failure_code(self):
        self.write(self.pin("pip", "26.3"))
        with patch.object(audit.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)):
            result = audit.main(["--output", str(self.output), "-r", str(self.path)])
        self.assertEqual(result, 7)

    def test_cli_does_not_clobber_an_existing_report(self):
        self.write(self.pin("pip", "26.3"))
        self.output.write_text("preserve this report")
        with patch.object(audit.subprocess, "run", side_effect=AssertionError("must not run")):
            result = audit.main(["--output", str(self.output), "-r", str(self.path)])
        self.assertNotEqual(result, 0)
        self.assertEqual(self.output.read_text(), "preserve this report")


if __name__ == "__main__":
    unittest.main()
