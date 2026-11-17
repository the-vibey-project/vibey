# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Container bases are pinned by digest and hook repos by commit SHA.

A mutable tag (`python:3.12-slim-bookworm`, `rev: v0.16.3`) lets the thing a build or a
commit runs change underneath it with no diff to show for it. A digest or a SHA cannot.

These are collection contracts: module-level test functions are used on purpose
(ADR-0016), as in the neighbouring meta tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO / "deploy" / "docker" / "Dockerfile"
PRECOMMIT = REPO / ".pre-commit-config.yaml"

FROM = re.compile(r"^FROM\s+(?:--\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def test_every_dockerfile_from_names_a_sha256_digest() -> None:
    stages: set[str] = set()
    unpinned: list[str] = []
    for number, line in enumerate(DOCKERFILE.read_text().splitlines(), start=1):
        match = FROM.match(line)
        if not match:
            continue
        image, stage = match.group(1), match.group(2)
        if image != "scratch" and image not in stages and not DIGEST.search(image):
            unpinned.append(f"line {number}: FROM {image}")
        if stage:
            stages.add(stage)
    assert not unpinned, f"FROM without @sha256 digest: {unpinned}"


def test_every_precommit_repo_rev_is_a_40_hex_sha() -> None:
    config = yaml.safe_load(PRECOMMIT.read_text())
    bad = [
        f"{repo['repo']} rev={repo.get('rev')!r}"
        for repo in config["repos"]
        if repo["repo"] != "local" and not SHA.match(str(repo.get("rev", "")))
    ]
    assert not bad, f"hook repos not pinned to a commit SHA: {bad}"
