#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measure the local Ollama JSON path without claiming cross-host capability."""

from __future__ import annotations

import argparse
import json
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
        return {
            "ok": isinstance(content, str) and bool(content.strip()),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "content_chars": len(content) if isinstance(content, str) else 0,
            "eval_count": body.get("eval_count"),
            "context": context,
            "output": output,
        }
    except Exception as exc:  # pragma: no cover - host-dependent probe failures
        return {
            "ok": False,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "context": context,
            "output": output,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument("--output", type=int, default=2048)
    args = parser.parse_args()
    result = {
        "measured_at": datetime.now(UTC).isoformat(),
        "url": args.url,
        "model": args.model,
        "probe": probe(args.url, args.model, args.context, args.output, 'Return {"ok":true}.'),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["probe"]["ok"] else 2  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
