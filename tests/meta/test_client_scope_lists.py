# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every scope the hub defines is one the krypton clients can name (SP-ACP review B-10).

A host may offer a device any `HubScope`. The app's `HubScope` type and its `SCOPES` table, and
the desktop's scope descriptions, are written by hand in TypeScript and C, so a scope added to
`domain/hub_scope.py` and missed there would reach a pairing screen that cannot say what it is.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import re
from pathlib import Path

from vibey.domain.hub_scope import HubScope

REPO = Path(__file__).resolve().parents[2]
TS_TYPE = REPO / "clients" / "app" / "src" / "core" / "interfaces" / "hub-client-interface.ts"
TS_TABLE = REPO / "clients" / "app" / "src" / "core" / "hub-client.ts"
C_TABLE = REPO / "clients" / "desktop" / "src" / "core" / "kr-pairing.c"


def _ts_scope_type() -> set[str]:
    match = re.search(r"export type HubScope = ([^;]+);", TS_TYPE.read_text())
    assert match is not None, f"no HubScope type in {TS_TYPE}"
    return set(re.findall(r"'([a-z_]+)'", match.group(1)))


def _ts_scope_table() -> set[str]:
    match = re.search(r"static readonly SCOPES[^=]*= \{(.*?)\n  \};", TS_TABLE.read_text(), re.S)
    assert match is not None, f"no SCOPES table in {TS_TABLE}"
    return set(re.findall(r"^\s+([a-z_]+):", match.group(1), re.M))


def _c_scope_table() -> set[str]:
    match = re.search(r"SCOPES\[\] = \{(.*?)\n    \};", C_TABLE.read_text(), re.S)
    assert match is not None, f"no SCOPES table in {C_TABLE}"
    return set(re.findall(r'\{"([a-z_]+)",', match.group(1)))


def test_the_app_and_the_desktop_name_every_hub_scope() -> None:
    every = {scope.value for scope in HubScope}
    assert _ts_scope_type() == every
    assert _ts_scope_table() == every
    assert _c_scope_table() == every
