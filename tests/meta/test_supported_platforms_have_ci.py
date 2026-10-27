# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every Linux distribution vibey declares has CI that proves it, or says it has none (#1116).

`scripts/minimum_specs.toml` declares the Linux distributions the requirements tables cover.
A declaration is a claim, and "a floor nothing runs on is a claim, not a contract" (ADR-0022),
so each distro names the CI cell that proves it, or carries an explicit `pending` marker, and
this test holds both to `.github/workflows/ci.yml`:

1. A distro declares `ci`, as a `job` and `cell`, or as `pending` with the reason.
2. A declared cell exists in that job's matrix.
3. A release-numbered distro (`ubuntu-24.04`) declares `pinned`, and the claim is true: a
   cell on `ubuntu-latest` does not prove Ubuntu 24.04, whatever the row is called.
4. A Linux cell in the job is accounted for by a declared distro, so CI cannot quietly gain a
   platform the requirements never mention.

The checks are a class over plain data, so the same rules run against the real files and,
below, against deliberately broken ones (a rule that cannot fail is not a rule).
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RELEASE_SUFFIX = re.compile(r"-(\d+\.\d+)$")


class PlatformCiAudit:
    """Audits declared distros against a workflow's matrix cells."""

    def __init__(self, distros: Mapping[str, Mapping[str, Any]], workflow: Mapping[str, Any]):
        self._distros = distros
        self._workflow = workflow

    def cells(self, job: str) -> dict[str, Mapping[str, Any]]:
        matrix = self._workflow["jobs"][job]["strategy"]["matrix"]["include"]
        return {str(cell["distro"]): cell for cell in matrix}

    def problems(self) -> list[str]:
        found: list[str] = []
        claimed: dict[str, set[str]] = {}
        for key, distro in self._distros.items():
            ci = distro.get("ci")
            if not isinstance(ci, Mapping):
                found.append(f"{key}: declares no `ci` (a job and cell, or `pending`)")
                continue
            if ci.get("pending"):
                continue
            job, cell = ci.get("job"), ci.get("cell")
            if not job or not cell:
                found.append(f"{key}: `ci` names neither a job and cell nor `pending`")
                continue
            claimed.setdefault(str(job), set()).add(str(cell))
            cells = self.cells(str(job)) if job in self._workflow["jobs"] else {}
            if cell not in cells:
                found.append(f"{key}: ci cell {job}/{cell} is not in the workflow matrix")
                continue
            found.extend(self._pinning(key, ci, cells[str(cell)]))
        found.extend(self._unaccounted(claimed))
        return found

    def _pinning(self, key: str, ci: Mapping[str, Any], cell: Mapping[str, Any]) -> list[str]:
        release = RELEASE_SUFFIX.search(key)
        if release is None:
            return []
        if not isinstance(ci.get("pinned"), bool):
            return [f"{key}: a release-numbered distro must declare `pinned` true or false"]
        names_release = release.group(1) in f"{cell.get('runner', '')} {cell.get('container', '')}"
        if ci["pinned"] != names_release:
            return [
                f"{key}: declares pinned={ci['pinned']}, but its cell runs on "
                f"{cell.get('runner')!r} / {cell.get('container')!r}"
            ]
        return []

    def _unaccounted(self, claimed: Mapping[str, set[str]]) -> list[str]:
        found = []
        for job, names in claimed.items():
            for name, cell in self.cells(job).items():
                linux = str(cell.get("runner", "")).startswith("ubuntu")
                if linux and name not in names:
                    found.append(f"ci {job}/{name} runs Linux but no declared distro names it")
        return found


def _real() -> PlatformCiAudit:
    toml = tomllib.loads((ROOT / "scripts" / "minimum_specs.toml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    return PlatformCiAudit(toml["minimum_specs"]["linux"]["distros"], workflow)


def _workflow(*cells: dict[str, str]) -> dict[str, Any]:
    return {"jobs": {"desktop": {"strategy": {"matrix": {"include": list(cells)}}}}}


UBUNTU_LATEST = {"distro": "ubuntu", "runner": "ubuntu-latest", "container": ""}


def test_every_declared_distro_is_proven_by_ci_or_says_it_is_not() -> None:
    assert _real().problems() == []


def test_the_real_declarations_are_not_vacuous() -> None:
    audit = _real()
    assert {"ubuntu", "arch", "fedora"} <= set(audit.cells("desktop"))
    assert len(audit._distros) >= 4


def test_a_distro_with_no_ci_declaration_is_refused() -> None:
    audit = PlatformCiAudit({"arch": {}}, _workflow(UBUNTU_LATEST))
    assert audit.problems() == ["arch: declares no `ci` (a job and cell, or `pending`)"]


def test_a_cell_missing_from_the_matrix_is_refused() -> None:
    declared = {"fedora": {"ci": {"job": "desktop", "cell": "fedora"}}}
    audit = PlatformCiAudit(declared, _workflow(UBUNTU_LATEST))
    assert audit.problems()[0].startswith("fedora: ci cell desktop/fedora is not in")


def test_floating_ubuntu_cannot_be_declared_pinned() -> None:
    declared = {
        "ubuntu-24.04": {"ci": {"job": "desktop", "cell": "ubuntu", "pinned": True}},
    }
    audit = PlatformCiAudit(declared, _workflow(UBUNTU_LATEST))
    assert "declares pinned=True" in audit.problems()[0]


def test_a_pinned_cell_may_say_so_and_a_release_must_say_which() -> None:
    cell = {"distro": "ubuntu", "runner": "ubuntu-latest", "container": "ubuntu:24.04"}
    ok = {"ubuntu-24.04": {"ci": {"job": "desktop", "cell": "ubuntu", "pinned": True}}}
    assert PlatformCiAudit(ok, _workflow(cell)).problems() == []
    silent = {"ubuntu-24.04": {"ci": {"job": "desktop", "cell": "ubuntu"}}}
    assert "must declare `pinned`" in PlatformCiAudit(silent, _workflow(cell)).problems()[0]


def test_a_pending_distro_needs_no_cell_and_a_half_declared_one_is_refused() -> None:
    pending = {"ubuntu-26.04": {"ci": {"pending": "not built"}}}
    assert PlatformCiAudit(pending, _workflow(UBUNTU_LATEST)).problems() == []
    half = {"arch": {"ci": {"job": "desktop"}}}
    assert "neither a job and cell" in PlatformCiAudit(half, _workflow(UBUNTU_LATEST)).problems()[0]


def test_ci_cannot_gain_a_linux_platform_the_declarations_never_mention() -> None:
    declared = {"fedora": {"ci": {"job": "desktop", "cell": "fedora"}}}
    fedora = {"distro": "fedora", "runner": "ubuntu-latest", "container": "fedora:latest"}
    audit = PlatformCiAudit(declared, _workflow(fedora, UBUNTU_LATEST))
    assert audit.problems() == ["ci desktop/ubuntu runs Linux but no declared distro names it"]
