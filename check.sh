#!/usr/bin/env bash
# check.sh: the one gate for this repo. Run it before every commit. It stops
# at the first failure and exits non-zero.
#   1. the tests in tests/ (offline, on synthetic data in temp folders)
#   2. shellcheck on every shell script, when shellcheck is installed
#   3. the lint: this repo follows its own standard
#   4. the scrub on this repo, with your deny-list, plus gitleaks when installed
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "check: needs Python 3.11 or newer (python3 --version)" >&2
  exit 1
fi

echo "== tests"
python3 -m unittest discover -s tests

echo "== shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck check.sh scripts/*.sh examples/run.sh template/check.sh \
    template/scripts/*.sh template/examples/run.sh
  echo "ok"
else
  echo "shellcheck is not installed; skipped"
fi

echo "== lint"
python3 src/playbook_lint.py .

echo "== scrub"
bash scripts/scrub.sh .

echo "check: ok"
