#!/bin/bash
# storm-queue.sh -- run QwenStorm lanes, as many at once as this device measured (8.c, 8.j).
#
# HOW MANY AT ONCE is `[local_models] concurrent_runs` in .vibey-gh.toml, asked of vibey-gh
# (`vibey-gh slots allowed`), which checks it against THIS device's own calibration evidence
# (ADR-0057) -- never a literal here. The declared default is 1, 8.c as written. No evidence,
# evidence for a device this no longer is, or a vibey-gh that cannot answer, all mean one: said
# in progress.log with the reason, and `slots allowed` records a calibration request that the
# queue runs itself, under the model lock, the next time the storm is idle.
#
# queue.txt lines: "<slug> <issue> [dep1,dep2,...]". Every lane starts from the integration
# branch (verified work only), so:
#   * a lane starts only when every dependency is in integrated.txt;
#   * no lane starts while a finished lane awaits review (has result.json but is in neither
#     integrated.txt nor abandoned.txt) -- integration keeps pace with the storm, so each lane
#     builds on everything verified before it and history stays linear;
#   * a lane whose dependency was abandoned is marked blocked, for the reviewer to settle.
# UNATTENDED mode (the file $Q/UNATTENDED exists; the operator's choice of 2026-09-22): a finished
# lane no longer holds the storm. Every lane whose dependencies are integrated runs, and finished
# lanes wait for a batch review; integrating a batch unlocks the lanes that depend on it.
# The queue is re-read on every pass, so lanes can be appended or reordered while this runs.
# PRIORITY (ADR-0054): `tools/storm-priority.py push|bump|unbump` puts a lane at the front,
# first pushed first, with its unintegrated dependencies pulled forward ahead of it. It runs
# next after the lane running now -- never instead of it -- and admission below still judges
# its issue. Only the operator or a source declared in storm.toml [priority] sources may.
# Declared in storm.toml, derived from the tree when it is silent -- never a literal here
# (12.h). A shell script cannot read TOML, so it asks the one resolver the Python tools use
# rather than keeping a second copy that agrees until the day it does not.
Q="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(python3 "$Q/tools/storm_paths.py" python)"
SLUG="$(python3 "$Q/tools/storm_paths.py" slug)"
MAIN="$(python3 "$Q/tools/storm_paths.py" repo)"
touch "$Q/integrated.txt" "$Q/abandoned.txt"
# The outer loop: refresh, repair, publish, merge-train, every ten minutes. Started here so it
# is on whenever a storm is, and --detached makes it stop when this runner does -- an outer
# loop that outlived the inner one would keep publishing lanes nobody was still producing.
# `ps -Ao args=`, not pgrep -f: macOS pgrep has no -a, and the check must not silently answer
# "not running" and start a second cycle beside the first.
# The hourly merge train, deliberately in its own process. The cycle runs the train every ten
# minutes as one of its steps, so on a healthy night this finds nothing to do -- it exists for
# the night the cycle dies, when the train would otherwise stop with it while lanes keep
# finishing and pull requests pile up behind a queue nobody is draining. A backstop sharing a
# process with the thing it backs up is not a backstop.
if ! ps -Ao args= | grep -q '[s]torm-merge.py'; then
  nohup python3 "$Q/tools/storm-merge.py" --run --every 3600 --detached \
    > "$Q/scratch/storm-merge.log" 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo "$(date -u +%FT%TZ) hourly merge train started (backstop for the 10-minute cycle)" \
    | tee -a "$Q/progress.log"
fi
if ! ps -Ao args= | grep -q '[s]torm-cycle.py'; then
  nohup python3 "$Q/tools/storm-cycle.py" --run --every 600 --detached \
    > "$Q/scratch/storm-cycle.log" 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo "$(date -u +%FT%TZ) outer cycle started (10 min: refresh, repair, publish, merge-train)" \
    | tee -a "$Q/progress.log"
fi
said=""
say_once() { [ "$said" = "$1" ] || { echo "$(date -u +%FT%TZ) $1" | tee -a "$Q/progress.log"; said="$1"; }; }
mkdir -p "$Q/scratch"
# How many lanes may run at once on this device (see the header). Any answer that is not a
# whole number of at least one -- an older vibey-gh without `slots`, an unreadable config, a
# runner that is down -- is one. The reason vibey-gh gives goes to scratch/slots.log.
slots() {
  local n
  n="$(cd "$MAIN" && "$PY" -m vibey_gh slots allowed 2>>"$Q/scratch/slots.log")" || n=""
  case "$n" in ''|*[!0-9]*|0) echo 1 ;; *) echo "$n" ;; esac
}
# Lanes running now: this storm's `running` marks (written before a lane starts, so a lane just
# launched is counted before its process exists) or, host-wide, every qwenlane process -- the
# model is shared by the host, not by this storm -- whichever is larger.
running() {
  local marks procs
  marks="$(find "$Q/lanes" -path '*/.qwenstorm/running' 2>/dev/null | wc -l | tr -d ' ')"
  procs="$(pgrep -f "qwenstorm-3.0.0/tools/qwenlane.py" | wc -l | tr -d ' ')"
  [ "$marks" -gt "$procs" ] && echo "$marks" || echo "$procs"
}
# A mark left by a runner that died mid-lane would hold that lane forever; at start nothing of
# this storm runs, so every mark is stale.
find "$Q/lanes" -path '*/.qwenstorm/running' -delete 2>/dev/null
run_lane() {
  local slug="$1" issue="$2" L="$Q/lanes/$1"
  "$PY" "$Q/tools/qwenlane.py" "$L" "$issue" "$(cat "$L/.qwenstorm/title.txt")" "$L/.qwenstorm/issue.md" > "$L/.qwenstorm/lane.log" 2>&1
  echo "$(date -u +%FT%TZ) end   $slug #$issue exit=$? $(tail -1 "$L/.qwenstorm/lane.log")" | tee -a "$Q/progress.log"
  [ -f "$L/.qwenstorm/result.json" ] || echo '{"completed": false, "crashed": true}' > "$L/.qwenstorm/result.json"
  rm -f "$L/.qwenstorm/running"
}
# The storm is idle: the one window a calibration of this device can run without measuring
# contention with a lane. Only when `slots allowed` asked for one, under the model lock the
# operator's measurements share, from this storm's own lanes (or, when none survive, its
# committed specs). A failure is logged and leaves the storm at one; it never blocks it.
calibrate_if_requested() {
  local dir="${VIBEY_GH_SLOTS_DIR:-$HOME/.local/state/vibey-gh/slots}"
  [ -n "$(find "$dir" -maxdepth 1 -name '*.request.json' 2>/dev/null)" ] || return 0
  echo "$(date -u +%FT%TZ) calibrating concurrent lanes for this device (requested)" | tee -a "$Q/progress.log"
  {
    if [ ! -s "$Q/scratch/slot-corpus.json" ]; then
      "$PY" "$Q/tools/storm_turn_pool.py" lanes --out "$Q/scratch/turn-pool.jsonl"
      [ -s "$Q/scratch/turn-pool.jsonl" ] \
        || "$PY" "$Q/tools/storm_turn_pool.py" specs --repo "$MAIN" --out "$Q/scratch/turn-pool.jsonl"
      (cd "$MAIN" && "$PY" -m vibey_gh slots corpus --pool "$Q/scratch/turn-pool.jsonl" \
        --out "$Q/scratch/slot-corpus.json")
    fi
    (cd "$MAIN" && "$PY" -m vibey_gh slots calibrate --if-requested \
      --corpus "$Q/scratch/slot-corpus.json" --lock "$(dirname "$Q")/.ollama-lock")
  } >> "$Q/scratch/slots-calibrate.log" 2>&1 \
    || echo "$(date -u +%FT%TZ) calibration did not finish; see scratch/slots-calibrate.log" | tee -a "$Q/progress.log"
}
said_slots=""
while true; do
  # "Next" means next after whatever is running (ADR-0054): the host-wide wait comes first,
  # so a lane is never interrupted -- a push made meanwhile only changes what starts after it.
  SLOTS="$(slots)"
  if [ "$SLOTS" != "$said_slots" ]; then
    echo "$(date -u +%FT%TZ) concurrent lanes: $SLOTS ($(tail -1 "$Q/scratch/slots.log" 2>/dev/null || echo 'vibey-gh did not answer; one'))" | tee -a "$Q/progress.log"
    said_slots="$SLOTS"
  fi
  while [ "$(running)" -ge "$SLOTS" ]; do sleep "${STORM_POLL_SECONDS:-30}"; done
  # What runs next is decided in ONE place, storm_queue.py, which storm-priority.py lists
  # from too, so the runner and the operator's view cannot disagree. It keeps this loop's old
  # rules exactly: the ledger (not lanes/) decides what is settled, a finished lane awaits
  # review and holds the storm unless UNATTENDED, a lane met before the next one whose
  # dependency was abandoned is marked blocked -- and the priority lane goes first.
  # It answers: run SLUG ISSUE | review SLUG.. | wait [SLUG..] | empty. A resolver that cannot
  # answer is waited out and said, never read as "empty": exit 3 is an unknown priority order
  # (an unreadable or vanished priority log), exit 4 a crash (see storm_queue.py).
  decision="$("$PY" "$Q/tools/storm_queue.py" next)"; rc=$?
  if [ "$rc" != 0 ]; then
    say_once "waiting: cannot decide what runs next (resolver exit $rc): ${decision:-the resolver did not answer}"
    sleep 60; continue
  fi
  # `read`, never an unquoted `set --` of the decision: that word-splits AND globs, so a slug
  # like `qu*` would have become whatever it matched in the current directory. The resolver
  # refuses such a slug; this keeps the runner safe even if one ever got through.
  read -r verdict rest <<<"$decision"
  case "$verdict" in
    empty) say_once "queue empty"; calibrate_if_requested; exit 0 ;;
    review) say_once "waiting for review: $rest"; sleep 60; continue ;;
    wait) say_once "waiting: no pending lane has all dependencies integrated (awaiting batch review: ${rest:-none})"; sleep 60; continue ;;
    run) ;;
    *) say_once "waiting: the resolver answered '$decision', which this runner does not know"; sleep 60; continue ;;
  esac
  read -r slug issue _ <<<"$rest"
  set -- "$slug" "$issue"
  said=""
  L="$Q/lanes/$1"
  if [ ! -d "$L" ]; then
    "$Q/tools/lane-setup.sh" "$1" integration >> "$Q/progress.log" 2>&1 \
      || { echo "$(date -u +%FT%TZ) setup failed $1" | tee -a "$Q/progress.log"; mkdir -p "$L/.qwenstorm"; echo '{"completed": false, "setup_failed": true}' > "$L/.qwenstorm/result.json"; continue; }
  fi
  # Outside text is contained at the seam it enters (12.j, ADR-0053). The issue is fetched,
  # WITH its author and every edit and rename, in one query, and admitted only if each account
  # is one [unattended_approval] authors names -- asked of vibey-gh through storm_trust.py, not
  # re-parsed here. Every start re-asks, so an issue edited since an earlier fetch is judged as
  # it is now. A stranger, or a history that cannot be read, is a refusal: the helper writes
  # result.json (as a blocked lane gets) and the reason goes to progress.log -- never skipped.
  mkdir -p "$L/.qwenstorm"
  if ! why="$("$PY" "$Q/tools/storm_trust.py" admit "$L/.qwenstorm" "$2")"; then
    [ -f "$L/.qwenstorm/result.json" ] \
      || echo '{"completed": false, "refused": "the provenance check did not finish"}' > "$L/.qwenstorm/result.json"
    echo "$(date -u +%FT%TZ) refused $1 #$2: ${why:-the provenance check did not finish}" | tee -a "$Q/progress.log"
    continue
  fi
  echo "$(date -u +%FT%TZ) $why" >> "$Q/progress.log"
  echo "$(date -u +%FT%TZ) start $1 #$2 on integration@$(git -C "$Q/integration" rev-parse --short HEAD)" | tee -a "$Q/progress.log"
  touch "$L/.qwenstorm/running"
  # One at a time runs in the foreground, exactly as before; more than one runs beside this
  # loop, which goes back to wait until fewer than SLOTS lanes are running.
  if [ "$SLOTS" -gt 1 ]; then run_lane "$1" "$2" & else run_lane "$1" "$2"; fi
done
