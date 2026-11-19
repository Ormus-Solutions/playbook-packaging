"""Tests for scripts/scrub.sh with planted fake secrets in temp folders.

Every fake value is built from parts at run time, so this file itself holds
no secret, e-mail, phone number or address for the scrub (or gitleaks) to find.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from support import BASH, SCRUB, env, git, run, scrub

AT = "@"
ALLOW = "scrub:" + "allow"

# rule -> a line that holds one fake example of it
PLANTED = {
    "private-key": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    "aws-key": "aws_key " + "AKIA" + "QWERTYUIOPASDFGH",
    "github-token": "token " + "ghp" + "_" + "a1B2" * 9,
    "slack-token": "xox" + "b-" + "1234567890-abcdefghij",
    "api-key": "key " + "sk" + "-ant-" + "abcDEF123456ghiJKL789",
    "google-key": "key " + "AI" + "za" + "Sy" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7",
    "stripe-key": "sk" + "_live_" + "a1b2c3d4e5f6g7h8i9j0",
    "jwt": "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + ".abcdefghij12",
    "bearer-token": "Authorization: Bear" + "er " + "abc123def456ghi789jkl012",
    "url-credentials": "postgres" + "://admin:" + "hunter2x" + AT + "db/app",
    "secret-assignment": "CLIENT_SEC" + "RET=" + "abc123def456ghi789jkl0",
    "whatsapp-id": "group " + "1203630000" + "00000001" + AT + "g.us",
    "email": "write to jane.doe" + AT + "acme-mail.io",
    "phone": "call +1 555 " + "0100 199",
    "tailscale-name": "ssh box.tail1234" + ".ts" + ".net",
    "tailscale-ip": "at 100.101" + ".2.3",
    "ip-address": "server 10.1" + ".2.3",
    "internal-host": "nas.home" + ".arpa",
    "home-path": "see /home" + "/jane/notes",
}

# Lines that look close to a finding but are fine to publish.
CLEAN = [
    "write to jane" + AT + "example.com or git" + AT + "github.com:owner/repo.git",
    "Co-Authored-By: a bot <noreply" + AT + "bot-maker.io>",
    "loopback 127.0.0.1, docs range 192.0.2.10, netmask 255.255.255.0",
    "a version is not an address: 1.2.3.4.5, and 3.11 is not either",
    "a date is not a phone: 2026-11-19",
    "placeholders are fine: /home/$USER/notes, /home/<you>/notes, ~/notes",
    "code is fine: state = threading.local()",
    "a token by name only: TOKEN=${TOKEN}",
]


class Folder:
    """A temp folder that deletes itself."""

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix="scrub-test-"))
        return self.path

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


class RulesTest(unittest.TestCase):
    def test_every_planted_kind_is_found_by_its_rule(self) -> None:
        with Folder() as folder:
            for rule, line in PLANTED.items():
                (folder / f"{rule}.txt").write_text(line + "\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        for rule in PLANTED:
            with self.subTest(rule=rule):
                self.assertRegex(done.stdout, rf"(?m)^{rule}\.txt:1:\d+: {rule}$")
        self.assertIn("scrub: FAILED", done.stdout)

    def test_the_output_never_shows_the_matched_text(self) -> None:
        with Folder() as folder:
            for rule, line in PLANTED.items():
                (folder / f"{rule}.txt").write_text(line + "\n", encoding="utf-8")
            done = scrub(folder)
        output = done.stdout + done.stderr
        for line in PLANTED.values():
            value = line.split()[-1]
            with self.subTest(value=value[:6]):
                self.assertNotIn(value, output)

    def test_lookalikes_are_clean(self) -> None:
        with Folder() as folder:
            (folder / "notes.md").write_text("\n".join(CLEAN) + "\n", encoding="utf-8")
            (folder / ".env.example").write_text("TOKEN=\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("scrub: clean", done.stdout)

    def test_secret_files_are_found_by_name(self) -> None:
        with Folder() as folder:
            for name in (".env", ".env.local", "id_rsa", "server.pem"):
                (folder / name).write_text("x\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 1)
        for name in (".env", ".env.local", "id_rsa", "server.pem"):
            self.assertIn(f"{name}: secret-file", done.stdout)

    def test_the_allow_marker_hides_a_finding_and_is_counted(self) -> None:
        with Folder() as folder:
            (folder / "fixture.txt").write_text(PLANTED["email"] + "  # " + ALLOW + "\n",
                                                encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("1 findings hidden", done.stdout)

    def test_pictures_are_not_read_but_named_in_a_warning(self) -> None:
        with Folder() as folder:
            (folder / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 16)
            done = scrub(folder)
        self.assertEqual(done.returncode, 0)
        self.assertIn("1 pictures, PDFs or videos were not read", done.stderr)


class DenylistTest(unittest.TestCase):
    def write_denylist(self, folder: Path) -> Path:
        path = folder / "denylist.txt"
        path.write_text("# my clients\nglobex corp\ninitech\n", encoding="utf-8")
        return path

    def test_a_hit_prints_the_entry_number_never_the_word(self) -> None:
        with Folder() as outside, Folder() as folder:
            denylist = self.write_denylist(outside)
            (folder / "notes.md").write_text("Call with Globex-Corp today\n", encoding="utf-8")
            done = scrub(folder, denylist)
        self.assertEqual(done.returncode, 1)
        self.assertIn("notes.md:1:11: deny-list entry 2", done.stdout)
        self.assertNotIn("globex", (done.stdout + done.stderr).lower())

    def test_joined_forms_match_and_longer_words_do_not(self) -> None:
        with Folder() as outside, Folder() as folder:
            denylist = self.write_denylist(outside)
            (folder / "a.md").write_text("globexcorp\nGLOBEX_CORP\nGlobex Corp\n", encoding="utf-8")
            (folder / "b.md").write_text("globexcorporation and initechs\n", encoding="utf-8")
            done = scrub(folder, denylist)
        for line in (1, 2, 3):
            self.assertIn(f"a.md:{line}:1: deny-list entry 2", done.stdout)
        self.assertNotIn("b.md", done.stdout)

    def test_a_file_name_is_checked_and_masked(self) -> None:
        with Folder() as outside, Folder() as folder:
            denylist = self.write_denylist(outside)
            (folder / "initech-notes.md").write_text("nothing here\n", encoding="utf-8")
            done = scrub(folder, denylist)
        self.assertEqual(done.returncode, 1)
        self.assertIn("***-notes.md: deny-list entry 3 (in the path)", done.stdout)
        self.assertNotIn("initech", done.stdout.lower())

    def test_a_missing_denylist_is_skipped_with_a_warning(self) -> None:
        with Folder() as folder:
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 0)
        self.assertIn("no deny-list", done.stderr)
        self.assertIn("deny-list: 0 entries", done.stdout)

    def test_a_denylist_inside_the_scanned_folder_is_refused(self) -> None:
        with Folder() as folder:
            denylist = self.write_denylist(folder)
            done = scrub(folder, denylist)
        self.assertEqual(done.returncode, 2)
        self.assertIn("inside the folder you scan", done.stderr)


class GitTest(unittest.TestCase):
    def test_only_files_that_would_be_published_are_read(self) -> None:
        with Folder() as folder:
            git(folder, "init", "-q")
            (folder / ".gitignore").write_text("local.txt\n", encoding="utf-8")
            (folder / "local.txt").write_text(PLANTED["aws-key"] + "\n", encoding="utf-8")
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_a_repo_inside_the_repo_is_read(self) -> None:
        with Folder() as folder:
            git(folder, "init", "-q")
            inner = folder / "vendor" / "tool"
            inner.mkdir(parents=True)
            git(inner, "init", "-q")
            (inner / "app.cfg").write_text(PLANTED["aws-key"] + "\n", encoding="utf-8")
            done = scrub(folder)
        self.assertEqual(done.returncode, 1)
        self.assertIn("vendor/tool/app.cfg:1:9: aws-key", done.stdout)

    def test_a_folder_that_git_ignores_is_still_read(self) -> None:
        with Folder() as folder:
            git(folder, "init", "-q")
            (folder / ".gitignore").write_text("private/\n", encoding="utf-8")
            (folder / "private").mkdir()
            (folder / "private" / "notes.md").write_text(PLANTED["email"] + "\n", encoding="utf-8")
            done = scrub(folder / "private")
        self.assertEqual(done.returncode, 1)
        self.assertIn("notes.md:1:10: email", done.stdout)

    def test_a_secret_removed_later_is_still_found_in_history(self) -> None:
        with Folder() as folder:
            git(folder, "init", "-q")
            (folder / "app.cfg").write_text(PLANTED["aws-key"] + "\n", encoding="utf-8")
            git(folder, "add", ".")
            git(folder, "commit", "-q", "-m", "add config")
            (folder / "app.cfg").write_text("key from the environment\n", encoding="utf-8")
            git(folder, "commit", "-q", "-am", "remove the key")
            done = scrub(folder)
        self.assertEqual(done.returncode, 1)
        self.assertRegex(done.stdout, r"(?m)^history [0-9a-f]+: aws-key$")
        self.assertNotRegex(done.stdout, r"(?m)^app\.cfg")
        self.assertIn("history: 2 commits", done.stdout)

    def test_commit_messages_are_checked(self) -> None:
        with Folder() as outside, Folder() as folder:
            denylist = outside / "denylist.txt"
            denylist.write_text("initech\n", encoding="utf-8")
            git(folder, "init", "-q")
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            git(folder, "add", ".")
            git(folder, "commit", "-q", "-m", "fix the Initech report")
            done = scrub(folder, denylist)
        self.assertEqual(done.returncode, 1)
        self.assertRegex(done.stdout, r"(?m)^history [0-9a-f]+: deny-list entry 1$")

    def test_a_personal_author_email_is_a_warning(self) -> None:
        with Folder() as folder:
            git(folder, "init", "-q")
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            git(folder, "add", ".")
            git(folder, "-c", "user.email=dev" + AT + "acme-mail.io", "commit", "-q", "-m", "first")
            done = scrub(folder)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("1 commit carries an author or committer e-mail", done.stderr)
        self.assertNotIn("acme-mail", done.stdout + done.stderr)


class GitleaksTest(unittest.TestCase):
    def test_without_gitleaks_the_skip_is_named(self) -> None:
        with Folder() as folder:
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            done = scrub(folder)
        self.assertIn("gitleaks is not installed", done.stderr)

    @unittest.skipUnless(shutil.which("gitleaks"), "gitleaks is not installed")
    def test_gitleaks_runs_when_it_is_installed(self) -> None:
        with Folder() as folder:
            (folder / "app.cfg").write_text(PLANTED["aws-key"] + "\n", encoding="utf-8")
            done = scrub(folder, bare=False)
        self.assertEqual(done.returncode, 1)
        self.assertIn("gitleaks found something in the files", done.stderr)


class UsageTest(unittest.TestCase):
    def test_a_missing_folder_is_a_usage_error(self) -> None:
        done = scrub(Path("/nonexistent/folder"))
        self.assertEqual(done.returncode, 2)

    def test_two_folders_are_a_usage_error(self) -> None:
        done = run([BASH, str(SCRUB), ".", "."], env=env())
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage:", done.stderr)


if __name__ == "__main__":
    unittest.main()
