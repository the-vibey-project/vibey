# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A webhook URL is a credential: whoever holds it can post as the project.

The release pipeline announces published surfaces through `DISCORD_WEBHOOK_URL`, a
repository secret the workflow names and never carries. This check walks every tracked
file so the value cannot land in the tree by accident, in a workflow, a document, a
test fixture or a note.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Assembled from parts so this file never contains the pattern it forbids.
_WEBHOOK = re.compile("discord(?:app)?\\.com/api/" + "webhooks/" + r"\\d+/[A-Za-z0-9_-]{20,}")


def _tracked_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return [REPO / name for name in listed.split("\0") if name]


def test_no_tracked_file_carries_a_discord_webhook_url() -> None:
    offenders: list[str] = []
    for path in _tracked_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _WEBHOOK.search(text):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"a Discord webhook URL is committed in: {offenders}"
