"""Tests for scripts/new.sh: it makes a playbook repo from the template."""
from __future__ import annotations

import filecmp
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from support import BASH, NEW, ROOT, env, run

PLACEHOLDERS = ["{{" + name + "}}" for name in ("slug", "title", "year", "date")]


class NewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="new-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def new(self, slug: str, dest: Path):
        return run([BASH, str(NEW), slug, str(dest)], env=env(bare=False))

    def test_makes_a_repo_with_every_file_of_the_standard(self) -> None:
        dest = self.tmp / "playbook-lane-counts"
        done = self.new("lane-counts", dest)
        self.assertEqual(done.returncode, 0, done.stderr)
        for name in ("README.md", "PLAYBOOK.md", "LICENSE", "CHANGELOG.md", ".gitignore",
                     "check.sh", "scripts/scrub.sh", "src/tool.py", "examples/run.sh",
                     "examples/expected-output.txt", "tests/test_tool.py"):
            self.assertTrue((dest / name).is_file(), name)
        for name in ("check.sh", "scripts/scrub.sh", "examples/run.sh"):
            self.assertTrue(os.access(dest / name, os.X_OK), name)

    def test_fills_the_slug_title_year_and_date(self) -> None:
        dest = self.tmp / "out"
        self.new("lane-counts", dest)
        self.assertEqual((dest / "README.md").read_text().splitlines()[0], "# Lane counts")
        self.assertIn("playbook-lane-counts/config.toml", (dest / "src/tool.py").read_text())
        for path in dest.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                text = path.read_text(errors="replace")
                for marker in PLACEHOLDERS:
                    self.assertNotIn(marker, text, f"{path.name} still has {marker}")

    def test_the_repo_starts_on_main_with_no_commit(self) -> None:
        dest = self.tmp / "out"
        self.new("lane-counts", dest)
        branch = run(["git", "-C", str(dest), "symbolic-ref", "--short", "HEAD"])
        self.assertEqual(branch.stdout.strip(), "main")
        head = run(["git", "-C", str(dest), "rev-parse", "--verify", "-q", "HEAD"])
        self.assertNotEqual(head.returncode, 0)

    def test_the_new_repo_tests_pass_and_its_gate_lists_the_placeholders(self) -> None:
        dest = self.tmp / "out"
        self.new("lane-counts", dest)
        tests = run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=dest)
        self.assertEqual(tests.returncode, 0, tests.stderr)
        gate = run([BASH, str(dest / "check.sh")], env=env(bare=False))
        self.assertEqual(gate.returncode, 1)
        self.assertIn("fill the placeholders above", gate.stderr)

    def test_a_playbook_prefix_is_not_doubled(self) -> None:
        dest = self.tmp / "out"
        done = self.new("playbook-demo-api", dest)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Created playbook-demo-api", done.stdout)
        self.assertEqual((dest / "README.md").read_text().splitlines()[0], "# Demo api")

    def test_a_bad_slug_is_refused(self) -> None:
        for slug in ("Lane_Counts", "lane--counts", "-lane", "lane counts", ""):
            with self.subTest(slug=slug):
                done = self.new(slug, self.tmp / "out")
                self.assertEqual(done.returncode, 2)
                self.assertFalse((self.tmp / "out").exists())

    def test_a_folder_that_is_not_empty_is_left_alone(self) -> None:
        dest = self.tmp / "busy"
        dest.mkdir()
        (dest / "mine.txt").write_text("keep me\n")
        done = self.new("lane-counts", dest)
        self.assertEqual(done.returncode, 2)
        self.assertEqual(sorted(p.name for p in dest.iterdir()), ["mine.txt"])

    def test_the_template_scrub_is_an_exact_copy(self) -> None:
        self.assertTrue(filecmp.cmp(ROOT / "scripts/scrub.sh",
                                    ROOT / "template/scripts/scrub.sh", shallow=False),
                        "copy scripts/scrub.sh to template/scripts/scrub.sh")


if __name__ == "__main__":
    unittest.main()
