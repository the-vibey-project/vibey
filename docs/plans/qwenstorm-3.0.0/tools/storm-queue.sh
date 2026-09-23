#!/bin/bash
# storm-queue.sh -- run QwenStorm lanes one at a time (sub-doctrine 8.c: one loop instance).
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
Q=/private/tmp/claude-501/storm/qwenstorm-3.0.0
PY=/Users/adam/git/vibey/.venv-vibey-2.0.0/bin/python
touch "$Q/integrated.txt" "$Q/abandoned.txt"
# The outer loop: refresh, repair, publish, merge-train, every ten minutes. Started here so it
# is on whenever a storm is, and --detached makes it stop when this runner does -- an outer
# loop that outlived the inner one would keep publishing lanes nobody was still producing.
# `ps -Ao args=`, not pgrep -f: macOS pgrep has no -a, and the check must not silently answer
# "not running" and start a second cycle beside the first.
if ! ps -Ao args= | grep -q '[s]torm-cycle.py'; then
  nohup python3 "$Q/tools/storm-cycle.py" --run --every 600 --detached \
    > "$Q/scratch/storm-cycle.log" 2>&1 < /dev/null &
  disown 2>/dev/null || true
  echo "$(date -u +%FT%TZ) outer cycle started (10 min: refresh, repair, publish, merge-train)" \
    | tee -a "$Q/progress.log"
fi
settled() { grep -qx "$1" "$Q/integrated.txt" "$Q/abandoned.txt"; }
said=""
say_once() { [ "$said" = "$1" ] || { echo "$(date -u +%FT%TZ) $1" | tee -a "$Q/progress.log"; said="$1"; }; }
while true; do
  while pgrep -f "qwenstorm-3.0.0/tools/qwenlane.py" >/dev/null; do sleep 30; done
  unreviewed=""; pending=0; next=""
  while read -r slug issue deps; do
    [ -z "$slug" ] && continue
    # The ledger decides, not the scratch directory. A lane in integrated.txt or abandoned.txt
    # is done however little of lanes/ survives: /tmp is wiped between sessions, and keying
    # "done" off result.json re-ran every already-integrated lane on top of work the
    # integration branch already carries.
    settled "$slug" && continue
    if [ -f "$Q/lanes/$slug/.qwenstorm/result.json" ]; then
      unreviewed="$unreviewed $slug"; continue
    fi
    pending=$((pending + 1))
    [ -n "$next" ] && continue
    ok=1
    for d in ${deps//,/ }; do
      if grep -qx "$d" "$Q/abandoned.txt"; then
        mkdir -p "$Q/lanes/$slug/.qwenstorm"
        echo "{\"completed\": false, \"blocked_on\": \"$d\"}" > "$Q/lanes/$slug/.qwenstorm/result.json"
        echo "$(date -u +%FT%TZ) blocked $slug #$issue: dependency $d was abandoned" | tee -a "$Q/progress.log"
        ok=0; break
      fi
      grep -qx "$d" "$Q/integrated.txt" || { ok=0; break; }
    done
    [ "$ok" = 1 ] && next="$slug $issue"
  done < "$Q/queue.txt"
  if [ "$pending" = 0 ] && [ -z "$unreviewed" ]; then say_once "queue empty"; exit 0; fi
  if [ -n "$unreviewed" ] && [ ! -f "$Q/UNATTENDED" ]; then say_once "waiting for review:$unreviewed"; sleep 60; continue; fi
  if [ -z "$next" ]; then say_once "waiting: no pending lane has all dependencies integrated (awaiting batch review:${unreviewed:- none})"; sleep 60; continue; fi
  said=""
  set -- $next; L="$Q/lanes/$1"
  if [ ! -d "$L" ]; then
    "$Q/tools/lane-setup.sh" "$1" integration >> "$Q/progress.log" 2>&1 \
      || { echo "$(date -u +%FT%TZ) setup failed $1" | tee -a "$Q/progress.log"; mkdir -p "$L/.qwenstorm"; echo '{"completed": false, "setup_failed": true}' > "$L/.qwenstorm/result.json"; continue; }
  fi
  if [ ! -s "$L/.qwenstorm/issue.md" ]; then
    mkdir -p "$L/.qwenstorm"
    (cd /Users/adam/git/vibey && gh issue view "$2" -R the-vibey-project/vibey --json body --jq .body) > "$L/.qwenstorm/issue.md"
    (cd /Users/adam/git/vibey && gh issue view "$2" -R the-vibey-project/vibey --json title --jq .title) > "$L/.qwenstorm/title.txt"
  fi
  echo "$(date -u +%FT%TZ) start $1 #$2 on integration@$(git -C "$Q/integration" rev-parse --short HEAD)" | tee -a "$Q/progress.log"
  "$PY" "$Q/tools/qwenlane.py" "$L" "$2" "$(cat "$L/.qwenstorm/title.txt")" "$L/.qwenstorm/issue.md" > "$L/.qwenstorm/lane.log" 2>&1
  echo "$(date -u +%FT%TZ) end   $1 #$2 exit=$? $(tail -1 "$L/.qwenstorm/lane.log")" | tee -a "$Q/progress.log"
  [ -f "$L/.qwenstorm/result.json" ] || echo '{"completed": false, "crashed": true}' > "$L/.qwenstorm/result.json"
done
