"""Tests for src/playbook_lint.py: it checks a repo against the standard."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from support import BASH, LINT, NEW, ROOT, env, run

FINISHED = ROOT / "examples" / "lane-counts"


class LintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lint-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "playbook-lane-counts"
        made = run([BASH, str(NEW), "lane-counts", str(self.repo)], env=env(bare=False))
        self.assertEqual(made.returncode, 0, made.stderr)

    def finish(self) -> None:
        for name in ("README.md", "PLAYBOOK.md", "LICENSE"):
            shutil.copy(FINISHED / name, self.repo / name)

    def lint(self, repo: Path | None = None):
        return run([sys.executable, str(LINT), str(repo or self.repo)])

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.repo / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def test_the_finished_example_passes(self) -> None:
        self.finish()
        done = self.lint()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertTrue(done.stdout.endswith("lint: ok\n"))

    def test_a_fresh_copy_lists_the_files_to_fill(self) -> None:
        done = self.lint()
        self.assertEqual(done.returncode, 1)
        for name in ("README.md", "PLAYBOOK.md", "LICENSE"):
            self.assertRegex(done.stdout, rf"(?m)^  {name}: \d+ lines? with a placeholder")

    def test_a_missing_section_is_named(self) -> None:
        self.finish()
        self.edit("PLAYBOOK.md", "## Undo", "## Removal")
        done = self.lint()
        self.assertEqual(done.returncode, 1)
        self.assertIn('PLAYBOOK.md: missing section "## Undo"', done.stdout)

    def test_a_step_needs_verify_and_expected(self) -> None:
        self.finish()
        self.edit("PLAYBOOK.md", "Verify: `python3 -c 'import tomllib", "Check: `python3 -c 'import tomllib")
        self.edit("PLAYBOOK.md", "Expected: `['lanes'", "Result: `['lanes'")
        done = self.lint()
        self.assertIn('step "2. Make your config file" has no "Verify:" line', done.stdout)
        self.assertIn('step "2. Make your config file" has no "Expected:" line', done.stdout)

    def test_a_step_must_be_numbered(self) -> None:
        self.finish()
        self.edit("PLAYBOOK.md", "### 3. Put your own lanes in it", "### Put your own lanes in it")
        done = self.lint()
        self.assertIn('step "Put your own lanes in it" is not numbered', done.stdout)

    def test_a_heading_inside_a_code_block_does_not_count(self) -> None:
        self.finish()
        self.edit("README.md", "## Credits\n", "```text\n## Credits\n```\n")
        done = self.lint()
        self.assertIn('README.md: missing section "## Credits"', done.stdout)

    def test_the_agent_prompt_must_name_the_playbook(self) -> None:
        self.finish()
        self.edit("README.md", "Read PLAYBOOK.md in this repo", "Read the docs in this repo")
        done = self.lint()
        self.assertIn("the agent path needs a prompt in a code block that names PLAYBOOK.md",
                      done.stdout)

    def test_check_sh_must_be_executable(self) -> None:
        self.finish()
        (self.repo / "check.sh").chmod(0o644)
        done = self.lint()
        self.assertIn("check.sh: not executable", done.stdout)

    def test_an_empty_tests_folder_fails(self) -> None:
        self.finish()
        shutil.rmtree(self.repo / "tests")
        (self.repo / "tests").mkdir()
        done = self.lint()
        self.assertIn("tests/: missing or empty", done.stdout)

    def test_this_repo_follows_its_own_standard(self) -> None:
        done = self.lint(ROOT)
        self.assertEqual(done.returncode, 0, done.stdout)


if __name__ == "__main__":
    unittest.main()
