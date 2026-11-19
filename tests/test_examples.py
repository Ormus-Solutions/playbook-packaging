"""The demo in examples/run.sh prints exactly examples/expected-output.txt."""
from __future__ import annotations

import unittest

from support import BASH, ROOT, env, run


class ExamplesTest(unittest.TestCase):
    def test_run_sh_prints_the_expected_output(self) -> None:
        done = run([BASH, str(ROOT / "examples" / "run.sh")], env=env(bare=False))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        expected = (ROOT / "examples" / "expected-output.txt").read_text(encoding="utf-8")
        self.assertEqual(done.stdout, expected)

    def test_the_readme_preview_is_the_real_output(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        preview = readme.split("## Preview", 1)[1].split("```text\n", 1)[1].split("```", 1)[0]
        expected = (ROOT / "examples" / "expected-output.txt").read_text(encoding="utf-8")
        self.assertEqual(preview, expected, "paste examples/expected-output.txt into the README")


if __name__ == "__main__":
    unittest.main()
