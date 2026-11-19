#!/usr/bin/env bash
# run.sh: watch the whole packaging process work on synthetic data, with no setup.
#
#   1. new.sh makes a playbook repo from the template in a temp folder
#   2. the lint fails on it: the placeholders are still there
#   3. the finished example docs from examples/lane-counts/ are copied in
#   4. the lint passes
#   5. the new repo's own check.sh passes (tests, placeholders, scrub)
#
# It writes only to a temp folder, which it deletes at the end. The scrub in
# step 5 uses examples/denylist.example.txt, so your real deny-list is not read.
# The output must match examples/expected-output.txt (a test checks it).
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
repo="$work/playbook-lane-counts"

echo "== 1. scripts/new.sh lane-counts playbook-lane-counts"
bash "$here/scripts/new.sh" lane-counts "$repo" >/dev/null
echo "created: $(cd "$repo" && find . -mindepth 1 -maxdepth 1 | sed 's|^\./||' | LC_ALL=C sort | paste -sd ' ' -)"

echo "== 2. lint the fresh copy (it fails: placeholders are left)"
python3 "$here/src/playbook_lint.py" "$repo" || true

echo "== 3. copy in the finished docs from examples/lane-counts/"
cp "$here/examples/lane-counts/README.md" "$here/examples/lane-counts/PLAYBOOK.md" \
   "$here/examples/lane-counts/LICENSE" "$repo/"

echo "== 4. lint again"
python3 "$here/src/playbook_lint.py" "$repo"

echo "== 5. the new repo's own gate"
if PLAYBOOK_DENYLIST="$here/examples/denylist.example.txt" bash "$repo/check.sh" >"$work/check.log" 2>&1; then
  tail -n 1 "$work/check.log"
else
  cat "$work/check.log"
  exit 1
fi
