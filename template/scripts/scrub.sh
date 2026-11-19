#!/usr/bin/env bash
# scrub.sh: check a folder before it goes public.
#
# Usage: scripts/scrub.sh [dir]        (default: the current folder)
#
# It looks for what must never be published:
#   - secrets: private keys, tokens and API keys, passwords in settings,
#     user:password inside a URL, and files such as .env or id_rsa
#   - e-mail addresses, phone numbers and WhatsApp chat ids
#   - IP addresses, Tailscale names and addresses, internal host names
#     (names ending in .local, .lan, .internal, .corp, .home.arpa)
#   - home folders of a user (a path under /home, /Users or C:\Users)
#   - every word of your deny-list (client names, machine names, people)
#   - a commit whose author or committer e-mail is not a noreply address
#
# Where it looks: the files that would be published (in a git repo: the
# tracked files plus the new ones that .gitignore does not hide), the file
# names, and, when the folder is the top of a git repo, every commit of the
# history, because a public repo publishes its whole history.
#
# The deny-list lives OUTSIDE the repo, because the names in it are exactly
# the ones that must not be published. Path: $PLAYBOOK_DENYLIST, default
# ~/.config/playbooks/denylist.txt. One name per line; lines that start with
# # are comments. A dash, underscore, dot or space inside an entry is
# optional, so a two-word entry also matches the words joined by a dash, an
# underscore or nothing. Case does not matter.
# When the file is missing, that check is skipped with a warning.
#
# gitleaks (https://github.com/gitleaks/gitleaks) runs too when it is
# installed: it knows many more token formats.
#
# A finding prints the file, line, column and rule, never the matched text,
# and a deny-list hit prints the entry number, never the word. So the output
# is safe to paste in a chat or to show in a public CI log.
#
# A line that must keep a match (a test fixture, a docs example) can carry the
# marker scrub:allow. The summary counts every finding it hides.
#
# Exit 0: clean. Exit 1: something was found. Exit 2: a usage or setup error.
#
# Copy this file as it is into every playbook repo (scripts/scrub.sh).
# Source: playbook-packaging by Ormus (Ormus Solutions), MIT license.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "scrub: python3 is required (3.8 or newer)" >&2
  exit 2
fi

exec python3 - "$@" <<'PY'
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

USAGE = "usage: scripts/scrub.sh [dir]"
ALLOW = "scrub:" + "allow"  # split so this line is not an allow marker itself
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
             ".mypy_cache", ".pytest_cache", ".ruff_cache"}
PICTURES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
            ".heic", ".pdf", ".mp4", ".mov", ".webm"}
MAX_BYTES = 5_000_000


def warn(text):
    print(f"scrub: warning: {text}", file=sys.stderr)


# ---- what an allowed value looks like -------------------------------------

def allowed_email(local, domain):
    """Addresses reserved for examples, git's own ssh user, and noreply
    addresses (they reach no person) are fine."""
    local, domain = local.lower(), domain.lower()
    if local in ("git", "noreply", "no-reply"):
        return True
    if domain in {"example.com", "example.org", "example.net"}:
        return True
    return domain.endswith((".example", ".test", ".invalid", ".localhost",
                            "noreply.github.com"))


def email_is_private(m):
    return not allowed_email(m.group("local"), m.group("domain"))


def ip_is_private(m):
    parts = [int(p) for p in m.groups()]
    if any(p > 255 for p in parts):
        return False
    a, b, c, _ = parts
    if a in (0, 127, 255):  # any, loopback, netmask
        return False
    # The three ranges RFC 5737 reserves for documentation.
    return (a, b, c) not in {(192, 0, 2), (198, 51, 100), (203, 0, 113)}


def phone_digits(m):
    return 8 <= sum(ch.isdigit() for ch in m.group(0)) <= 15


def letters_and_digits(m):
    value = m.group("v")
    return any(ch.isdigit() for ch in value) and any(ch.isalpha() for ch in value)


# ---- the rules: (name, pattern, extra check or None) ----------------------
# The first rule that matches at a position wins, so the specific ones come
# before the general ones.

OCTET = r"(\d{1,3})"
RULES = [
    ("private-key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY"), None),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), None),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"), None),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), None),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), None),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), None),
    ("stripe-key", re.compile(r"\b[rsp]k_(?:live|test)_[0-9A-Za-z]{16,}"), None),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), None),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}"), None),
    ("url-credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@'\"]+:(?![$<{])[^\s/@'\"]+@"), None),
    ("secret-assignment", re.compile(
        r"(?i)\b[\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|passphrase|access[_-]?key)[\w-]*"
        r"['\"]?\s*[:=]\s*['\"]?(?P<v>[A-Za-z0-9+/_=-]{20,})"), letters_and_digits),
    ("whatsapp-id", re.compile(
        r"\b\d{5,20}(?:-\d{5,20})?@(?:g\.us|c\.us|s\.whatsapp\.net|lid|newsletter)\b"), None),
    ("email", re.compile(
        r"(?<![\w.+-])(?P<local>[A-Za-z0-9._%+-]+)@(?P<domain>[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b"),
        email_is_private),
    ("phone", re.compile(r"(?<![\w+])\+\d[\d ().-]{6,22}\d(?!\w)"), phone_digits),
    ("phone", re.compile(r"(?<![\w.-])\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w-])"), None),
    ("tailscale-name", re.compile(r"(?<![\w-])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.ts\.net\b"), None),
    ("tailscale-ip", re.compile(
        r"(?<![\w.])100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}(?!\.?\d)(?!\w)"), None),
    ("tailscale-ip", re.compile(r"(?i)\bfd7a:115c:a1e0:"), None),
    ("ip-address", re.compile(
        r"(?<![\w.])" + OCTET + r"\." + OCTET + r"\." + OCTET + r"\." + OCTET + r"(?!\.?\d)(?!\w)"),
        ip_is_private),
    ("internal-host", re.compile(
        r"(?<![\w.-])(?:[A-Za-z0-9-]+\.)+(?:local|lan|internal|intranet|corp|localdomain|home\.arpa)(?![\w.(-])"),
        None),
    ("home-path", re.compile(
        r"(?<![\w.~-])(?:/home/|/Users/)(?![$<{*])[A-Za-z0-9._-]+"
        r"|(?<!\w)[A-Za-z]:\\Users\\(?![$<{%*])[A-Za-z0-9._-]+"), None),
]

SECRET_FILE = re.compile(
    r"^(?:\.env(?:\..+)?|id_(?:rsa|dsa|ecdsa|ed25519)|.+\.(?:pem|p12|pfx|key|jks|keystore)|\.netrc|\.pypirc)$")
SECRET_FILE_OK = re.compile(r"^\.env\.(?:example|sample|template)$")


# ---- the deny-list --------------------------------------------------------

def load_denylist(root):
    raw = os.environ.get("PLAYBOOK_DENYLIST") or "~/.config/playbooks/denylist.txt"
    path = Path(raw).expanduser()
    if not path.is_file():
        warn("no deny-list, so client and private names were NOT checked. "
             "Create ~/.config/playbooks/denylist.txt (one name per line) "
             "or set PLAYBOOK_DENYLIST.")
        return []
    resolved = path.resolve()
    if resolved == root or root in resolved.parents:
        print("scrub: the deny-list is inside the folder you scan; move it out "
              "(it holds the names that must not be published)", file=sys.stderr)
        sys.exit(2)
    entries = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), 1):
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        parts = [re.escape(p) for p in re.split(r"[-_\s.]+", word) if p]
        if not parts:
            continue
        joined = r"[-_\s.]?".join(parts)
        pattern = re.compile(r"(?<![A-Za-z0-9])" + joined + r"(?![A-Za-z0-9])", re.I)
        entries.append((number, pattern))
    return entries


# ---- scanning -------------------------------------------------------------

def scan_text(line, denylist):
    """Return [(column, rule)] for one line, first rule wins per column."""
    hits = {}
    for name, pattern, check in RULES:
        for m in pattern.finditer(line):
            if check is None or check(m):
                hits.setdefault(m.start() + 1, name)
    for number, pattern in denylist:
        for m in pattern.finditer(line):
            hits.setdefault(m.start() + 1, f"deny-list entry {number}")
    return sorted(hits.items())


def mask(text, denylist):
    """Hide deny-listed words in a path before it is printed."""
    for _, pattern in denylist:
        text = pattern.sub("***", text)
    return text


def git(root, *args):
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, errors="replace", stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return None
    return done.stdout if done.returncode == 0 else None


def walk(root, start):
    names = []
    for folder, dirs, files in os.walk(start):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in files:
            names.append((Path(folder) / f).relative_to(root).as_posix())
    return names


def list_files(root):
    """The files that would be published, as paths relative to root.

    In a git repo: the tracked files and the new ones .gitignore does not
    hide. A folder git lists as a whole (a repo inside the repo) is walked.
    When git lists nothing (a folder that git ignores), every file is read,
    so an empty list never passes for a clean result.
    """
    names = []
    if (git(root, "rev-parse", "--is-inside-work-tree") or "").strip() == "true":
        out = git(root, "ls-files", "-z", "-co", "--exclude-standard") or ""
        for name in sorted({n for n in out.split("\0") if n}):
            if name.endswith("/"):
                names += walk(root, root / name)
            elif (root / name).exists() or (root / name).is_symlink():
                names.append(name)
    if not names:
        names = walk(root, root)
    return sorted(set(names))


def scan_files(root, names, denylist, findings, counts):
    for rel in names:
        path = root / rel
        shown = mask(rel, denylist)
        base = rel.rsplit("/", 1)[-1]
        if SECRET_FILE.match(base) and not SECRET_FILE_OK.match(base):
            findings.append(f"{shown}: secret-file (do not publish this file)")
        for col, rule in scan_text(rel, denylist):
            if rule.startswith("deny-list"):
                findings.append(f"{shown}: {rule} (in the path)")
        if path.is_symlink():
            for col, rule in scan_text(os.readlink(path), denylist):
                findings.append(f"{shown}: {rule} (in the link target)")
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in PICTURES:
            counts["pictures"] += 1
            continue
        if path.stat().st_size > MAX_BYTES:
            warn(f"{shown}: bigger than {MAX_BYTES // 1_000_000} MB, not read")
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            counts["binary"] += 1
            continue
        counts["files"] += 1
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            hits = scan_text(line, denylist)
            if hits and ALLOW in line:
                counts["allowed"] += len(hits)
                continue
            for col, rule in hits:
                findings.append(f"{shown}:{number}:{col}: {rule}")


def scan_history(root, denylist, findings, counts):
    log = git(root, "log", "--all", "-p", "--no-color", "--no-ext-diff",
              "--format=%x00%h%n%B")
    if log is None:
        return
    seen = set()
    sha, in_message = "", False
    for line in log.splitlines():
        if line.startswith("\0"):
            sha, in_message = line[1:], True
            counts["commits"] += 1
            continue
        if line.startswith("diff --git "):
            in_message = False
            hits = [(c, r) for c, r in scan_text(line, denylist) if r.startswith("deny-list")]
        elif in_message:
            hits = scan_text(line, denylist)
        elif line.startswith("+") and not line.startswith("+++"):
            hits = scan_text(line[1:], denylist)
        else:
            continue
        if hits and ALLOW in line:
            continue
        for _, rule in hits:
            if (sha, rule) not in seen:
                seen.add((sha, rule))
                findings.append(f"history {sha}: {rule}")
    authors = git(root, "log", "--all", "--format=%ae %ce") or ""
    personal = 0
    for line in authors.splitlines():
        for address in line.split():
            local, _, domain = address.partition("@")
            if domain and not allowed_email(local, domain):
                personal += 1
                break
    if personal:
        # A finding, not a warning: a public repo shows this address on every
        # commit, so the gate must stop before it is published.
        what = "1 commit carries" if personal == 1 else f"{personal} commits carry"
        findings.append(f"history: {what} an author or committer e-mail that is "
                        "not a noreply address (a public repo shows it on every "
                        "commit). Set a noreply address (GitHub: Settings, Emails) "
                        "with git config user.email, then rewrite the history: "
                        "git rebase -r --root --exec 'git commit --amend --no-edit "
                        "--reset-author'")


def run_gitleaks(root, names, with_history):
    """Run gitleaks on a copy of exactly the files that would be published."""
    exe = shutil.which("gitleaks")
    if exe is None:
        warn("gitleaks is not installed, so its checks were skipped "
             "(https://github.com/gitleaks/gitleaks)")
        return 0
    new_style = subprocess.run([exe, "dir", "--help"], capture_output=True,
                               stdin=subprocess.DEVNULL).returncode == 0
    flags = ["--no-banner", "--redact", "--log-level", "warn"]
    found = 0
    with tempfile.TemporaryDirectory() as tmp:
        for rel in names:
            src = root / rel
            if src.is_file() and not src.is_symlink():
                dst = Path(tmp) / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        cmd = [exe, "dir", *flags, tmp] if new_style else \
              [exe, "detect", "--no-git", "--source", tmp, *flags]
        if subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode != 0:
            print("scrub: gitleaks found something in the files; see it with: "
                  "gitleaks dir -v --redact .", file=sys.stderr)
            found = 1
    if with_history:
        cmd = [exe, "git", *flags, str(root)] if new_style else \
              [exe, "detect", "--source", str(root), *flags]
        if subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode != 0:
            print("scrub: gitleaks found something in the git history; see it "
                  "with: gitleaks git -v --redact .", file=sys.stderr)
            found = 1
    return found


def main(argv):
    if len(argv) > 1 or (argv and argv[0] in ("-h", "--help")):
        print(USAGE, file=sys.stderr)
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    root = Path(argv[0] if argv else ".")
    if not root.is_dir():
        print(f"scrub: not a folder: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    denylist = load_denylist(root)
    names = list_files(root)
    findings = []
    counts = {"files": 0, "binary": 0, "pictures": 0, "allowed": 0, "commits": 0}
    scan_files(root, names, denylist, findings, counts)

    top = (git(root, "rev-parse", "--show-toplevel") or "").strip()
    with_history = bool(top) and Path(top).resolve() == root \
        and git(root, "rev-parse", "--verify", "-q", "HEAD") is not None
    if with_history:
        scan_history(root, denylist, findings, counts)

    for line in findings:
        print(line)
    if counts["pictures"]:
        warn(f"{counts['pictures']} pictures, PDFs or videos were not read: look at "
             "each one yourself (a screenshot can show client data)")
    if counts["allowed"]:
        print(f"scrub: {counts['allowed']} findings hidden by {ALLOW} markers")
    sys.stdout.flush()  # our lines first, then what gitleaks prints
    leaks = run_gitleaks(root, names, with_history)

    commits = counts["commits"]
    history = (f"{commits} commit{'' if commits == 1 else 's'}" if with_history
               else "not checked")
    summary = (f"{counts['files']} text files, deny-list: {len(denylist)} entries, "
               f"history: {history}")
    if findings or leaks:
        print(f"scrub: FAILED, {len(findings)} findings ({summary})")
        print("scrub: fix each one, or move the data out of the repo. A finding in "
              "history stays public after you delete the line: start a fresh "
              "history. A key that was ever pushed must be rotated.")
        return 1
    print(f"scrub: clean ({summary})")
    return 0


sys.exit(main(sys.argv[1:]))
PY
