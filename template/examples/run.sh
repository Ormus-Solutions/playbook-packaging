#!/usr/bin/env bash
# run.sh: see the tool work on the synthetic data in examples/, with no setup.
# The output must match examples/expected-output.txt (a test checks it).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 src/tool.py --demo
