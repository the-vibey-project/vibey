#!/usr/bin/env bash
# scripts/fleet/run.sh REPO PHASE [DRIVER]
#
# Launch one dogfooded fleet-program run: a fresh disposable worktree off
# origin/develop, driven by one of the *loop runners against a phase plan
# file under docs/plans/fleet/<PHASE>-<REPO>.md.
#
# See docs/plans/fleet-program-runbook.md for the program this feeds and
# docs/plans/fleet/README.md for the mechanics this script implements.
set -euo pipefail

REPO="${1:?usage: run.sh REPO PHASE [DRIVER]}"
PHASE="${2:?usage: run.sh REPO PHASE [DRIVER]}"
DRIVER="${3:-claudeloop}"

case "$REPO" in
  vibey|claudeloop|codexloop) ;;
  *) echo "unknown repo: $REPO (expected vibey|claudeloop|codexloop)" >&2; exit 1 ;;
esac
case "$DRIVER" in
  claudeloop|codexloop) ;;
  *) echo "unknown driver: $DRIVER" >&2; exit 1 ;;
esac
if ! command -v "$DRIVER" >/dev/null 2>&1; then
  echo "driver '$DRIVER' is not on PATH — every runner ships in the one vibey distribution now (ADR-0037): \`uv tool install vibey-engine\`, or \`uv tool install --editable \"$VIBEY_ROOT\"\` from this checkout" >&2
  exit 1
fi

VIBEY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLAN_FILE="$VIBEY_ROOT/docs/plans/fleet/${PHASE}-${REPO}.md"
if [ ! -f "$PLAN_FILE" ]; then
  echo "no plan file at $PLAN_FILE" >&2
  exit 1
fi

REPO_ROOT="$HOME/git/$REPO"
WT="$HOME/.cache/fleet-worktrees/${REPO}-${PHASE}"
RUN_ID="${REPO}-${PHASE}"
BRANCH="chore/${PHASE}"

echo "== $RUN_ID via $DRIVER =="

cd "$REPO_ROOT"
git fetch -q origin

if [ -d "$WT" ]; then
  echo "worktree already exists at $WT — reusing (resume, not fresh start)" >&2
else
  mkdir -p "$(dirname "$WT")"
  git worktree add -B "$BRANCH" "$WT" origin/develop
fi

# Protected paths (tests/infrastructure/db/test_chaos.py, the no-loss
# property suite, tests/system/test_delivery_stage_set.py, tests/live/**)
# are called out in each plan file directly and enforced again by land.sh's
# refusal check — no driver here supports an appended system prompt, so
# there is no out-of-band note to inject at launch time.

LOG_DIR="$WT/.$DRIVER"
mkdir -p "$LOG_DIR"

case "$DRIVER" in
  claudeloop)
    # Deliberately not passing --permission-mode: claudeloop's own default
    # is bypassPermissions (required for real autonomy — see
    # infrastructure/agent/options.py's docstring), and it's safe here
    # because worktree isolation + the repo's own scope guard are the
    # actual safety boundary, not per-command approval. Overriding it to
    # acceptEdits (an earlier version of this script did) leaves Bash
    # commands unapproved, so any run that needs to execute its own gate
    # sweep (ruff/mypy/pytest) blocks immediately with "User approval
    # needed" and reports failure having done nothing.
    exec claudeloop run "$PLAN_FILE" \
      --cwd "$WT" \
      --run-id "$RUN_ID" \
      --add-folder "$VIBEY_ROOT/docs/plans" \
      --max-turns 800 --max-dollars 80 --max-wait 21600 \
      --done-marker CLAUDELOOP_TASK_FULLY_COMPLETE \
      --log-level INFO --log-file "$LOG_DIR/run.log" \
      --stream-ui
    ;;
  codexloop)
    # NOTE: codexloop's `run` has no --cwd today (Phase C tracks adding it).
    # Until then, correctness depends on actually being in $WT — cd there
    # explicitly rather than relying on a flag that doesn't exist yet.
    cd "$WT"
    exec codexloop run "$PLAN_FILE" \
      --run-id "$RUN_ID" \
      --max-turns 800 --max-wait 21600 \
      --log-level INFO --log-file "$LOG_DIR/run.log" \
      --stream-ui
    ;;
esac
