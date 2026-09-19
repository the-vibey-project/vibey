# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every import-linter contract in this tree can actually be broken.

A contract that cannot be broken is reported KEPT forever, and that reads as the best
news a gate can give. Three ways to write one were found live in this tree (#263), and
each is caught here without building an import graph:

1. The root package is not top-level. grimp builds its graph from top-level packages
   only, so `root_package = "vibey_runners.common"` raised NotATopLevelModule before any
   contract was evaluated. Both of vibey-runners-common's contracts had never been
   checked once.

2. A forbidden module overlaps a source module. import-linter skips every pair where
   one module is the other or contains it, so forbidding `agyloop.cli` from
   `agyloop.cli.interfaces` searches nothing at all. The agy lane planted
   `interfaces -> run_outcome` and the contract still reported KEPT.

3. A forbidden module inside the tree does not exist. import-linter filters forbidden
   modules down to those present in the graph, silently, so a typo or a rename leaves
   that line enforcing nothing.

Wildcard expressions (`vibey.application.*`) are exempt from rules 2 and 3.
import-linter documents the overlap skip as what makes a wildcard usable, since the
source is often one of the modules it matches. A wildcard that matches nothing is a
separate question, and import-linter already reports it.

Every configuration is discovered, not listed (ADR-0018): the root `.importlinter`,
plus the `[tool.importlinter]` table of each tenant under src/vibey_runners/ and
src/vibey_tools/.

Module-level test functions for the reason tests/meta/test_adr_counts.py gives: pytest
collects `test_*` functions, and ADR-0016's class rule is about production code.
"""

from __future__ import annotations

import configparser
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
TENANT_ROOTS = ("src/vibey_runners", "src/vibey_tools")


@dataclass(frozen=True)
class Config:
    """One import-linter configuration, normalised across the INI and TOML forms."""

    where: str
    roots: tuple[str, ...]
    contracts: tuple[dict[str, Any], ...]
    search: tuple[Path, ...]


def _lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _root_config() -> Config:
    parser = configparser.ConfigParser()
    parser.read(REPO / ".importlinter", encoding="utf-8")
    session = parser["importlinter"]
    roots = _lines(session.get("root_packages", "")) or _lines(session.get("root_package", ""))
    contracts = tuple(
        dict(parser[name])
        for name in parser.sections()
        if name.startswith("importlinter:contract:")
    )
    # The root graph spans src/vibey and every tenant it names, so its packages are looked
    # for wherever a tenant keeps them: under its own src/, or flat in its directory.
    tenant_dirs = [
        p for root in TENANT_ROOTS for p in sorted((REPO / root).iterdir()) if p.is_dir()
    ]
    search = (REPO / "src", *(d / "src" for d in tenant_dirs), *tenant_dirs)
    return Config(".importlinter", tuple(roots), contracts, search)


def _tenant_configs() -> list[Config]:
    configs = []
    for root in TENANT_ROOTS:
        for package in sorted((REPO / root).iterdir()):
            manifest = package / "pyproject.toml"
            if not manifest.is_file():
                continue
            with manifest.open("rb") as handle:
                table = tomllib.load(handle).get("tool", {}).get("importlinter")
            if table is None:
                continue
            roots = _lines(table.get("root_packages", [])) or _lines(table.get("root_package", ""))
            configs.append(
                Config(
                    package.relative_to(REPO).as_posix(),
                    tuple(roots),
                    tuple(table.get("contracts", [])),
                    (package / "src", package),
                )
            )
    return configs


def _configs() -> list[Config]:
    found = [_root_config(), *_tenant_configs()]
    # A check that finds nothing to check proves nothing; if the discovery breaks, say so.
    assert len(found) > 1, "found no tenant import-linter configuration; the layout moved"
    return found


def _ids(config: Config) -> str:
    return config.where


def _overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(b + ".") or b.startswith(a + ".")


def _module_exists(module: str, search: tuple[Path, ...]) -> bool:
    relative = Path(*module.split("."))
    return any(
        (base / relative).with_suffix(".py").is_file()
        or (base / relative / "__init__.py").is_file()
        for base in search
    )


def _forbidden_contracts(config: Config) -> list[dict[str, Any]]:
    return [c for c in config.contracts if str(c.get("type", "")).strip() == "forbidden"]


@pytest.mark.parametrize("config", _configs(), ids=_ids)
def test_every_root_package_is_top_level(config: Config) -> None:
    assert config.roots, f"{config.where} names no root package"
    dotted = [root for root in config.roots if "." in root]
    assert not dotted, (
        f"{config.where} roots its graph at {dotted}. grimp raises NotATopLevelModule on a "
        "dotted root, so lint-imports exits before evaluating a single contract."
    )


@pytest.mark.parametrize("config", _configs(), ids=_ids)
def test_no_forbidden_module_overlaps_its_source(config: Config) -> None:
    dead = [
        f"{contract['name']}: {source} -> {forbidden}"
        for contract in _forbidden_contracts(config)
        for source in _lines(contract["source_modules"])
        for forbidden in _lines(contract["forbidden_modules"])
        if "*" not in forbidden and _overlaps(source, forbidden)
    ]
    assert not dead, (
        f"{config.where}: import-linter skips these pairs, so they forbid nothing: {dead}. "
        "Name the sibling modules instead of their shared parent."
    )


@pytest.mark.parametrize("config", _configs(), ids=_ids)
def test_every_forbidden_module_in_the_tree_exists(config: Config) -> None:
    missing = [
        f"{contract['name']}: {forbidden}"
        for contract in _forbidden_contracts(config)
        for forbidden in _lines(contract["forbidden_modules"])
        if "*" not in forbidden
        and any(_overlaps(forbidden, root) for root in config.roots)
        and not _module_exists(forbidden, config.search)
    ]
    assert not missing, (
        f"{config.where}: these forbidden modules are inside the graph's roots but do not "
        f"exist, and import-linter drops them without a word: {missing}"
    )
