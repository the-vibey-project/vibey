"""Replay a realistic single-session agent transcript against a llama-server and time it.

One session, turn by turn, the way a qwenloop lane talks to its server under sub-doctrine
8.c: a plan, then N turns that each append the model's reply and a tool result (real repo
file text). Records llama-server's own per-request timings (prompt tokens actually
processed vs. reused from cache, generation speed) plus wall time.

usage: bench.py BASE_URL LABEL [API_KEY] [--turns 10]
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path("/private/tmp/claude-501/storm/qwenstorm-3.0.0")
REPO = ROOT / "integration"
PLAN = (ROOT / "specs/engines-pool.md").read_text()
FILES = [
    "src/vibey/infrastructure/engines/local_engines.py",
    "src/vibey/infrastructure/engines/descriptors.py",
    "src/vibey/infrastructure/config_loader.py",
    "src/vibey/infrastructure/cluster_preflight.py",
    "tests/infrastructure/engines/test_local_engines.py",
    "src/vibey/domain/config.py",
    "src/vibey/bootstrap.py",
    "src/vibey/cli/main.py",
    "tests/test_bootstrap.py",
    "tests/cli/test_operational_commands.py",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("label")
    ap.add_argument("api_key", nargs="?", default="")
    ap.add_argument("--turns", type=int, default=10)
    a = ap.parse_args()
    headers = {"Content-Type": "application/json"}
    if a.api_key:
        headers["Authorization"] = f"Bearer {a.api_key}"
    messages = [
        {
            "role": "system",
            "content": "You are a careful software engineer working in a git worktree.",
        },
        {"role": "user", "content": PLAN + "\n\nStart by stating which file you will read first."},
    ]
    rows = []
    start_all = time.monotonic()
    for turn in range(1, a.turns + 1):
        body = json.dumps(
            {
                "messages": messages,
                "max_tokens": 160,
                "temperature": 0,
                "cache_prompt": True,
                "stream": False,
            }
        ).encode()
        req = urllib.request.Request(f"{a.base_url}/chat/completions", data=body, headers=headers)
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=900) as r:
            data = json.loads(r.read())
        wall = time.monotonic() - t0
        tm = data.get("timings", {})
        reply = data["choices"][0]["message"].get("content") or ""
        rows.append(
            {
                "turn": turn,
                "wall_s": round(wall, 2),
                "prompt_n": tm.get("prompt_n"),
                "cache_n": tm.get("cache_n"),
                "prompt_ms": round(tm.get("prompt_ms", 0)),
                "gen_n": tm.get("predicted_n"),
                "gen_tps": round(tm.get("predicted_per_second", 0), 1),
                "ctx_tokens": data.get("usage", {}).get("prompt_tokens"),
            }
        )
        print(json.dumps({"label": a.label, **rows[-1]}), flush=True)
        text = (REPO / FILES[(turn - 1) % len(FILES)]).read_text()[:7000]
        messages += [
            {"role": "assistant", "content": reply},
            {
                "role": "user",
                "content": f"Tool result (read_file {FILES[(turn - 1) % len(FILES)]}):\n{text}\n\nNext step?",
            },
        ]
    total = time.monotonic() - start_all
    summary = {
        "label": a.label,
        "summary": True,
        "total_wall_s": round(total, 1),
        "prompt_ms_total": sum(r["prompt_ms"] for r in rows),
        "prompt_tokens_processed": sum(r["prompt_n"] or 0 for r in rows),
        "mean_gen_tps": round(sum(r["gen_tps"] for r in rows) / len(rows), 1),
        "final_ctx_tokens": rows[-1]["ctx_tokens"],
    }
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
