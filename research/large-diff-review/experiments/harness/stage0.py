"""Stage 0 -- feasibility. Reads no quality outcome: a synthetic toy diff, timing, rendering.

1. Does `render_harmony` render exactly what Ollama's chat path renders? (equal
   prompt_eval_count for the same conversation, raw vs chat)
2. Which budget-forcing mechanism yields a complete, schema-valid, code-echoing answer
   after the reasoning is cut at a budget: chat prefill (no format), chat prefill with
   format, raw generate? And is the prefix's KV reused (phase-2 prompt_eval time)?
3. Is the prompt cache reused across two identical requests?
"""

from __future__ import annotations

import json
import sys

from client import Model
from review import DEFECT_SCHEMA, Asker, render_harmony
from vibey_gh import local_review as lr

TOY_DIFF = '''diff --git a/toy/limits.py b/toy/limits.py
--- a/toy/limits.py
+++ b/toy/limits.py
@@ -1,12 +1,14 @@
 """Rate limits for the toy service."""


 def allowed(requests_this_minute: int, limit: int) -> bool:
-    """True while the caller is under its per-minute limit."""
-    return requests_this_minute < limit
+    """True while the caller is under its per-minute limit, inclusive of the last one."""
+    if limit <= 0:
+        return False
+    return requests_this_minute <= limit


 def remaining(requests_this_minute: int, limit: int) -> int:
     return max(0, limit - requests_this_minute)
'''


def payload() -> dict:
    return {
        "model": "gpt-oss:20b",
        "messages": [
            {"role": "system", "content": lr.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Review this pull request diff.\n\n<diff>\n{TOY_DIFF}\n</diff>",
            },
        ],
        "format": DEFECT_SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }


def main() -> int:
    model = Model()
    asker = Asker(model)
    out = {}
    tag = {"stage": 0}

    # 1. rendering
    body, codes = asker.sealed(payload())
    chat = dict(body, options={**body["options"], "num_predict": 1})
    r1 = model.ask("/api/chat", chat, 300, tag={**tag, "test": "render-chat"})
    system, user = (m["content"] for m in body["messages"])
    raw = {
        "model": "gpt-oss:20b",
        "raw": True,
        "stream": False,
        "prompt": render_harmony(system, user) + "<|start|>assistant",
        "options": {"temperature": 0, "num_ctx": 65536, "num_predict": 1},
    }
    r2 = model.ask("/api/generate", raw, 300, tag={**tag, "test": "render-raw"})
    out["render"] = {
        "chat_prompt_tokens": r1["prompt_tokens"],
        "raw_prompt_tokens": r2["prompt_tokens"],
    }
    print(json.dumps(out["render"]), flush=True)

    # 2. forcing: cut the reasoning at 160 tokens, then force each way.
    full = dict(body, options={**body["options"], "num_predict": 160})
    r3 = model.ask("/api/chat", full, 600, tag={**tag, "test": "phase1-160"})
    thinking = model.store.thinking(r3["key"])
    out["phase1"] = {
        k: r3[k]
        for k in (
            "done_reason",
            "reasoning_chars",
            "answer_chars",
            "prompt_tokens",
            "prompt_eval_s",
            "wall_s",
        )
    }
    print(json.dumps(out["phase1"]), flush=True)
    for mode in ("prefill", "prefill-format", "raw"):
        rec, verdict, code, reason = asker.forced(
            body, thinking, codes, mode, {**tag, "test": f"force-{mode}"}, 0
        )
        out[mode] = {
            "code": code,
            "reason": reason[:200],
            "done_reason": rec.get("done_reason"),
            "prompt_tokens": rec.get("prompt_tokens"),
            "prompt_eval_s": rec.get("prompt_eval_s"),
            "eval_tokens": rec.get("eval_tokens"),
            "wall_s": rec.get("wall_s"),
            "content_head": (rec.get("content") or "")[:160],
            "reasoning_chars": rec.get("reasoning_chars"),
            "verdict_keys": sorted(verdict) if verdict else None,
        }
        print(mode, json.dumps(out[mode]), flush=True)

    # 3. an unforced full answer twice (determinism + cache)
    for rep in (0, 1):
        full = dict(body, options={**body["options"], "num_predict": 4096})
        r = model.ask("/api/chat", full, 900, tag={**tag, "test": "full"}, replicate=rep)
        out[f"full{rep}"] = {
            k: r[k]
            for k in (
                "done_reason",
                "reasoning_chars",
                "answer_chars",
                "prompt_tokens",
                "prompt_eval_s",
                "eval_tokens",
                "wall_s",
            )
        }
        out[f"full{rep}"]["content"] = r["content"][:300]
        print(f"full{rep}", json.dumps(out[f"full{rep}"]), flush=True)
    from client import RESULTS

    (RESULTS / "stage0.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
