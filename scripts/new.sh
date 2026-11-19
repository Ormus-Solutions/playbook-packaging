#!/usr/bin/env bash
# new.sh: start a new playbook repo from the template.
#
# Usage: scripts/new.sh <slug> <dest>
#   slug  lowercase words joined by dashes, for example lane-counts.
#         The repo is named playbook-<slug>. A slug that already starts
#         with "playbook-" is taken as it is.
#   dest  a folder that does not exist yet, or an empty one.
#
# It copies template/ to <dest>, fills {{slug}}, {{title}}, {{year}} and
# {{date}}, and runs git init with main as the default branch. It writes
# nothing outside <dest> and makes no commit: the first commit is yours.
# The <FILL: ...> placeholders are left for you; ./check.sh lists them.
set -euo pipefail

usage() {
  echo "usage: scripts/new.sh <slug> <dest>" >&2
  exit 2
}

[ "$#" -eq 2 ] || usage
slug=${1#playbook-}
dest=$2

if ! [[ "$slug" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "new.sh: the slug must be lowercase letters and digits joined by single dashes, got: $1" >&2
  exit 2
fi
if [ -e "$dest" ] && { [ ! -d "$dest" ] || [ -n "$(ls -A "$dest")" ]; }; then
  echo "new.sh: $dest already exists and is not an empty folder; pick a new one" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "new.sh: python3 is required" >&2
  exit 2
fi

template="$(cd "$(dirname "$0")/.." && pwd)/template"
words=${slug//-/ }
title="$(printf '%s' "${words:0:1}" | tr '[:lower:]' '[:upper:]')${words:1}"

mkdir -p "$dest"
cp -R "$template/." "$dest/"
find "$dest" -name __pycache__ -type d -prune -exec rm -rf {} +

# Fill the four placeholders in every text file. Python keeps each file's
# mode, so check.sh stays executable.
python3 - "$dest" "$slug" "$title" "$(date +%Y)" "$(date +%Y-%m-%d)" <<'PY'
import sys
from pathlib import Path

dest, slug, title, year, date = sys.argv[1:]
values = {"slug": slug, "title": title, "year": year, "date": date}
for path in sorted(Path(dest).rglob("*")):
    if not path.is_file() or ".git" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    new = text
    for key, value in values.items():
        new = new.replace("{{" + key + "}}", value)
    if new != text:
        path.write_text(new, encoding="utf-8")
PY

chmod +x "$dest/check.sh" "$dest/scripts/scrub.sh" "$dest/examples/run.sh"

if command -v git >/dev/null 2>&1; then
  git init -q "$dest"
  git -C "$dest" symbolic-ref HEAD refs/heads/main
else
  echo "new.sh: git is not installed, so the folder is not a repo yet" >&2
fi

cat <<EOF
Created playbook-$slug in $dest
Next:
  1. cd $dest && ./check.sh      (the tests pass; it lists the placeholders to fill)
  2. replace src/, examples/ and tests/ with your own tool, on synthetic data
  3. fill README.md, PLAYBOOK.md and LICENSE until ./check.sh prints "check: ok"
EOF
