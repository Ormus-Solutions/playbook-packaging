"""Offline tests: they pin the behaviour on synthetic data, with no setup.

Run them with: python3 -m unittest discover -s tests
Replace them with tests for your own tool, and keep the demo test: it proves
that examples/run.sh still prints examples/expected-output.txt.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import tool  # the reference implementation in src/tool.py


class SummarizeTest(unittest.TestCase):
    def test_counts_tasks_per_lane_and_state(self) -> None:
        tasks = [
            {"lane": "api", "state": "open"},
            {"lane": "api", "state": "done"},
            {"lane": "web", "state": "open"},
        ]
        self.assertEqual(
            tool.summarize(tasks, ["api", "web"], ["open", "done"]),
            "lane  open  done\n"
            "api      1     1\n"
            "web      1     0\n",
        )

    def test_unknown_lane_and_state_are_counted_as_other(self) -> None:
        tasks = [{"lane": "ops", "state": "open"}, {"lane": "api", "state": "blocked"}]
        self.assertEqual(
            tool.summarize(tasks, ["api"], ["open"]),
            "lane   open  other\n"
            "api       0      1\n"
            "other     1      0\n",
        )

    def test_title_comes_first(self) -> None:
        out = tool.summarize([], ["api"], ["open"], "demo board")
        self.assertEqual(out.splitlines()[0], "demo board")


class ConfigTest(unittest.TestCase):
    def test_missing_config_says_what_to_do(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as caught:
                tool.load_config(Path(tmp) / "config.toml")
        self.assertIn("examples/config.example.toml", str(caught.exception))

    def test_lanes_must_be_a_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('lanes = "api"\nstates = ["open"]\n', encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                tool.load_config(path)
        self.assertIn("'lanes' must be a list", str(caught.exception))

    def test_other_is_kept_for_names_not_in_the_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('lanes = ["api", "other"]\nstates = ["open"]\n', encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                tool.load_config(path)
        self.assertIn("'other' is kept", str(caught.exception))


class DemoTest(unittest.TestCase):
    def test_demo_prints_the_expected_output(self) -> None:
        done = subprocess.run(["bash", str(ROOT / "examples" / "run.sh")],
                              capture_output=True, text=True, check=True)
        expected = (ROOT / "examples" / "expected-output.txt").read_text(encoding="utf-8")
        self.assertEqual(done.stdout, expected)


if __name__ == "__main__":
    unittest.main()
