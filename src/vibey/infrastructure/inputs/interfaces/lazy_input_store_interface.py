# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the lazily composed input store, beside its class (ADR-0016; SP-LOOPS Phase 3c,
fix round 1, review I4).

Mirrors `infrastructure/inputs/lazy_input_store.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.input_store_interface import InputStoreInterface


@runtime_checkable
class LazyInputStoreInterface(InputStoreInterface, Protocol):
    """`InputStoreInterface` over a store composed on its first use and kept: reading `[inputs]`
    and the store's credentials waits until a run, or a command, needs the store. A composition
    that fails raises from that first use (a `ConfigError`, say) and is tried again next time."""
