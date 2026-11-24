#!/usr/bin/env python3
"""Validate the structural invariants of an ArkUI motion contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TIMING_ANCHORS = {
    "firstMotionMs",
    "peakMotionMs",
    "lastMotionMs",
}
TRIGGER_NAMES = {
    "scene-enter",
    "tap",
    "tap-or-pan",
    "scroll-progress",
    "state-change",
    "route-enter",
    "route-exit",
    "long-press",
    "drag-release",
}


def require(condition: bool, path: str, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(f"{path}: {message}")


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_contract(data: Any, contract_path: Path, check_paths: bool) -> list[str]:
    errors: list[str] = []
    require(isinstance(data, dict), "$", "contract must be a JSON object", errors)
    if not isinstance(data, dict):
        return errors

    require(data.get("schemaVersion") == 1, "$.schemaVersion", "must equal 1", errors)
    require(bool(NAME_RE.fullmatch(str(data.get("id", "")))), "$.id", "must be lowercase hyphen-case", errors)

    source = data.get("source")
    require(isinstance(source, dict), "$.source", "must be an object", errors)
    if isinstance(source, dict):
        source_type = source.get("type")
        require(source_type in {"html", "image", "video", "description"}, "$.source.type",
                "must be html, image, video, or description", errors)
        if source_type in {"html", "image", "video"}:
            source_path = source.get("path")
            require(non_empty_string(source_path), "$.source.path", "must be a non-empty string", errors)
            if check_paths and non_empty_string(source_path):
                resolved = (contract_path.parent / source_path).resolve()
                require(resolved.exists(), "$.source.path", f"file does not exist: {resolved}", errors)
        viewport = source.get("viewport")
        require(isinstance(viewport, dict), "$.source.viewport", "must be an object", errors)
        if isinstance(viewport, dict):
            for key in ("width", "height"):
                value = viewport.get(key)
                require(isinstance(value, (int, float)) and value > 0, f"$.source.viewport.{key}",
                        "must be a positive number", errors)
            require(non_empty_string(viewport.get("unit")), "$.source.viewport.unit",
                    "must be a non-empty string", errors)

    target = data.get("target")
    require(isinstance(target, dict), "$.target", "must be an object", errors)
    if isinstance(target, dict):
        require(non_empty_string(target.get("platform")), "$.target.platform",
                "must be a non-empty string", errors)
        api_level = target.get("apiLevel")
        require(isinstance(api_level, int) and api_level >= 1, "$.target.apiLevel",
                "must be a positive integer", errors)
        require(non_empty_string(target.get("unit")), "$.target.unit",
                "must be a non-empty string", errors)

    scenes = data.get("scenes")
    require(isinstance(scenes, list) and bool(scenes), "$.scenes", "must be a non-empty array", errors)
    seen_ids: set[str] = set()
    if isinstance(scenes, list):
        for index, scene in enumerate(scenes):
            prefix = f"$.scenes[{index}]"
            require(isinstance(scene, dict), prefix, "must be an object", errors)
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("id")
            require(bool(NAME_RE.fullmatch(str(scene_id or ""))), f"{prefix}.id",
                    "must be lowercase hyphen-case", errors)
            if non_empty_string(scene_id):
                require(scene_id not in seen_ids, f"{prefix}.id", "must be unique", errors)
                seen_ids.add(scene_id)

            trigger = scene.get("trigger")
            require(isinstance(trigger, dict), f"{prefix}.trigger", "must be an object", errors)
            if isinstance(trigger, dict):
                trigger_type = trigger.get("type")
                require(trigger_type in TRIGGER_NAMES, f"{prefix}.trigger.type",
                        f"must be one of {sorted(TRIGGER_NAMES)}", errors)

            duration = scene.get("durationMs")
            require(duration is None or (isinstance(duration, (int, float)) and duration >= 0),
                    f"{prefix}.durationMs", "must be null or a non-negative number", errors)

            properties = scene.get("properties")
            require(isinstance(properties, list) and bool(properties), f"{prefix}.properties",
                    "must be a non-empty array", errors)
            if isinstance(properties, list):
                for prop_index, prop in enumerate(properties):
                    require(non_empty_string(prop), f"{prefix}.properties[{prop_index}]",
                            "must be a non-empty string", errors)

            require(non_empty_string(scene.get("interruption")), f"{prefix}.interruption",
                    "must describe interruption behavior", errors)
            require(non_empty_string(scene.get("accessibility")), f"{prefix}.accessibility",
                    "must describe the non-motion access path", errors)
            require(non_empty_string(scene.get("performance")), f"{prefix}.performance",
                    "must state the performance constraint", errors)

            timing = scene.get("timingValidation")
            if timing is not None:
                require(isinstance(timing, dict), f"{prefix}.timingValidation", "must be an object", errors)
                if isinstance(timing, dict):
                    sampling = timing.get("sampling")
                    require(isinstance(sampling, dict), f"{prefix}.timingValidation.sampling",
                            "must be an object", errors)
                    if isinstance(sampling, dict):
                        require(non_empty_string(sampling.get("reference")),
                                f"{prefix}.timingValidation.sampling.reference",
                                "must name the reference sampling method", errors)
                        require(non_empty_string(sampling.get("target")),
                                f"{prefix}.timingValidation.sampling.target",
                                "must name the target sampling method", errors)

                    checkpoints = timing.get("checkpoints")
                    require(isinstance(checkpoints, list) and bool(checkpoints),
                            f"{prefix}.timingValidation.checkpoints",
                            "must be a non-empty array", errors)
                    if isinstance(checkpoints, list):
                        for checkpoint_index, checkpoint in enumerate(checkpoints):
                            checkpoint_path = f"{prefix}.timingValidation.checkpoints[{checkpoint_index}]"
                            require(isinstance(checkpoint, dict), checkpoint_path, "must be an object", errors)
                            if isinstance(checkpoint, dict):
                                require(non_empty_string(checkpoint.get("name")),
                                        f"{checkpoint_path}.name",
                                        "must be a non-empty string", errors)
                                require(checkpoint.get("anchor") in TIMING_ANCHORS,
                                        f"{checkpoint_path}.anchor",
                                        f"must be one of {sorted(TIMING_ANCHORS)}", errors)
                                tolerance = checkpoint.get("toleranceMs")
                                require(isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool)
                                        and tolerance > 0,
                                        f"{checkpoint_path}.toleranceMs",
                                        "must be a positive number", errors)

                    evidence = timing.get("evidence")
                    if evidence is not None:
                        require(isinstance(evidence, dict), f"{prefix}.timingValidation.evidence",
                                "must be an object", errors)
                        if isinstance(evidence, dict):
                            require(non_empty_string(evidence.get("comparison")),
                                    f"{prefix}.timingValidation.evidence.comparison",
                                    "must be a non-empty string", errors)

            gesture = scene.get("gesture")
            if gesture is not None:
                require(isinstance(gesture, dict), f"{prefix}.gesture", "must be an object", errors)
                if isinstance(gesture, dict) and "axis" in gesture:
                    require(gesture.get("axis") in {"horizontal", "vertical", "both"},
                            f"{prefix}.gesture.axis", "must be horizontal, vertical, or both", errors)

            progress = scene.get("progress")
            if progress is not None:
                require(isinstance(progress, dict), f"{prefix}.progress", "must be an object", errors)
                if isinstance(progress, dict):
                    for key in ("start", "end"):
                        value = progress.get(key)
                        require(isinstance(value, (int, float)), f"{prefix}.progress.{key}",
                                "must be a number", errors)
                    if isinstance(progress.get("start"), (int, float)) and isinstance(progress.get("end"), (int, float)):
                        require(progress.get("start") != progress.get("end"),
                                f"{prefix}.progress", "start and end must differ", errors)
                    require(isinstance(progress.get("clamped"), bool), f"{prefix}.progress.clamped",
                            "must be a boolean", errors)

            keyframes = scene.get("keyframes")
            if keyframes is not None:
                require(isinstance(keyframes, list) and bool(keyframes), f"{prefix}.keyframes",
                        "must be a non-empty array", errors)
                if isinstance(keyframes, list):
                    for frame_index, frame in enumerate(keyframes):
                        frame_path = f"{prefix}.keyframes[{frame_index}]"
                        require(isinstance(frame, dict), frame_path, "must be an object", errors)
                        if isinstance(frame, dict):
                            at = frame.get("at")
                            require(isinstance(at, (int, float)) and 0 <= at <= 1,
                                    f"{frame_path}.at", "must be between 0 and 1", errors)

            particles = scene.get("particles")
            if particles is not None:
                require(isinstance(particles, dict), f"{prefix}.particles", "must be an object", errors)
                if isinstance(particles, dict):
                    count = particles.get("count")
                    require(isinstance(count, int) and count > 0, f"{prefix}.particles.count",
                            "must be a positive integer", errors)
                    stagger = particles.get("staggerMs", 0)
                    require(isinstance(stagger, (int, float)) and stagger >= 0,
                            f"{prefix}.particles.staggerMs", "must be a non-negative number", errors)
                    duration = particles.get("durationMs")
                    if duration is not None:
                        require(isinstance(duration, (int, float)) and duration >= 0,
                                f"{prefix}.particles.durationMs", "must be a non-negative number", errors)

            spring = scene.get("spring")
            if spring is not None:
                require(isinstance(spring, dict), f"{prefix}.spring", "must be an object", errors)
                if isinstance(spring, dict):
                    response = spring.get("response")
                    damping = spring.get("dampingFraction")
                    require(isinstance(response, (int, float)) and response > 0,
                            f"{prefix}.spring.response", "must be a positive number", errors)
                    require(isinstance(damping, (int, float)) and damping > 0,
                            f"{prefix}.spring.dampingFraction", "must be a positive number", errors)

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path, help="Path to a motion contract JSON file")
    parser.add_argument("--no-path-check", action="store_true",
                        help="Do not require source.path to exist relative to the contract")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = args.contract.expanduser().resolve()
    if not contract_path.is_file():
        print(f"ERROR: contract not found: {contract_path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 2

    errors = validate_contract(data, contract_path, not args.no_path_check)
    if errors:
        print(f"INVALID: {contract_path}", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    scenes = data["scenes"]
    print(f"OK: {contract_path}")
    print(f"  scenes: {len(scenes)} -> {', '.join(scene['id'] for scene in scenes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
