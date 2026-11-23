# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run input: one pasted text or one file a person gives every BUILD run of a project
(SP-LOOPS Phase 3; design Goal 4 and Decision 6).

A run input is stored once under its digest, the lowercase hex SHA-256 of its bytes, and the
ledger records that digest, its kind and its size, never its content. Its name is what a run
sees it as (the file's base name; `paste` for a paste), so a name is held to one path segment:
not empty, not `.` or `..`, no `/`, `\\` or NUL, writable as UTF-8 and at most `NAME_MAX_BYTES`
UTF-8 bytes. Any other character, a control character included, is allowed and escaped wherever
it is shown.

Pure: no I/O. Declared by `interfaces/run_input_interface.py::RunInputRuleInterface`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Final, Literal

from vibey.domain.interfaces.run_input_interface import RunInputRuleInterface

InputKind = Literal["paste", "file"]
INPUT_KINDS: Final[tuple[InputKind, ...]] = ("paste", "file")
NAME_MAX_BYTES: Final = 255
"""The longest a run input's name may be, in UTF-8 bytes: the common file-name limit."""
_DIGEST: Final = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class RunInput:
    """One stored run input as the index records it: no content."""

    digest: str
    kind: InputKind
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class InputListing:
    """A project's run inputs in the order they were added, and how many index lines could not
    be read (a torn last line after a crash, say) and were skipped rather than raised."""

    items: tuple[RunInput, ...]
    skipped: int


class RunInputRule:
    """Declared by `interfaces/run_input_interface.py::RunInputRuleInterface`."""

    def digest_of(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def valid_name(self, name: str, *, max_bytes: int = NAME_MAX_BYTES) -> str | None:
        if not name:
            return "is empty"
        if name in {".", ".."}:
            return f"{name!r} names a folder, not a file"
        if "/" in name or "\\" in name:
            return "contains a path separator"
        if "\x00" in name:
            return "contains a NUL"
        try:
            size = len(name.encode("utf-8"))
        except UnicodeEncodeError:
            return "is not text that can be written as UTF-8"
        if size > max_bytes:
            return f"is {size} bytes long; at most {max_bytes} are allowed"
        return None

    def is_digest(self, text: str) -> bool:
        return _DIGEST.fullmatch(text) is not None


RUN_INPUT_RULE: Final[RunInputRuleInterface] = RunInputRule()
"""The one rule. Annotated with the interface so `mypy --strict` checks the class against it."""
digest_of: Final = RUN_INPUT_RULE.digest_of
"""`RUN_INPUT_RULE.digest_of`, under the name the run input plan gives it."""
valid_name: Final = RUN_INPUT_RULE.valid_name
"""`RUN_INPUT_RULE.valid_name`, under the name the run input plan gives it."""
