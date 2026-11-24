#!/usr/bin/env python3
"""Create a standalone copy of a bundled HarmonyOS motion lab."""

import argparse
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent.parent
SCENES = ("intro", "scroll-and-burst", "navigation-and-gestures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", choices=SCENES)
    parser.add_argument("output", type=Path, help="New project directory outside the skill")
    args = parser.parse_args()
    target = args.output.resolve()
    if target.is_relative_to(ROOT):
        parser.error("choose a project directory outside the skill")
    if target.exists() or args.output.is_symlink():
        parser.error(f"output already exists: {args.output}")

    assets = ROOT / "assets"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=target.parent) as temp:
            project = Path(temp) / target.name
            copytree(assets / "harmonyos-motion-lab", project)
            if args.scene != "intro":
                copytree(assets / "harmonyos-motion-overlays" / args.scene, project, dirs_exist_ok=True)
            if target.exists() or target.is_symlink():
                parser.error(f"output already exists: {target}")
            project.rename(target)
    except OSError as error:
        parser.exit(1, f"Could not create motion lab: {error}\n")
    print(target)


if __name__ == "__main__":
    main()
