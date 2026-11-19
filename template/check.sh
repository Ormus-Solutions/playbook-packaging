#!/usr/bin/env bash
# check.sh: the one gate for this playbook. Run it before every commit and
# before you publish. It stops at the first failure and exits non-zero.
#   1. the tests in tests/ (offline, on the synthetic data)
#   2. placeholders from the template that are not filled yet
#   3. the scrub: secrets, e-mails, phones, IPs, host names, home paths and
#      your deny-list (see scripts/scrub.sh), plus gitleaks when installed
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "check: needs Python 3.11 or newer (python3 --version)" >&2
  exit 1
fi

echo "== tests"
python3 -m unittest discover -s tests

echo "== placeholders"
# The markers are split in two so this file does not match itself.
if grep -rnF --exclude-dir=.git -e '<''FILL:' -e '{{''slug}}' -e '{{''title}}' \
     -e '{{''year}}' -e '{{''date}}' . ; then
  echo "check: fill the placeholders above, then run again" >&2
  exit 1
fi
echo "none left"

echo "== scrub"
bash scripts/scrub.sh .

echo "check: ok"
