#!/usr/bin/env python3
"""Run one motion QA scene and save capture, analysis, and verdicts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from capture_motion import find_browser, find_hdc, run_command

SCRIPTS = Path(__file__).resolve().parent
ANCHORS = {"firstMotionMs", "peakMotionMs", "lastMotionMs"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(script, *args):
    command = [sys.executable, str(SCRIPTS / script), *map(str, args)]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=90)
    if result.returncode:
        raise RuntimeError(f"{script} ({result.returncode}): {(result.stderr or result.stdout).strip()}")


def analyze(capture, destination, roi):
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "analysis.json"
    args = ["--roi", roi] if roi else []
    run("analyze_motion_trace.py", "analyze", capture, *args, "--json-output", output,
        "--markdown-output", destination / "analysis.md", "--contact-sheet", destination / "contact-sheet.jpg")
    return output


def reference_baseline(reference, config_dir, output, fresh, min_fps, anchors):
    entry = (config_dir / reference["entry"]).resolve()
    inputs = [entry, *((config_dir / path).resolve() for path in reference.get("inputs", []))]
    browser = find_browser(reference.get("browser")).resolve()
    digest = hashlib.sha256(json.dumps(reference, sort_keys=True).encode())
    for path in [*inputs, SCRIPTS / "capture_motion.py", SCRIPTS / "analyze_motion_trace.py"]:
        digest.update(str(path).encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    digest.update(f"{browser}:{browser.stat().st_mtime_ns}".encode())
    cache = output / "reference-cache"
    cache.mkdir(exist_ok=True)
    marker = cache / f"{digest.hexdigest()}.txt"
    if marker.is_file() and not fresh:
        candidate = cache / marker.read_text(encoding="utf-8").strip() / "analysis.json"
        if all(candidate.with_name(name).is_file() for name in ("capture.json", "analysis.json", "contact-sheet.jpg")):
            if not timing_issue(read_json(candidate), anchors, min_fps, "browser-screencast"):
                return candidate, True
    destination = Path(tempfile.mkdtemp(prefix="capture-", dir=cache))
    url = entry.as_uri() + ("?" + reference["query"] if reference.get("query") else "")
    run("capture_motion.py", "browser", "--url", url, "--browser", browser,
        "--width", reference.get("width", 390), "--height", reference.get("height", 844),
        "--duration-ms", reference.get("durationMs", 1400), "--output", destination,
        "--trigger-js", reference["triggerJs"])
    analysis = analyze(destination / "capture.json", destination, reference.get("roi"))
    if not timing_issue(read_json(analysis), anchors, min_fps, "browser-screencast"):
        pending = destination / "cache-pointer.txt"
        pending.write_text(destination.name, encoding="utf-8")
        pending.replace(marker)
    return analysis, False


def device_preflight(serial, explicit_hdc):
    hdc = find_hdc(explicit_hdc)
    targets = run_command([str(hdc), "list", "targets"], timeout=10).stdout.split()
    if serial not in targets:
        raise RuntimeError(f"device {serial} is unavailable (connected: {[item for item in targets if item != '[Empty]']})")
    return hdc


def prepare_target(target, serial, hdc):
    if target.get("resetClick"):
        x, y = target["resetClick"]
        run_command([str(hdc), "-t", serial, "shell", f"uitest uiInput click {x} {y}"], timeout=15)
        time.sleep(target.get("resetSettleMs", 350) / 1000)


def check_scene(expected, destination, serial, hdc, result):
    command = [str(hdc), "-t", serial]
    remote = f"/data/local/tmp/motion_qa_{uuid.uuid4().hex}"
    remote_layout = f"{remote}.json"
    remote_snapshot = f"{remote}.png"
    layout = destination / "preflight-layout.json"
    snapshot = destination / "preflight-screen.png"
    try:
        run_command([*command, "shell", f"uitest dumpLayout -p {remote_layout}"], timeout=12)
        run_command([*command, "file", "recv", remote_layout, str(layout)], timeout=12)
        result["layout"] = str(layout)
        nodes = [read_json(layout)]
        visible_text = {}
        while nodes:
            node = nodes.pop()
            attrs = node.get("attributes", {})
            if attrs.get("id") and attrs.get("visible") not in ("false", False):
                visible_text.setdefault(attrs["id"], set()).add(attrs.get("text", ""))
            nodes.extend(node.get("children", []))
        missing = []
        for item in expected:
            node_id = item["id"]
            actual = visible_text.get(node_id)
            if not actual or ("text" in item and item["text"] not in actual):
                missing.append({"expected": item, "visibleText": sorted(actual or ())})
        if missing:
            result["unmatched"] = missing
            raise RuntimeError("Scene or initial state mismatch. See sceneCheck.unmatched in report.json.")
        result["status"] = "pass"
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        try:
            run_command([*command, "shell", f"snapshot_display -f {remote_snapshot} -t png"], timeout=12)
            run_command([*command, "file", "recv", remote_snapshot, str(snapshot)], timeout=12)
            if snapshot.is_file():
                result["screenshot"] = str(snapshot)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            result["screenshotError"] = str(error)
        raise
    finally:
        try:
            run_command([*command, "shell", f"rm -f {remote_layout} {remote_snapshot}"], timeout=5)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            result["cleanupError"] = str(error)


def capture_target(target, destination, mode, serial, hdc):
    is_swipe = "triggerSwipe" in target
    trigger_flag = "--trigger-swipe" if is_swipe else "--trigger-click"
    coordinates = target["triggerSwipe" if is_swipe else "triggerClick"]
    args = ["--serial", serial, "--hdc", hdc, "--output", destination, trigger_flag,
            ",".join(map(str, coordinates)), "--swipe-velocity", target.get("swipeVelocity", 800),
            "--pre-roll-ms", target.get("preRollMs", 800 if mode == "quick" else 500),
            "--duration-ms", target.get("durationMs", 1800 if mode == "quick" else 1400)]
    if mode == "quick":
        run("capture_motion.py", "harmony", *args)
    else:
        if target.get("model"):
            args.extend(["--model", target["model"]])
        if target.get("crop"):
            args.extend(["--crop", ",".join(map(str, target["crop"]))])
        run("capture_emulator_window.py", *args)
    return destination / "capture.json"


def timing_issue(analysis, anchors, min_fps, expected_source):
    source = analysis.get("source")
    if source != expected_source:
        return f"expected {expected_source}, got {source}"
    fps = analysis["coverage"]["effectiveFps"] or 0
    if fps < min_fps:
        return f"capture coverage {fps:g} FPS is below {min_fps:g} FPS"
    if any(analysis["summary"].get(anchor) is None for anchor in anchors):
        return "at least one required anchor was not detected"
    frames = analysis["frameMetrics"]
    if frames[0]["timestampMs"] >= -20 or frames[-1]["timestampMs"] <= 0:
        return "missing capture around the trigger"
    if frames[-1].get("active") and "lastMotionMs" in anchors:
        return "motion is still active at the end of the recording"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path, help="Local scene JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("quick", "timing"), default="quick")
    parser.add_argument("--serial", help="Override the device in the scene")
    parser.add_argument("--hdc", help="Explicit hdc executable")
    parser.add_argument("--target-capture", type=Path, help="Analyze an existing capture.json without a device")
    parser.add_argument("--refresh-reference", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    scene = read_json(args.scene)
    target = scene.get("target", {})
    checks = scene.get("timing", {}) if args.mode == "timing" else {}
    anchors = checks.get("checkpoints", ["peakMotionMs"])
    min_fps = checks.get("minCaptureFps", 20)
    tolerance = checks.get("toleranceMs", 75)
    if not anchors or set(anchors) - ANCHORS or not (0 < min_fps < float("inf") and 0 < tolerance < float("inf")):
        raise ValueError("timing requires supported checkpoints and positive finite tolerance and capture FPS")
    output = args.output.resolve()
    serial = args.serial or target.get("serial")
    expected = target.get("expectedNodes", [])
    if not args.target_capture:
        if not isinstance(expected, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip()
            or ("text" in item and not isinstance(item["text"], str))
            for item in expected
        ):
            raise ValueError("target.expectedNodes must be a list of node IDs with optional text")
        if not serial:
            raise ValueError("set target.serial or pass --serial")
        if ("triggerClick" in target) == ("triggerSwipe" in target):
            raise ValueError("set exactly one of target.triggerClick and target.triggerSwipe")
        for key, size in (("triggerClick", 2), ("triggerSwipe", 4), ("resetClick", 2), ("crop", 4)):
            if key in target:
                values = target[key]
                if not isinstance(values, list) or len(values) != size or any(type(value) is not int or value < 0 for value in values):
                    raise ValueError(f"target.{key} needs {size} non-negative integers")
        hdc = device_preflight(serial, args.hdc)
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    print(f"Evidence directory: {work}", flush=True)
    report = {"scene": scene["id"], "mode": args.mode, "status": "error"}
    try:
        if not args.target_capture and expected:
            prepare_target(target, serial, hdc)
            report["sceneCheck"] = {"status": "fail", "expectedNodes": expected}
            check_scene(expected, work, serial, hdc, report["sceneCheck"])
        if args.mode == "timing":
            baseline, cached = reference_baseline(scene["reference"], args.scene.resolve().parent,
                                                 output, args.refresh_reference, min_fps, anchors)
            report.update(referenceAnalysis=str(baseline), referenceReused=cached)
        if args.target_capture:
            capture = args.target_capture.resolve()
        else:
            if not expected:
                prepare_target(target, serial, hdc)
            capture = capture_target(target, work / "target", args.mode, serial, hdc)
        roi = target.get(f"{args.mode}Roi", target.get("roi"))
        target_analysis = analyze(capture, work / "target", roi)
        analysis = read_json(target_analysis)
        report.update(targetCapture=str(capture), targetAnalysis=str(target_analysis),
                      captureFps=analysis["coverage"]["effectiveFps"])
        trigger = read_json(capture).get("trigger", {})
        start, end = trigger.get("sentOffsetMs"), trigger.get("completedOffsetMs")
        if start is not None and end is not None:
            report["inputWindowMs"] = {"sent": start, "returned": end, "duration": round(end - start, 3)}
            report["timingOrigin"] = "Input command return. The actual input time can fall inside the recorded interval."
        if args.mode == "quick":
            report.update(status="review-sampled-states", contactSheet=str(target_analysis.with_name("contact-sheet.jpg")))
        else:
            for label, evidence, source in (("reference", read_json(baseline), "browser-screencast"),
                                            ("target", analysis, "emulator-window")):
                issue = timing_issue(evidence, anchors, min_fps, source)
                if issue:
                    report.update(status="inconclusive", reason=f"{label}: {issue}")
                    break
            else:
                comparison = work / "comparison.json"
                run("analyze_motion_trace.py", "compare", baseline, target_analysis, "--checkpoints", ",".join(anchors),
                    "--tolerance-ms", tolerance, "--output", comparison, "--allow-failure")
                result = read_json(comparison)
                report.update(status="pass" if result["passed"] else "fail", comparison=str(comparison),
                              toleranceMs=tolerance, checkpoints=result["rows"])
    except Exception as error:
        report["reason"] = str(error)
        raise
    finally:
        report["elapsedSeconds"] = round(time.monotonic() - started, 2)
        write_json(work / "report.json", report)
        print(f"{report['status']}: {work / 'report.json'}", flush=True)
    return {"pass": 0, "review-sampled-states": 0, "fail": 1, "inconclusive": 2}[report["status"]]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
