#!/bin/bash
# Benchmark llama-server configurations for one-instance-per-loop (sub-doctrine 8.c).
# Runs each config alone (the machine cannot hold two 14B servers), same 10-turn replay.
B=/private/tmp/claude-501/storm/qwenstorm-3.0.0/bench
MODEL=/Users/adam/Library/Caches/qwenloop/models/qwen2.5-coder-14b-q5-k-m/qwen2.5-coder-14b-instruct-q5_k_m.gguf
DRAFT=/Users/adam/.ollama/models/blobs/sha256-29d8c98fa6b098e200069bfb88b9508dc3e85586d20cba59f8dda9a808165104
PY=/Users/adam/git/vibey/.venv-vibey-2.0.0/bin/python
PORT=18091
: > "$B/results.jsonl"
run() {  # label, extra args...
  label="$1"; shift
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
