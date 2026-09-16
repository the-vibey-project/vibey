# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rewrite ``api_baseline.json`` from the OpenAI SDK installed right now.

Run this ONLY as part of a deliberate SDK upgrade, in the same commit as the
``openai`` bound in ``pyproject.toml``. The baseline is what makes the drift gate
mean anything: refreshing it on an unrelated branch converts a review prompt into
a rubber stamp, which is the one thing the gate exists to prevent.

    python tools/refresh_api_baseline.py

It prints the delta rather than only writing the file, because the point of the
upgrade is to look at what changed -- a removed method is a ``codexloop api``
command that disappears from someone's scripts, and that deserves to be read
before it is committed. Exits non-zero when nothing changed, so it cannot be run
out of habit and leave a no-op commit behind.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import openai

from codexloop.infrastructure.api.introspect import discover_surface

BASELINE = Path(__file__).resolve().parents[1] / (
    "src/codexloop/infrastructure/api/api_baseline.json"
)


def main() -> int:
    previous = json.loads(BASELINE.read_text(encoding="utf-8"))
    surface = discover_surface()
    current = {
        "openai_version": openai.__version__,
        "method_count": len(surface),
        "local_helpers": sorted(spec.path for spec in surface if spec.is_local_helper),
        "methods": sorted(spec.path for spec in surface),
    }

    added = sorted(set(current["methods"]) - set(previous["methods"]))
    removed = sorted(set(previous["methods"]) - set(current["methods"]))
    helpers_changed = set(current["local_helpers"]) != set(previous["local_helpers"])
    # The recorded version counts as a difference in its own right. A release can leave
    # the method set untouched, and treating that as "nothing changed" would leave the
    # snapshot naming an SDK nobody is running -- the baseline's first field says which
    # version it describes, so a stale one is a stale baseline even when the surface
    # happens to match.
    version_changed = current["openai_version"] != previous["openai_version"]

    print(f"openai {previous['openai_version']} -> {current['openai_version']}")
    print(f"methods {previous['method_count']} -> {current['method_count']}")
    for path in added:
        print(f"  + {path}")
    for path in removed:
        print(f"  - {path}")
    if helpers_changed:
        print("  ! local_helpers changed -- update LOCAL_HELPER_PATHS to match")

    if not added and not removed and not helpers_changed and not version_changed:
        print("baseline already matches the installed SDK; nothing written")
        return 1
    if not added and not removed and not helpers_changed:
        print("  (surface unchanged; refreshing the recorded version only)")

    BASELINE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {BASELINE.relative_to(BASELINE.parents[2])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
