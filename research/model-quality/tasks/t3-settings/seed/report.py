"""A one-line summary of the active settings."""

from __future__ import annotations

from typing import Any

from settings import load_settings


def summary(overrides: dict[str, Any] | None = None) -> str:
    cfg = load_settings(overrides)
    plugins = ",".join(cfg["plugins"])
    return f"theme={cfg['theme']} tabs={cfg['editor']['tabs']} plugins={plugins}"
