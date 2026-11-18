# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The container image's build stage and runtime stage run the same Python minor version.

`deploy/docker/Dockerfile` builds the application's virtualenv in one stage (a `uv` image that
carries Python 3.12) and copies it into a second, slimmer stage. A virtualenv records the
interpreter it was made with and keeps its packages under `lib/python3.12/site-packages`, so a
runtime stage on a different minor version starts, finds no `vibey`, and fails with
`ModuleNotFoundError`. The image check in CI caught it once, after a base-image bump had already
merged; this holds it at the source, so the mismatch fails in the pull request that causes it.

The same minor version also appears in the path of the pip files the runtime stage deletes, so
that path is held to it too.

These are collection contracts: module-level test functions are used on purpose (ADR-0016), as
in the neighbouring meta tests.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO / "deploy" / "docker" / "Dockerfile"

BUILD_FROM = re.compile(
    r"^FROM\s+\S*python(\d+\.\d+)\S*\s+AS\s+build\b", re.MULTILINE | re.IGNORECASE
)
RUNTIME_FROM = re.compile(
    r"^FROM\s+python:(\d+\.\d+)[-@]\S*\s+AS\s+runtime\b", re.MULTILINE | re.IGNORECASE
)
SITE_PACKAGES = re.compile(r"/usr/local/lib/python(\d+\.\d+)/site-packages")


def _versions(text: str) -> dict[str, set[str]]:
    return {
        "build stage image": set(BUILD_FROM.findall(text)),
        "runtime stage image": set(RUNTIME_FROM.findall(text)),
        "runtime pip paths": set(SITE_PACKAGES.findall(text)),
    }


def disagreement(text: str) -> str:
    """Why the Dockerfile's Python versions disagree, or an empty string when they do not."""
    found = _versions(text)
    missing = [name for name, versions in found.items() if not versions]
    if missing:
        return f"could not read a Python version from: {', '.join(missing)}"
    distinct = set().union(*found.values())
    if len(distinct) == 1:
        return ""
    return "Python minor versions differ: " + "; ".join(
        f"{name}={sorted(versions)}" for name, versions in found.items()
    )


def test_the_build_and_runtime_stages_run_the_same_python() -> None:
    problem = disagreement(DOCKERFILE.read_text(encoding="utf-8"))
    assert not problem, problem


def test_a_runtime_stage_on_another_minor_version_is_named() -> None:
    text = (
        "FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim@sha256:aa AS build\n"
        "FROM python:3.15-slim-bookworm@sha256:bb AS runtime\n"
        "RUN rm -rf /usr/local/lib/python3.12/site-packages/pip\n"
    )
    problem = disagreement(text)
    assert "differ" in problem
    assert "'3.15'" in problem


def test_pip_paths_that_name_another_minor_version_are_named() -> None:
    text = (
        "FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim@sha256:aa AS build\n"
        "FROM python:3.12-slim-bookworm@sha256:bb AS runtime\n"
        "RUN rm -rf /usr/local/lib/python3.15/site-packages/pip\n"
    )
    assert "differ" in disagreement(text)


def test_matching_versions_are_clean() -> None:
    text = (
        "FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim@sha256:aa AS build\n"
        "FROM python:3.12-slim-bookworm@sha256:bb AS runtime\n"
        "RUN rm -rf /usr/local/lib/python3.12/site-packages/pip\n"
    )
    assert disagreement(text) == ""


def test_a_dockerfile_with_no_readable_version_is_not_a_clean_pass() -> None:
    assert "could not read" in disagreement("FROM scratch\n")
