#!/usr/bin/env python3
"""Check that a playbook repo follows the packaging standard (STANDARD.md).

Usage: python3 src/playbook_lint.py [repo]      (default: the current folder)

It prints one line per problem, then a summary. Exit 0 when the repo follows
the standard, 1 when it does not, 2 on a usage error. It only reads files.

The pattern is a linter: rules a person would check by eye, written as code,
so an agent can run them after every change and a person can trust "lint: ok".
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FILES = ("README.md", "PLAYBOOK.md", "LICENSE", "CHANGELOG.md",
                  ".gitignore", "check.sh", "scripts/scrub.sh")
REQUIRED_DIRS = ("src", "examples", "tests")
README_SECTIONS = ("What it is", "What it saved me", "Who it is for", "Requirements",
                   "Quick start", "Preview", "Files", "Credits")
QUICK_START_PATHS = ("Hand it to your agent", "Do it by hand")
PLAYBOOK_SECTIONS = ("Goal", "Before you start", "Steps", "Adapt it", "Done when",
                     "Undo", "Safety")
# Built from parts so this file does not contain the markers it looks for.
PLACEHOLDERS = ("<" + "FILL:", "{{" + "slug}}", "{{" + "title}}",
                "{{" + "year}}", "{{" + "date}}")
# Where placeholders are looked for: the files of the standard, not other folders
# (this repo keeps its template/ full of placeholders on purpose).
PLACEHOLDER_SCOPE = ("README.md", "PLAYBOOK.md", "LICENSE", "CHANGELOG.md",
                     "check.sh", "src", "examples", "tests")


@dataclass
class Section:
    title: str
    level: int
    lines: list[str] = field(default_factory=list)


def sections(text: str) -> list[Section]:
    """Split Markdown into sections by heading, ignoring code blocks."""
    found: list[Section] = [Section("", 0)]
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if line[hashes:hashes + 1] == " ":
                found.append(Section(line[hashes:].strip(), hashes))
                continue
        found[-1].lines.append(line)
    return found


def find(found: list[Section], title: str, level: int) -> Section | None:
    for s in found:
        if s.level == level and s.title.lower().startswith(title.lower()):
            return s
    return None


def body_of(found: list[Section], start: Section) -> list[str]:
    """The lines of a section and of every deeper section under it."""
    out: list[str] = []
    inside = False
    for s in found:
        if s is start:
            inside = True
            out.extend(s.lines)
            continue
        if inside:
            if s.level <= start.level:
                break
            out.append("#" * s.level + " " + s.title)
            out.extend(s.lines)
    return out


def has_code_block(lines: list[str]) -> bool:
    return any(line.lstrip().startswith("```") for line in lines)


def check_readme(text: str) -> list[str]:
    problems: list[str] = []
    found = sections(text)
    if not any(s.level == 1 for s in found):
        problems.append("README.md: no title (a line that starts with '# ')")
    for title in README_SECTIONS:
        if find(found, title, 2) is None:
            problems.append(f'README.md: missing section "## {title}"')
    for title in QUICK_START_PATHS:
        sub = find(found, title, 3)
        if sub is None:
            problems.append(f'README.md: Quick start needs "### {title}"')
        elif title == QUICK_START_PATHS[0]:
            if not has_code_block(sub.lines) or "PLAYBOOK.md" not in "\n".join(sub.lines):
                problems.append("README.md: the agent path needs a prompt in a code "
                                "block that names PLAYBOOK.md")
    preview = find(found, "Preview", 2)
    if preview is not None:
        lines = body_of(found, preview)
        if not has_code_block(lines) and ".svg" not in "\n".join(lines):
            problems.append("README.md: Preview needs a code block or an SVG made "
                            "from the synthetic example")
    return problems


def check_playbook(text: str) -> list[str]:
    problems: list[str] = []
    found = sections(text)
    for title in PLAYBOOK_SECTIONS:
        if find(found, title, 2) is None:
            problems.append(f'PLAYBOOK.md: missing section "## {title}"')
    steps = find(found, "Steps", 2)
    if steps is not None:
        index = found.index(steps)
        numbered = []
        for s in found[index + 1:]:
            if s.level <= 2:
                break
            if s.level == 3:
                numbered.append(s)
        if not numbered:
            problems.append('PLAYBOOK.md: Steps has no step (a heading like "### 1. Do this")')
        for step in numbered:
            label = f'PLAYBOOK.md: step "{step.title}"'
            if not step.title.split(".")[0].strip().isdigit():
                problems.append(f"{label} is not numbered")
            starts = [line.strip() for line in body_of(found, step)]
            if not any(line.startswith("Verify:") for line in starts):
                problems.append(f'{label} has no "Verify:" line')
            if not any(line.startswith("Expected:") for line in starts):
                problems.append(f'{label} has no "Expected:" line')
    adapt = find(found, "Adapt it", 2)
    if adapt is not None:
        rows = [line for line in body_of(found, adapt) if line.lstrip().startswith("|")]
        if not rows or "setting" not in rows[0].lower():
            problems.append("PLAYBOOK.md: Adapt it needs a table with a Setting column")
    return problems


def placeholder_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for name in PLACEHOLDER_SCOPE:
        path = repo / name
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for folder, dirs, names in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                files.extend(Path(folder) / f for f in sorted(names))
    return files


def check_placeholders(repo: Path) -> list[str]:
    problems: list[str] = []
    for path in placeholder_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = [n for n, line in enumerate(text.splitlines(), 1)
                 if any(p in line for p in PLACEHOLDERS)]
        if lines:
            rel = path.relative_to(repo).as_posix()
            word = "line" if len(lines) == 1 else "lines"
            problems.append(f"{rel}: {len(lines)} {word} with a placeholder to fill "
                            f"(first: line {lines[0]})")
    return problems


def lint(repo: Path) -> list[str]:
    problems: list[str] = []
    for name in REQUIRED_FILES:
        if not (repo / name).is_file():
            problems.append(f"{name}: missing")
    for name in REQUIRED_DIRS:
        folder = repo / name
        if not folder.is_dir() or not any(folder.iterdir()):
            problems.append(f"{name}/: missing or empty")
    check = repo / "check.sh"
    if check.is_file() and not os.access(check, os.X_OK):
        problems.append("check.sh: not executable (chmod +x check.sh)")
    license_file = repo / "LICENSE"
    if license_file.is_file() and "MIT License" not in license_file.read_text(encoding="utf-8"):
        problems.append("LICENSE: not the MIT license")
    changelog = repo / "CHANGELOG.md"
    if changelog.is_file() and not any(
            line.startswith("## ") for line in changelog.read_text(encoding="utf-8").splitlines()):
        problems.append('CHANGELOG.md: no entry (a line like "## 0.1.0")')
    readme = repo / "README.md"
    if readme.is_file():
        problems += check_readme(readme.read_text(encoding="utf-8"))
    playbook = repo / "PLAYBOOK.md"
    if playbook.is_file():
        problems += check_playbook(playbook.read_text(encoding="utf-8"))
    problems += check_placeholders(repo)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a playbook repo against the standard.")
    parser.add_argument("repo", nargs="?", default=".", help="the playbook repo folder")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"lint: not a folder: {args.repo}", file=sys.stderr)
        return 2
    print(f"lint: {repo.name}")
    problems = lint(repo)
    for problem in problems:
        print(f"  {problem}")
    if problems:
        word = "problem" if len(problems) == 1 else "problems"
        print(f"lint: {len(problems)} {word}")
        return 1
    print("lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
