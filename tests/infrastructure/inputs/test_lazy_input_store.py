# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The run input store composed on its first use (SP-LOOPS Phase 3c, fix round 1: review I4).
Module-level test functions (ADR-0016 is about production code)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.interfaces.input_store_interface import InputStoreInterface
from vibey.domain.config import ConfigError
from vibey.infrastructure.inputs.hash_addressed_input_store import HashAddressedInputStore
from vibey.infrastructure.inputs.interfaces.lazy_input_store_interface import (
    LazyInputStoreInterface,
)
from vibey.infrastructure.inputs.lazy_input_store import LazyInputStore


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 23, tzinfo=UTC)


def test_nothing_is_composed_until_a_store_call_and_then_only_once(tmp_path: Path) -> None:
    made: list[int] = []

    def compose() -> InputStoreInterface:
        made.append(1)
        return HashAddressedInputStore(tmp_path / "inputs", _Clock())

    store = LazyInputStore(compose)
    assert isinstance(store, LazyInputStoreInterface)
    assert made == []
    project = uuid4()
    item = store.put(project, "paste", "paste", b"words")
    assert store.listed(project).items == (item,)
    assert store.get(project, item.digest, size=item.size) == b"words"
    assert store.restore(project, b"words") == item.digest
    assert store.describe() == f"local store at {tmp_path / 'inputs'}"
    assert made == [1]


def test_a_composition_that_fails_raises_from_that_use_and_is_tried_again(tmp_path: Path) -> None:
    attempts: list[int] = []

    def compose() -> InputStoreInterface:
        attempts.append(1)
        if len(attempts) == 1:
            raise ConfigError("/home/p/vibey.toml", "VIBEY_INPUTS_SECRET_KEY is not set")
        return HashAddressedInputStore(tmp_path / "inputs", _Clock())

    store = LazyInputStore(compose)
    with pytest.raises(ConfigError, match="is not set"):
        store.listed(uuid4())
    assert store.listed(uuid4()).items == ()
    assert len(attempts) == 2
