#!/bin/bash
# Benchmark llama-server configurations for one-instance-per-loop (sub-doctrine 8.c).
# Runs each config alone (the machine cannot hold two 14B servers), same 10-turn replay.
#
# Resumable (10.h, ADR-0057): results.jsonl is appended to, never truncated, and a label whose
# session summary is already in it is skipped, so a reboot or a kill mid-run costs only the
# configuration that was running. To measure a configuration again, move results.jsonl aside
# first; the old file is the record of the old run. A label cut short leaves turn rows with no
# summary row, and a rerun appends a whole fresh session after them.
#
# The directory is this script's own, never a literal (12.h), and the durability gate refuses
# it when it resolves to storage the OS empties. MODEL, DRAFT, PY and PORT may be set in the
# environment; the defaults are the machine the benchmark was first run on.
B="$(cd "$(dirname "$0")" && pwd)"
MODEL="${MODEL:-$HOME/Library/Caches/qwenloop/models/qwen2.5-coder-14b-q5-k-m/qwen2.5-coder-14b-instruct-q5_k_m.gguf}"
DRAFT="${DRAFT:-$HOME/.ollama/models/blobs/sha256-29d8c98fa6b098e200069bfb88b9508dc3e85586d20cba59f8dda9a808165104}"
PY="${PY:-$HOME/git/vibey/.venv-vibey-2.0.0/bin/python}"
PORT="${PORT:-18091}"
python3 "$B/../tools/storm_durability.py" check --path "results=$B/results.jsonl" || exit $?
touch "$B/results.jsonl"
run() {  # label, extra args...
  label="$1"; shift
  if grep -q "\"label\": \"$label\", \"summary\": true" "$B/results.jsonl"; then
    echo "skip $label: its session is already recorded in results.jsonl"
    return
  fi
  llama-server --model "$MODEL" --host 127.0.0.1 --port $PORT --jinja "$@" > "$B/server-$label.log" 2>&1 &
  pid=$!
  for i in $(seq 1 120); do
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $pid 2>/dev/null || { echo "{\"label\": \"$label\", \"error\": \"server exited during load\"}" >> "$B/results.jsonl"; return; }
    sleep 2
  done
  "$PY" "$B/bench.py" "http://127.0.0.1:$PORT/v1" "$label" >> "$B/results.jsonl" 2>> "$B/bench-errors.log" \
    || echo "{\"label\": \"$label\", \"error\": \"bench failed\"}" >> "$B/results.jsonl"
  grep -E "llama_kv_cache|KV self size|CPU_Mapped|Metal_Mapped|n_slots|total VRAM|recommendedMaxWorkingSetSize" "$B/server-$label.log" | head -8 > "$B/server-$label.summary"
  kill $pid; wait $pid 2>/dev/null
}
run A-baseline --ctx-size 32768
run D-1slot-f16-32k --ctx-size 32768 -np 1 -fa on
run B-1slot-q8-48k --ctx-size 49152 -np 1 -fa on -ctk q8_0 -ctv q8_0
run C-1slot-q8-48k-draft --ctx-size 49152 -np 1 -fa on -ctk q8_0 -ctv q8_0 --model-draft "$DRAFT" --spec-draft-n-max 16
echo done
