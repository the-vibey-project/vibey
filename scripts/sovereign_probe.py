#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measure the local Ollama JSON path without claiming cross-host capability."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from datetime import UTC, datetime


def probe(url: str, model: str, context: int, output: int, prompt: str) -> dict[str, object]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": context, "num_predict": output},
    }
    started = time.monotonic()
    try:
        request = urllib.request.Request(
            f"{url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310
            body = json.loads(response.read())
        content = body.get("message", {}).get("content", "")
        valid = isinstance(content, str) and bool(content.strip())
        return {
            # ``valid`` is the persisted fit contract consumed by
            # OllamaChatClient._load_fit.  ``ok`` remains as the per-probe status
            # used by this script and by older records.
            "ok": valid,
            "valid": valid,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "content_chars": len(content) if isinstance(content, str) else 0,
            "eval_count": body.get("eval_count"),
            "context": context,
            "output": output,
        }
    except Exception as exc:  # pragma: no cover - host-dependent probe failures
        return {
            "ok": False,
            "valid": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "context": context,
            "output": output,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--contexts", default="4096,8192")
    parser.add_argument("--outputs", default="512,1024,2048")
    parser.add_argument("--record", type=str)
    args = parser.parse_args()
    contexts = [int(value) for value in args.contexts.split(",")]
    outputs = [int(value) for value in args.outputs.split(",")]
    results = [
        probe(args.url, args.model, context, output, 'Return {"ok":true}.')
        for context in contexts
        for output in outputs
    ]
    valid = [item for item in results if item["ok"]]
    selected = (
        min(valid, key=lambda item: (item["elapsed_seconds"], item["context"], item["output"]))
        if valid
        else None
    )
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    result = {
        "measured_at": datetime.now(UTC).isoformat(),
        "url": args.url,
        "model": args.model,
        "revision": revision,
        "prompt_shape": {"system_chars": 22, "user_chars": 20},
        "results": results,
        "selected_fit": selected,
    }
    encoded = json.dumps(result, sort_keys=True)
    if args.record:
        with open(args.record, "w", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
    print(encoded)
    return 0 if selected is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
