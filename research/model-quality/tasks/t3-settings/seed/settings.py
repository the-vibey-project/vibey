"""Application settings: constant defaults plus per-call overrides."""

from __future__ import annotations

from typing import Any

DEFAULTS: dict[str, Any] = {
    "theme": "light",
    "editor": {"tabs": 4, "wrap": True},
    "plugins": ["core"],
}


def load_settings(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the defaults with `overrides` applied on top."""
    merged = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            current.update(value)
        else:
            merged[key] = value
    return merged
