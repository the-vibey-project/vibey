# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The artifact classes each forge's API exposes, held as data the capture is accounted against.

`forge-snapshot` says which classes it reads and which it declines. Whether those two lists
cover what a forge offers is a different claim, and it needs a list that did not come from the
capture itself (vibey#1571). That list is `data/forge-api-classes.json`: for each forge, every
repository-scoped group its API description publishes, mapped to the forge-neutral class it
belongs to. Two forges name the same artifact differently (GitHub's `releases/assets`, a
Forgejo release's attachments), so the neutral name is what the two share.

A forge whose list was not read in full says so with `verified: false`, and the manifest
repeats it: an inventory written from memory is evidence of nothing but the attempt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vibey_gh.forge_snapshot import digest
from vibey_gh.interfaces.forge_snapshot_interface import ForgeInventoryInterface

__all__ = ["INVENTORY_PATH", "INVENTORY_SCHEMA", "JsonForgeInventory"]

INVENTORY_SCHEMA = "vibey.forge-api-classes/1"
# Shipped inside the package so an installed `vibey-gh` can account for a capture without the
# repository's docs beside it.
INVENTORY_PATH = Path(__file__).parent / "data" / "forge-api-classes.json"


class JsonForgeInventory(ForgeInventoryInterface):
    def __init__(self, path: Path = INVENTORY_PATH) -> None:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("schema") != INVENTORY_SCHEMA:
            raise ValueError(f"{path} is not a {INVENTORY_SCHEMA} inventory")
        forges = document.get("forges")
        if not isinstance(forges, dict) or not forges:
            raise ValueError(f"{path} inventories no forge")
        self._classes = {name: self._read(path, name, forge) for name, forge in forges.items()}
        self._verified = {name: forge.get("verified") is True for name, forge in forges.items()}
        self._sha256 = digest(document)

    @property
    def sha256(self) -> str:
        return self._sha256

    def classes(self, forge: str) -> tuple[str, ...] | None:
        return self._classes.get(forge)

    def verified(self, forge: str) -> bool:
        return self._verified.get(forge, False)

    @staticmethod
    def _read(path: Path, name: str, forge: Any) -> tuple[str, ...]:
        entries = forge.get("entries") if isinstance(forge, dict) else None
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{path}: {name} lists no entries")
        natives: list[str] = []
        neutral: set[str] = set()
        for entry in entries:
            native = entry.get("native") if isinstance(entry, dict) else None
            forge_class = entry.get("class") if isinstance(entry, dict) else None
            if not (
                isinstance(native, str) and native and isinstance(forge_class, str) and forge_class
            ):
                raise ValueError(f"{path}: {name} has an entry without a native and a class")
            natives.append(native)
            neutral.add(forge_class)
        if len(set(natives)) != len(natives):
            raise ValueError(f"{path}: {name} names a native group twice")
        return tuple(sorted(neutral))
