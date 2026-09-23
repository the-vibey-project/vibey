# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A webhook URL is a credential: whoever holds it can post as the project.

The release pipeline announces published surfaces through `DISCORD_WEBHOOK_URL`, a
repository secret the workflow names and never carries. This check walks every tracked
file as bytes, so a URL hidden in a PDF, an image's metadata or any other binary is as
visible as one in a workflow, and it proves on a synthetic URL that it can match at all.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Assembled from parts so this file never contains the pattern it forbids.
_WEBHOOK = re.compile(rb"discord(?:app)?\.com/api/" + b"webhooks/" + rb"\d+/[A-Za-z0-9_-]{20,}")


def _tracked_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return [REPO / name for name in listed.split("\0") if name]


def test_the_guard_recognises_a_webhook_url() -> None:
    sample = "https://discord.com/api/" + "webhooks/" + "1234567890123456789/" + "a" * 68
    assert _WEBHOOK.search(sample.encode()), "the guard would miss a real webhook URL"
    assert not _WEBHOOK.search(b"https://discord.com/widget?id=1234567890123456789")


def test_no_tracked_file_carries_a_discord_webhook_url() -> None:
    offenders = [
        str(path.relative_to(REPO))
        for path in _tracked_files()
        if path.is_file() and _WEBHOOK.search(path.read_bytes())
    ]
    assert not offenders, f"a Discord webhook URL is committed in: {offenders}"
