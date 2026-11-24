#!/usr/bin/env python3
"""Deterministic smoke tests for the motion timing analysis tools."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_motion_trace.py"
VALIDATOR = SCRIPT_DIR / "validate_motion_contract.py"


class TimingToolTests(unittest.TestCase):
    def make_capture(self, root: Path, shift: int = 0, motion_start: int = 3) -> Path:
        frames_dir = root / "frames"
        frames_dir.mkdir(parents=True)
        timestamps = [-100, -50, 0, 50, 100, 150, 200, 250, 300, 350, 400, 450]
        frames = []
        for index, timestamp in enumerate(timestamps):
            image = Image.new("RGB", (160, 240), (4, 6, 8))
            draw = ImageDraw.Draw(image)
            progress = 0 if index < motion_start else min(1.0, (index - motion_start + 1) / 5.0)
            offset = shift if index >= motion_start else 0
            size = 30 + round(20 * progress)
            x = 65 + offset
            y = 95 - round(18 * progress)
            draw.rounded_rectangle((x, y, x + size, y + size), radius=8, fill=(220, 255, 90))
            name = f"frame_{index:03d}.png"
            image.save(frames_dir / name)
            frames.append(
                {
                    "index": index,
                    "file": name,
                    "timestampMs": timestamp,
                    "timeBasis": "test",
                }
            )
        manifest = {
            "schemaVersion": 1,
            "kind": "motion-capture",
            "source": "synthetic",
            "capturedAt": "2026-11-23T00:00:00+00:00",
            "preRollMs": 100,
            "durationMs": 450,
            "trigger": {"type": "synthetic"},
            "coverage": {"frameCount": len(frames)},
            "frameDirectory": "frames",
            "frames": frames,
            "notes": ["synthetic"],
        }
        path = root / "capture.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def run_analyzer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ANALYZER), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )

    def test_analyze_detects_motion_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = self.make_capture(root)
            result = self.run_analyzer("analyze", str(capture), "--threshold", "0.2")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            analysis = json.loads((root / "analysis.json").read_text(encoding="utf-8"))
            self.assertIsNotNone(analysis["summary"]["firstMotionMs"])
            self.assertGreaterEqual(analysis["summary"]["firstMotionMs"], 0.0)
            self.assertGreater(analysis["summary"]["peakMotionMs"], 100.0)
            self.assertTrue((root / "analysis.md").is_file())
            self.assertTrue((root / "contact-sheet.jpg").is_file())

    def test_compare_reports_pass_and_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference_dir = root / "reference"
            target_dir = root / "target"
            reference_dir.mkdir()
            target_dir.mkdir()
            reference_capture = self.make_capture(reference_dir)
            target_capture = self.make_capture(target_dir, shift=2, motion_start=4)
            for capture in (reference_capture, target_capture):
                result = self.run_analyzer("analyze", str(capture), "--threshold", "0.2")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            pass_result = self.run_analyzer(
                "compare",
                str(reference_dir / "analysis.json"),
                str(target_dir / "analysis.json"),
                "--checkpoints",
                "firstMotionMs,peakMotionMs",
                "--tolerance-ms",
                "100",
                "--output",
                str(root / "pass.json"),
            )
            self.assertEqual(pass_result.returncode, 0, pass_result.stdout + pass_result.stderr)
            fail_result = self.run_analyzer(
                "compare",
                str(reference_dir / "analysis.json"),
                str(target_dir / "analysis.json"),
                "--checkpoints",
                "firstMotionMs",
                "--tolerance-ms",
                "0.001",
                "--output",
                str(root / "fail.json"),
            )
            self.assertNotEqual(fail_result.returncode, 0)

    def test_contract_timing_validation_rejects_unsupported_anchor(self) -> None:
        contract = {
            "schemaVersion": 1,
            "id": "validator-timing-test",
            "source": {
                "type": "description",
                "scene": "test",
                "viewport": {"width": 390, "height": 844, "unit": "css-px"},
            },
            "target": {"platform": "HarmonyOS NEXT", "apiLevel": 18, "unit": "vp"},
            "scenes": [
                {
                    "id": "timing-scene",
                    "trigger": {"type": "tap"},
                    "durationMs": 200,
                    "properties": ["opacity"],
                    "interruption": "A new tap restarts from the current opacity.",
                    "accessibility": "A labelled button triggers the same state change.",
                    "performance": "Animate opacity only.",
                    "timingValidation": {
                        "sampling": {
                            "reference": "browser-screencast",
                            "target": "emulator-window",
                        },
                        "checkpoints": [
                            {
                                "name": "first-motion",
                                "anchor": "firstMotionMs",
                                "toleranceMs": 75,
                            }
                        ],
                        "evidence": {"comparison": "outputs/comparison.json"},
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            valid = subprocess.run(
                [sys.executable, str(VALIDATOR), str(path), "--no-path-check"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            contract["scenes"][0]["timingValidation"]["checkpoints"][0]["anchor"] = "unknownAnchorMs"
            path.write_text(json.dumps(contract), encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(VALIDATOR), str(path), "--no-path-check"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("anchor", invalid.stderr)

if __name__ == "__main__":
    unittest.main()
