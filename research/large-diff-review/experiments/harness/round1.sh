#!/bin/sh
# Stage 2 round 1, in the order LOG.md fixed before any Stage 2 outcome.
cd "$(dirname "$0")/.." || exit 1
while pgrep -f "harness/stage1.py" >/dev/null; do sleep 60; done
PYTHONPATH=harness python3 harness/contention.py audit --write >> results/contention.log 2>&1
exec ./harness/go.sh stage2 round1 \
  D16-T1-BF8192 D32-T1-BF8192 D16-BF4096 A2 A1 \
  D16-T1-BF8192+FF D16-T1-BF8192+VER D16-T1-BF8192+SA D16-T1-BF8192+CTXnone \
  D16-T1-BF8192+CTXfile D16-T1-BF8192+TRI D16-T1-high-BF8192 D16-T1-BF4096 D16-T1-BF12288 \
  D16-T1-low-BF8192 D16-TD@qwen3:14b D16-TD@qwen2.5-coder:14b
