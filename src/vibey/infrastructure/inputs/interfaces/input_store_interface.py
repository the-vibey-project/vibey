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
    """`InputStoreInterface` on disk, under a root in the person's own state folder
    (`UserStateFolder.inputs()`), one folder per project id (0700): `objects/<digest[:2]>/
    <digest>` holds each input's bytes once (0600) and `index.jsonl` (0600) one JSON line per
    add. Every folder, read and write goes through `NoFollowFilesInterface`: a symlink is
    refused, never followed. No lock and no thread: the append is the commit."""
