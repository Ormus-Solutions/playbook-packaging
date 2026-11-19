"""Shared helpers for the tests: paths, and running the scripts in a clean setting."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRUB = ROOT / "scripts" / "scrub.sh"
NEW = ROOT / "scripts" / "new.sh"
LINT = ROOT / "src" / "playbook_lint.py"
BASH = shutil.which("bash") or "/bin/bash"
NO_DENYLIST = "/nonexistent/denylist.txt"


def bare_path() -> str:
    """A PATH with only python3 and git, so gitleaks is never found.

    This keeps the scrub tests the same on every machine, whether gitleaks
    is installed or not.
    """
    folder = Path(tempfile.mkdtemp(prefix="scrub-bin-"))
    for tool in ("python3", "git"):
        found = shutil.which(tool)
        if found:
            (folder / tool).symlink_to(found)
    return str(folder)


BARE_PATH = bare_path()


def env(denylist: str | Path = NO_DENYLIST, bare: bool = True) -> dict[str, str]:
    values = dict(os.environ)
    values["PLAYBOOK_DENYLIST"] = str(denylist)
    if bare:
        values["PATH"] = BARE_PATH
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        values.pop(key, None)
    return values


def run(cmd: list[str], cwd: Path | None = None, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, **kwargs)


def scrub(folder: Path, denylist: str | Path = NO_DENYLIST, bare: bool = True):
    return run([BASH, str(SCRUB), str(folder)], env=env(denylist, bare))


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(folder), "-c", "user.name=Test",
                    "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
                    "-c", "core.hooksPath=/dev/null",
                    *args], check=True, capture_output=True, env=env(bare=False))
