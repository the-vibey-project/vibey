#!/bin/sh
# Runs a harness script under the study's environment, appending to results/<name>.log.
cd "$(dirname "$0")/.." || exit 1
name=$1; shift
PYTHONUNBUFFERED=1 PYTHONPATH="$(cd ../../.. && pwd)/src/vibey_tools/gh:harness" \
  exec python3 "harness/$name.py" "$@" >> "results/$name.log" 2>&1
