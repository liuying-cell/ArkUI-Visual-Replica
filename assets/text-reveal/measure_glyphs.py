#!/usr/bin/env python3
"""Measure relative half-brightness crossings for the lime-text reveal sample."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from analyze_motion_trace import load_capture_frames


def crossings(manifest, slots, count, fraction, expected_source):
    capture, frames = load_capture_frames(manifest)
    if capture.get('source') != expected_source:
        raise ValueError(f'{manifest.name} must contain a {expected_source} capture')
    width, height = slots['size']
    top, bottom = slots['yRange']
    edges = [round(slots['firstSlotX'] + index * slots['slotPitch']) for index in range(count + 1)]
    if not (0 <= edges[0] < edges[-1] <= width and 0 <= top < bottom <= height
            and all((stop - start) * (bottom - top) >= 8 for start, stop in zip(edges, edges[1:]))):
        raise ValueError('Configured glyph slots exceed the frame or contain too few pixels')

    scores = []
    for frame in frames:
        if frame.image.size != (width, height):
            raise ValueError(f'Expected {width}x{height}, got {frame.image.size} in {manifest}')
        rgb = np.asarray(frame.image)[top:bottom].astype(np.int16)
        contrast = np.maximum(0, rgb[:, :, 1] - rgb[:, :, 2] - 5)
        scores.append([np.partition(contrast[:, start:stop].ravel(), -8)[-8:].mean()
                       for start, stop in zip(edges, edges[1:])])

    scores = np.asarray(scores)
    if np.any(scores[0] >= 10) or np.any(scores[-1] <= 40):
        raise ValueError(f'Expected blank start and settled lime text in {manifest}')
    times = []
    for index, column in enumerate(scores.T):
        hits = np.flatnonzero(column >= fraction * column[-1])
        if not len(hits):
            raise ValueError(f'No detectable crossing for glyph {index + 1} in {manifest}')
        times.append(frames[hits[0]].timestamp_ms)
    return np.asarray(times)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path, help='Text reveal qa-config.json')
    parser.add_argument('report', type=Path, help='report.json from timing mode')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))['glyphTiming']
    report = json.loads(args.report.read_text(encoding='utf-8'))
    if report.get('mode') != 'timing':
        raise ValueError('Pass report.json from timing mode')
    glyphs = list(config['text'])
    threshold = config['crossingFraction']
    align = config['alignGlyphIndex']
    if not 0 < threshold < 1 or not 0 <= align < len(glyphs):
        raise ValueError('crossingFraction must be between 0 and 1 with a valid alignGlyphIndex')

    baseline = Path(report['referenceAnalysis']).with_name('capture.json')
    reference = crossings(baseline, config['reference'], len(glyphs), threshold, 'browser-screencast')
    target = crossings(Path(report['targetCapture']), config['target'], len(glyphs), threshold, 'emulator-window')
    order_passed = bool(np.all(np.diff(reference) > 0) and np.all(np.diff(target) > 0))
    reference -= reference[align]
    target -= target[align]
    delta = target - reference
    max_delta = float(np.max(np.abs(delta)))
    tolerance = config['toleranceMs']
    passed = order_passed and max_delta <= tolerance
    print(json.dumps({
        'glyphs': glyphs,
        'crossingFraction': threshold,
        'alignGlyphIndex': align,
        'expectedOffsetsMs': [(index - align) * config['staggerMs'] for index in range(len(glyphs))],
        'referenceMs': reference.round(1).tolist(),
        'targetMs': target.round(1).tolist(),
        'deltaMs': delta.round(1).tolist(),
        'maxAbsDeltaMs': round(max_delta, 1),
        'ordered': order_passed,
        'toleranceMs': tolerance,
        'passed': passed,
    }, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(2)
