"""Application settings: constant defaults plus per-call overrides."""

from __future__ import annotations

import copy
from typing import Any

DEFAULTS: dict[str, Any] = {
    "theme": "light",
    "editor": {"tabs": 4, "wrap": True},
    "plugins": ["core"],
}


def load_settings(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the defaults with `overrides` applied on top."""
    merged = copy.deepcopy(DEFAULTS)
    for key, value in (overrides or {}).items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            current.update(copy.deepcopy(value))
        else:
            merged[key] = copy.deepcopy(value)
    return merged
