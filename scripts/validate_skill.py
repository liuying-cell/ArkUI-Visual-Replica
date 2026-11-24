#!/usr/bin/env python3
"""Validate this skill's packaged structure, references, contracts, and scripts."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency failure is reported cleanly
    raise SystemExit(f"PyYAML is required to validate SKILL.md: {exc}") from exc


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*```")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata"}
TEXT_SUFFIXES = {
    ".md", ".py", ".js", ".ets", ".ts", ".json", ".json5", ".yaml", ".yml",
    ".html", ".css", ".txt", ".gitignore",
}
EVAL_WORKFLOWS = {"static", "visual-motion", "interaction-motion", "not-applicable"}
EVIDENCE_LEVELS = {"L0", "L1", "L2", "L3", "L4"}
JUNK_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db"}
JUNK_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak"}


class Validator:
    def __init__(self, root: Path, skip_smoke: bool = False) -> None:
        self.root = root.resolve()
        self.skip_smoke = skip_smoke
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def markdown_without_fences(self, text: str) -> str:
        kept: list[str] = []
        in_fence = False
        for line in text.splitlines():
            if FENCE_RE.match(line):
                in_fence = not in_fence
                kept.append("")
                continue
            kept.append("" if in_fence else line)
        return "\n".join(kept)

    def heading_slug(self, title: str) -> str:
        title = title.strip().lower()
        title = re.sub(r"<[^>]+>", "", title)
        title = re.sub(r"[`*_~]", "", title)
        title = re.sub(r"[^\w\u4e00-\u9fff -]", "", title)
        return re.sub(r"\s+", "-", title).strip("-")

    def anchors(self, text: str) -> set[str]:
        anchors: set[str] = set()
        in_fence = False
        for line in text.splitlines():
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = HEADING_RE.match(line)
            if match:
                anchors.add(self.heading_slug(match.group(2)))
        return anchors

    def validate_frontmatter(self) -> str:
        skill = self.root / "SKILL.md"
        if not skill.is_file():
            self.error("SKILL.md is missing")
            return ""
        text = self.read(skill)
        parts = re.split(r"(?m)^---\s*$", text, maxsplit=2)
        if len(parts) < 3 or parts[0].strip():
            self.error("SKILL.md must start with a YAML frontmatter block")
            return text
        try:
            data = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            self.error(f"SKILL.md frontmatter is invalid YAML: {exc}")
            return text
        if not isinstance(data, dict):
            self.error("SKILL.md frontmatter must be a mapping")
            return text
        extras = sorted(set(data) - ALLOWED_FRONTMATTER)
        if extras:
            self.error(f"Unsupported frontmatter keys: {', '.join(extras)}")
        name = str(data.get("name", "")).strip()
        if not NAME_RE.fullmatch(name) or len(name) > 64:
            self.error("frontmatter name must be lowercase hyphen-case and at most 64 characters")
        if name != self.root.name.casefold():
            self.error(f"frontmatter name '{name}' must match folder '{self.root.name}'")
        description = str(data.get("description", "")).strip()
        if not description:
            self.error("frontmatter description is required")
        if len(description) > 1024:
            self.error("frontmatter description must be at most 1024 characters")
        if "<" in description or ">" in description:
            self.error("frontmatter description must not contain angle brackets")
        return text

    def validate_interface(self) -> None:
        path = self.root / "agents" / "openai.yaml"
        if not path.is_file():
            self.error("agents/openai.yaml is missing")
            return
        try:
            data = yaml.safe_load(self.read(path))
        except yaml.YAMLError as exc:
            self.error(f"agents/openai.yaml is invalid YAML: {exc}")
            return
        interface = data.get("interface") if isinstance(data, dict) else None
        if not isinstance(interface, dict):
            self.error("agents/openai.yaml must contain an interface mapping")
            return
        for key in ("display_name", "short_description", "default_prompt"):
            value = interface.get(key)
            if not isinstance(value, str) or not value.strip():
                self.error(f"agents/openai.yaml interface.{key} must be a non-empty string")
        short = interface.get("short_description")
        if isinstance(short, str) and not 25 <= len(short.strip()) <= 64:
            self.error("agents/openai.yaml short_description must contain 25-64 characters")
        prompt = interface.get("default_prompt")
        if isinstance(prompt, str) and "$arkui-visual-replica" not in prompt:
            self.warn("default_prompt does not explicitly name $arkui-visual-replica")

    def validate_reference_routing(self, skill_text: str) -> None:
        references_dir = self.root / "references"
        if not references_dir.is_dir():
            self.error("references directory is missing")
            return
        direct_targets = {
            Path(unquote(urlsplit(raw.strip()).path)).name
            for raw in LINK_RE.findall(skill_text)
            if urlsplit(raw.strip()).path.endswith(".md")
        }
        for path in sorted(references_dir.glob("*.md")):
            if path.name not in direct_targets:
                self.error(f"reference is not linked directly from SKILL.md: {path.name}")

    def validate_links(self) -> None:
        markdown_files = sorted(self.root.rglob("*.md"))
        for path in markdown_files:
            text = self.markdown_without_fences(self.read(path))
            for raw in LINK_RE.findall(text):
                target = raw.strip()
                if not target or target.startswith(("http://", "https://", "mailto:", "codex://")):
                    continue
                parsed = urlsplit(target)
                target_path = unquote(parsed.path)
                fragment = unquote(parsed.fragment)
                destination = (path.parent / target_path).resolve() if target_path else path.resolve()
                if not destination.exists():
                    self.error(f"broken local link in {path.relative_to(self.root)}: {target}")
                    continue
                if fragment and destination.suffix.lower() == ".md":
                    destination_text = self.markdown_without_fences(self.read(destination))
                    if fragment not in self.anchors(destination_text):
                        self.error(
                            f"broken anchor in {path.relative_to(self.root)}: {target}"
                        )

    def validate_long_references(self) -> None:
        for path in sorted((self.root / "references").glob("*.md")):
            lines = self.read(path).splitlines()
            if len(lines) < 100:
                continue
            preamble = "\n".join(lines[:40])
            if not re.search(r"(?m)^##\s+(?:Contents|目录)\s*$", preamble):
                self.error(f"reference over 100 lines needs a Contents section: {path.name}")

    def validate_evals(self) -> None:
        path = self.root / "evals" / "cases.json"
        if not path.is_file():
            self.error("evals/cases.json is missing")
            return
        try:
            data = json.loads(self.read(path))
        except json.JSONDecodeError as exc:
            self.error(f"invalid JSON in evals/cases.json: {exc}")
            return
        if not isinstance(data, dict) or data.get("schemaVersion") != 1:
            self.error("evals/cases.json must contain schemaVersion 1")
            return
        cases = data.get("cases")
        if not isinstance(cases, list) or len(cases) < 8:
            self.error("evals/cases.json must contain at least eight cases")
            return
        ids: set[str] = set()
        negative_count = 0
        workflows: set[str] = set()
        for index, case in enumerate(cases, start=1):
            label = f"evals/cases.json case {index}"
            if not isinstance(case, dict):
                self.error(f"{label} must be an object")
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not NAME_RE.fullmatch(case_id):
                self.error(f"{label} id must be lowercase hyphen-case")
            elif case_id in ids:
                self.error(f"{label} has duplicate id: {case_id}")
            else:
                ids.add(case_id)
            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                self.error(f"{label} prompt must be a non-empty string")
            should_trigger = case.get("shouldTrigger")
            if not isinstance(should_trigger, bool):
                self.error(f"{label} shouldTrigger must be boolean")
                continue
            workflow = case.get("workflow")
            if not isinstance(workflow, str) or workflow not in EVAL_WORKFLOWS:
                self.error(f"{label} workflow is not supported: {workflow}")
            else:
                workflows.add(workflow)
            references: dict[str, set[str]] = {}
            for field in ("requiredReferences", "forbiddenReferences"):
                values = case.get(field)
                if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                    self.error(f"{label} {field} must be a list of reference paths")
                    continue
                references[field] = set(values)
                for relative in values:
                    link = Path(relative)
                    destination = (self.root / link).resolve()
                    reference_root = self.root / "references"
                    if link.is_absolute() or reference_root not in destination.parents or not destination.is_file():
                        self.error(f"{label} {field} does not name a bundled reference: {relative}")
            required = references.get("requiredReferences", set())
            overlap = required & references.get("forbiddenReferences", set())
            if overlap:
                self.error(f"{label} required and forbidden references overlap: {sorted(overlap)}")
            level = case.get("minimumEvidenceLevel")
            if level is not None and (not isinstance(level, str) or level not in EVIDENCE_LEVELS):
                self.error(f"{label} minimumEvidenceLevel is invalid: {level}")
            acceptance = case.get("acceptance")
            if not isinstance(acceptance, list) or not acceptance or any(
                not isinstance(check, str) or not check.strip() for check in acceptance
            ):
                self.error(f"{label} needs non-empty acceptance checks")
            if should_trigger:
                if workflow == "not-applicable":
                    self.error(f"{label} triggered case must not use not-applicable workflow")
                if not required:
                    self.error(f"{label} triggered case needs requiredReferences")
                if level is None:
                    self.error(f"{label} triggered case needs minimumEvidenceLevel")
            else:
                negative_count += 1
                if workflow != "not-applicable":
                    self.error(f"{label} negative case must use not-applicable workflow")
                if required:
                    self.error(f"{label} negative case must not require references")
                if level is not None:
                    self.error(f"{label} negative case must use null minimumEvidenceLevel")
        if negative_count < 2:
            self.error("evals/cases.json needs at least two negative cases")
        if not {"static", "visual-motion", "interaction-motion"}.issubset(workflows):
            self.error("evals/cases.json must cover static, visual-motion, and interaction-motion workflows")

    def validate_contracts(self) -> None:
        validator = self.root / "scripts" / "validate_motion_contract.py"
        contracts = sorted((self.root / "assets").glob("motion-contract*.json"))
        if not contracts:
            self.warn("no motion contract fixtures found")
            return
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for path in contracts:
            result = subprocess.run(
                [sys.executable, str(validator), str(path), "--no-path-check"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=env,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                self.error(f"contract validation failed for {path.name}: {detail}")

        for path in sorted((self.root / "assets").glob("motion-qa*.json")):
            try:
                json.loads(self.read(path))
            except json.JSONDecodeError as exc:
                self.error(f"invalid JSON in {path.name}: {exc}")

    def validate_scripts(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for path in sorted((self.root / "scripts").glob("*.py")):
            try:
                compile(self.read(path), str(path), "exec")
            except SyntaxError as exc:
                self.error(f"Python syntax error in {path.name}: {exc}")
        for path in sorted((self.root / "scripts").glob("*.js")):
            result = subprocess.run(
                ["node", "--check", str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=env,
            )
            if result.returncode != 0:
                self.error(f"JavaScript syntax error in {path.name}: {(result.stderr or result.stdout).strip()}")
        if not self.skip_smoke:
            test_path = self.root / "scripts" / "test_timing_tools.py"
            result = subprocess.run(
                [sys.executable, str(test_path)],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=env,
            )
            if result.returncode != 0:
                self.error(f"timing smoke tests failed: {(result.stderr or result.stdout).strip()}")

    def validate_clean_package(self) -> None:
        for path in self.root.rglob("*"):
            relative = path.relative_to(self.root)
            if any(part in JUNK_NAMES for part in relative.parts):
                self.error(f"junk cache path remains: {relative}")
            if path.is_file() and path.suffix.lower() in JUNK_SUFFIXES:
                self.error(f"temporary artifact remains: {relative}")
        for path in self.root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path.name in {".gitignore", "validate_skill.py"}:
                continue
            text = self.read(path)
            for marker in ("TODO", "FIXME"):
                if re.search(rf"\b{marker}\b", text):
                    self.warn(f"unfinished marker {marker} in {path.relative_to(self.root)}")

    def run(self) -> int:
        skill_text = self.validate_frontmatter()
        self.validate_interface()
        self.validate_reference_routing(skill_text)
        self.validate_links()
        self.validate_long_references()
        self.validate_evals()
        self.validate_contracts()
        self.validate_scripts()
        self.validate_clean_package()
        for warning in self.warnings:
            print(f"WARN: {warning}")
        for error in self.errors:
            print(f"FAIL: {error}")
        if self.errors:
            print(f"Skill validation failed: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
            return 1
        print(f"Skill validation passed with {len(self.warnings)} warning(s)")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=Path(__file__).resolve().parent.parent,
        type=Path,
        help="Skill root directory (defaults to this script's parent skill)",
    )
    parser.add_argument("--skip-smoke", action="store_true", help="Skip the timing smoke tests")
    args = parser.parse_args()
    return Validator(args.root, skip_smoke=args.skip_smoke).run()


if __name__ == "__main__":
    raise SystemExit(main())
