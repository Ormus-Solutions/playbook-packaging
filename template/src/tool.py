#!/usr/bin/env python3
"""{{title}}: the reference implementation.

Replace this example with your own tool, and keep its shape:
- settings come from a config file, never hard-coded hosts or user paths;
- the core is a pure function (data in, text out), so it is easy to test;
- --demo runs on the synthetic data in examples/, so anyone can try it.

The example counts tasks per lane and state and prints a small table.

Usage:
    python3 src/tool.py --demo
    python3 src/tool.py tasks.json [--config ~/.config/playbook-{{slug}}/config.toml]
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
DEFAULT_CONFIG = Path("~/.config/playbook-{{slug}}/config.toml")
OTHER = "other"


def load_config(path: Path) -> dict:
    """Read the TOML config and check the keys the tool needs."""
    path = path.expanduser()
    if not path.is_file():
        raise SystemExit(f"no config at {path}: copy examples/config.example.toml "
                         "there and change it, or pass --config")
    with path.open("rb") as f:
        config = tomllib.load(f)
    for key in ("lanes", "states"):
        value = config.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
            raise SystemExit(f"config {path.name}: '{key}' must be a list of names")
        if OTHER in value:
            raise SystemExit(f"config {path.name}: '{OTHER}' is kept for names not in '{key}'")
    return config


def summarize(tasks: list[dict[str, str]], lanes: list[str], states: list[str],
              title: str = "") -> str:
    """Count tasks per lane and state.

    A lane or a state that is not in the config is counted under "other",
    so nothing is dropped without a trace. The "other" row and column only
    show when they hold something.
    """
    rows = [*lanes, OTHER]
    cols = [*states, OTHER]
    counts = {lane: dict.fromkeys(cols, 0) for lane in rows}
    for task in tasks:
        lane = task.get("lane") if task.get("lane") in lanes else OTHER
        state = task.get("state") if task.get("state") in states else OTHER
        counts[lane][state] += 1
    if not any(counts[OTHER].values()):
        rows.remove(OTHER)
    if not any(counts[lane][OTHER] for lane in rows):
        cols.remove(OTHER)

    first = max(len("lane"), *(len(r) for r in rows))
    widths = [max(4, len(c)) for c in cols]
    lines = [title] if title else []
    lines.append("lane".ljust(first) + "".join("  " + c.rjust(w) for c, w in zip(cols, widths)))
    for lane in rows:
        cells = "".join("  " + str(counts[lane][c]).rjust(w) for c, w in zip(cols, widths))
        lines.append(lane.ljust(first) + cells)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count tasks per lane and state.")
    parser.add_argument("tasks", nargs="?", help="a JSON file with a list of tasks")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help=f"the config file (default: {DEFAULT_CONFIG})")
    parser.add_argument("--demo", action="store_true",
                        help="run on the synthetic data in examples/")
    args = parser.parse_args(argv)
    if args.demo:
        config_path, tasks_path = EXAMPLES / "config.example.toml", EXAMPLES / "tasks.json"
    elif args.tasks:
        config_path, tasks_path = args.config, Path(args.tasks)
    else:
        parser.error("give a tasks file, or --demo")
    config = load_config(config_path)
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    sys.stdout.write(summarize(tasks, config["lanes"], config["states"], config.get("title", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
