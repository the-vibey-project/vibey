"""What `pip install krypton-app` brings with it: the engine, and the hub the launcher starts.

Measured on 2026-09-29: krypton-app depended on bare `vibey-engine`, whose hub web stack
(fastapi, uvicorn) is the `hub` extra (ADR-0067). `pip install krypton-app` alone therefore
installed a launcher whose one job -- `vibey serve` -- crashed on `No module named
'fastapi'`. These read the two manifests rather than an installed environment, because the
CI job runs this suite from the source tree without installing either package.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

CLIENT = Path(__file__).resolve().parents[1]
ENGINE_PYPROJECT = CLIENT.parents[1] / "pyproject.toml"


def _engine_requirement() -> Requirement:
    with (CLIENT / "pyproject.toml").open("rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    engines = [Requirement(d) for d in dependencies if Requirement(d).name == "vibey-engine"]
    assert len(engines) == 1, f"expected one vibey-engine requirement, found {dependencies}"
    return engines[0]


def test_krypton_app_installs_the_engine_with_its_hub() -> None:
    assert "hub" in _engine_requirement().extras


def test_the_engine_requirement_stays_unpinned() -> None:
    """The two packages release on their own cadences; the launcher checks the installed
    engine's abilities at run time instead of trusting a version number."""
    assert str(_engine_requirement().specifier) == ""


def test_the_extra_it_names_is_one_the_engine_declares_and_it_carries_the_web_stack() -> None:
    if not ENGINE_PYPROJECT.is_file():
        pytest.skip(f"no engine manifest at {ENGINE_PYPROJECT}; not running from the repository")
    with ENGINE_PYPROJECT.open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["name"] == "vibey-engine"
    extras = project["optional-dependencies"]
    for extra in _engine_requirement().extras:
        assert extra in extras, f"vibey-engine declares no [{extra}] extra"
    hub = {Requirement(r).name for r in extras["hub"]}
    assert {"fastapi", "uvicorn"} <= hub
