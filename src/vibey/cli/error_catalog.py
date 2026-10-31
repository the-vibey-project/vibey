# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey's error codes: one declared table, read by `Error:` output, `vibey explain` and the docs.

`error_codes.toml` holds an entry per exception class: a permanent code, a title, the cause
and what to do about it. `render` looks the raised type up here, `vibey explain CODE` prints
the entry, and `docs/reference/errors.md` is generated from it, so the three cannot disagree
(sub-doctrine 12.e). It is data, not attributes on the exception classes, so the pure domain
layer carries no presentation (ADR-0051, sub-doctrine 12.h).

A code is permanent: assigned once, in order, never reused or renumbered. The table is checked
when it loads, and a malformed one raises `ValueError` naming the entry.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from functools import cache
from importlib import resources
from typing import Any

from vibey.cli.interfaces.error_catalog_interface import ErrorCatalogInterface, ErrorEntry

__all__ = ["ErrorCatalog", "ErrorEntry"]

_CODE = re.compile(r"E\d{4}")


class ErrorCatalog(ErrorCatalogInterface):
    """Implements `ErrorCatalogInterface` over a validated table."""

    def __init__(self, entries: Sequence[ErrorEntry]) -> None:
        by_code: dict[str, ErrorEntry] = {}
        by_name: dict[str, ErrorEntry] = {}
        for entry in entries:
            self._validate(entry)
            if entry.qualname in by_name:
                raise ValueError(f"error catalog: {entry.qualname} is listed twice")
            by_name[entry.qualname] = entry
            if entry.code is not None:
                if entry.code in by_code:
                    raise ValueError(f"error catalog: code {entry.code} is used twice")
                by_code[entry.code] = entry
        self._entries = tuple(entries)
        self._by_code = by_code
        self._by_name = by_name

    @staticmethod
    def _validate(entry: ErrorEntry) -> None:
        name = entry.qualname
        if entry.abstract:
            if entry.code is not None:
                raise ValueError(f"error catalog: {name} is abstract and so has no code")
        elif entry.code is None or not _CODE.fullmatch(entry.code):
            raise ValueError(f"error catalog: {name} needs a code of the form E0001")
        elif not entry.cause.strip() or not entry.fix.strip():
            raise ValueError(f"error catalog: {entry.code} ({name}) needs a cause and a fix")
        if not entry.title.strip():
            raise ValueError(f"error catalog: {name} needs a title")

    @classmethod
    def from_toml(cls, text: str) -> ErrorCatalog:
        """The catalog a TOML document declares: an `[[error]]` table per entry."""
        rows: Sequence[Mapping[str, Any]] = tomllib.loads(text).get("error", ())
        try:
            return cls(
                [
                    ErrorEntry(
                        qualname=row["class"],
                        title=row["title"],
                        cause=row["cause"],
                        fix=row.get("fix", ""),
                        code=row.get("code"),
                        abstract=row.get("abstract", False),
                        retired=row.get("retired", False),
                    )
                    for row in rows
                ]
            )
        except KeyError as exc:
            raise ValueError(f"error catalog: an entry has no {exc.args[0]!r}") from None

    @classmethod
    @cache
    def shipped(cls) -> ErrorCatalog:
        """The table that ships in the wheel (`error_codes.toml`), read once."""
        text = resources.files("vibey.cli").joinpath("error_codes.toml").read_text("utf-8")
        return cls.from_toml(text)

    def entries(self) -> Sequence[ErrorEntry]:
        return self._entries

    def entry_for(self, exc_type: type[BaseException]) -> ErrorEntry | None:
        return self._by_name.get(f"{exc_type.__module__}.{exc_type.__qualname__}")

    def by_code(self, code: str) -> ErrorEntry | None:
        return self._by_code.get(code.strip().upper())
