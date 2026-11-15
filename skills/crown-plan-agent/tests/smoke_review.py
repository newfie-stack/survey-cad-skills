"""Run an offline review of an invented plan from a standalone skill folder."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

import fitz


def main() -> None:
    engine = Path(__file__).resolve().parents[1] / "engine"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        plan = root / "demo.pdf"
        scenario = root / "scenario.json"
        output = root / "review.md"
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((50, 60), "SKETCH")
            page.insert_text((50, 90), "SCALE 1:5000")
            page.insert_text((50, 120), "PLA 123456")
            page.insert_text((50, 150), "TOTAL AREA: 0.300 ha")
            document.save(plan)
        scenario.write_text(json.dumps({
            "land_class": "alberta_crown", "regulator": "AER", "disposition": "PLA", "stage": "initial",
            "plan_type": "sketch",
        }), encoding="utf-8")
        subprocess.run([
            sys.executable, str(engine / "review_cli.py"), str(plan),
            "--scenario", str(scenario), "--output", str(output),
            "--reference-cache", str(root / "empty-cache"), "--offline",
        ], cwd=root, check=True, capture_output=True, text=True)
        report = output.read_text(encoding="utf-8")
        for evidence in (
            "Observation: SKETCH", "Observation: SCALE 1:5000",
            "Observation: TOTAL AREA: 0.300 ha",
            "DISPOSITION_OBSERVED_IN_DRAWING_TEXT", "REVIEW_REQUIRED",
            "Download the current PLAR Table A2 PDF",
        ):
            if evidence not in report:
                raise RuntimeError(f"Synthetic review did not report {evidence!r}")
        print(report)
        print("Offline synthetic review passed.")


if __name__ == "__main__":
    main()
