# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the hash-addressed input store, beside its class (ADR-0016).

Mirrors `infrastructure/inputs/hash_addressed_input_store.py`. The runtime seam the run inputs
service consumes is `application/interfaces/input_store_interface.py::InputStoreInterface`; it
is restated here with what the on-disk store promises about its layout. Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.input_store_interface import InputStoreInterface


@runtime_checkable
class HashAddressedInputStoreInterface(InputStoreInterface, Protocol):
    """`InputStoreInterface` on disk. Under `project_folder / "inputs"` (0700):
    `objects/<digest[:2]>/<digest>` holds each input's bytes once (0600, written to a temporary
    name, synced, then renamed into place), and `index.jsonl` (0600) one JSON line per add,
    appended with a single `O_APPEND` write and synced. A symlink or other non-regular file
    where the store keeps its own is refused, never followed. No lock and no thread: the append
    is the commit."""
