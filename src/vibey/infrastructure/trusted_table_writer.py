# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes one table of the person's own `vibey.toml` and nothing else (SP-LOOPS Task 7).

vibey had a trusted-config reader (`TomlTrustedTableReader`, ADR-0101) but no writer: until the
`vibey loops marketplace | plugin | mcp` commands nothing changed a `vibey.toml`. This is the one
writer, kept small, for any table a command owns:

- **Only the table changes.** The file is scanned the way TOML reads it -- strings (all four
  kinds), comments, arrays and inline tables -- to find every header of the table and of its
  sub-tables (`[loops]`, `[[loops.marketplaces]]`, however spelt: `[ "loops" ]` is the same
  table). Those lines are replaced by the table rendered afresh, at the place the first of them
  stood (at the end of the file when there were none); every other byte is kept as it was.
  Comments and blank lines after the table's last key belong to what follows and are kept.
- **Nothing is lost silently.** A comment inside the table would be dropped by a rewrite, so the
  write is refused instead (`ConfigError`), as `vibey connect` refuses a commented settings file.
  The result is parsed before it is written and must hold exactly the new table and, apart from
  it, exactly what the file held: a table spelt as dotted keys or inline, or anything else the
  scan did not see, is refused with nothing written. Either refusal tells the person to edit the
  file by hand; `render_table` gives the text to paste.
- **Written the way a secret-bearing file is.** The new text goes to a temporary file beside the
  real one (0600 from the moment it exists), is fsynced and renamed over it, and the folder is
  fsynced; a failure removes the temporary file and leaves the old one. The file ends 0600
  whatever it was, and a missing folder is made 0700. A symlinked `vibey.toml` (dotfiles) is
  written where it points and stays a link: the link is the person's choice.

Values are what TOML holds exactly and `tomllib` gives back: strings, booleans, integers, lists
and tables. Anything else is refused. Declared by
`interfaces/trusted_table_writer_interface.py::TrustedTableWriterInterface`.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from vibey.domain.config import ConfigError
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

_BARE_KEY: Final = re.compile(r"[A-Za-z0-9_-]+")
_ESCAPES: Final = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}
_STRING: Final = re.compile(
    r'"""(?:[^"\\]|\\.|"{1,2}(?!"))*"{3,5}'
    r"|'''(?:[^']|'{1,2}(?!'))*'{3,5}"
    r'|"(?:[^"\\\n]|\\.)*"'
    r"|'[^'\n]*'",
    re.DOTALL,
)
"""TOML's four string kinds, multi-line first."""
_HAND_EDIT: Final = "edit it by hand (`vibey loops` prints the table to paste when it refuses)"


@dataclass(slots=True)
class _Scan:
    """What one pass over a TOML text found, by line: each table header (its line and its first
    key), the lines holding a comment, and the lines holding anything but space and comments."""

    headers: list[tuple[int, str]] = field(default_factory=list)
    comments: set[int] = field(default_factory=set)
    content: set[int] = field(default_factory=set)


class TomlTrustedTableWriter:
    """Declared by `interfaces/trusted_table_writer_interface.py::TrustedTableWriterInterface`."""

    def __init__(
        self,
        reader: TomlTrustedTableReader | None = None,
        fsync: Callable[[int], None] = os.fsync,
    ) -> None:
        self._reader = reader or TomlTrustedTableReader()
        self._fsync = fsync

    def write_table(self, path: Path, table: str, values: Mapping[str, object]) -> None:
        block = self._render(path, table, values)
        text = self._reader.read_text(path) or ""
        before = self._reader.parse(path, text)
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        spans = self._spans(path, table, lines)
        if spans:
            start = spans[0][0]
            kept = [line for index, line in enumerate(lines) if not self._inside(index, spans)]
            at = sum(1 for index in range(start) if not self._inside(index, spans))
            new = "".join([*kept[:at], block, *kept[at:]])
        else:
            gap = "\n" if lines else ""
            new = "".join([*lines, gap, block])
        self._check(path, table, values, before, new)
        self._replace(path, new.encode("utf-8"))

    def render_table(self, table: str, values: Mapping[str, object]) -> str:
        return self._render(Path(table), table, values)

    # -- finding the table -------------------------------------------------------------------

    def _spans(self, path: Path, table: str, lines: Sequence[str]) -> list[tuple[int, int]]:
        """The line ranges `[start, end)` the table's headers own, each ending after its last
        line of content; refuses a comment inside one."""
        scan = self._scan("".join(lines))
        bounds = [line for line, _ in scan.headers] + [len(lines)]
        spans: list[tuple[int, int]] = []
        for (start, key), following in zip(scan.headers, bounds[1:], strict=True):
            if key != table:
                continue
            end = max(line for line in range(start, following) if line in scan.content) + 1
            if any(start <= line < end for line in scan.comments):
                raise ConfigError(
                    str(path),
                    f"holds comments inside [{table}], which a rewrite would drop; vibey changes "
                    f"nothing: {_HAND_EDIT}",
                )
            spans.append((start, end))
        return spans

    @staticmethod
    def _inside(index: int, spans: Sequence[tuple[int, int]]) -> bool:
        return any(start <= index < end for start, end in spans)

    def _scan(self, text: str) -> _Scan:
        scan = _Scan()
        index, line, depth, line_start = 0, 0, 0, True
        while index < len(text):
            char = text[index]
            if char == "\n":
                index, line, line_start = index + 1, line + 1, True
            elif char in " \t\r":
                index += 1
            elif char == "#":
                scan.comments.add(line)
                end = text.find("\n", index)
                index = len(text) if end < 0 else end
            elif char == "[" and line_start and depth == 0:
                key, index = self._header(text, index)
                scan.headers.append((line, key))
                scan.content.add(line)
                line_start = False
            else:
                scan.content.add(line)
                line_start = False
                if char in "\"'":
                    end = self._string_end(text, index)
                    for _ in range(text.count("\n", index, end)):
                        line += 1
                        scan.content.add(line)
                    index = end
                else:
                    depth += 1 if char in "[{" else -1 if char in "]}" and depth else 0
                    index += 1
        return scan

    def _header(self, text: str, index: int) -> tuple[str, int]:
        """The first key of the header at `index` and where the header ends (after `]` or
        `]]`; at the end of the line for a header that is not closed)."""
        index += 2 if text.startswith("[[", index) else 1
        first: str | None = None
        while index < len(text) and text[index] not in "]\n":
            char = text[index]
            if char in "\"'":
                end = self._string_end(text, index)
                key = self._unquote(text[index:end])
                index = end
            elif char in " \t.":
                index += 1
                continue
            else:
                match = _BARE_KEY.match(text, index)
                key = match.group() if match else char
                index = match.end() if match else index + 1
            first = key if first is None else first
        while index < len(text) and text[index] == "]":
            index += 1
        return first or "", index

    @staticmethod
    def _unquote(quoted: str) -> str:
        """A quoted key's text: what a literal key holds, or a basic key's escapes undone for
        the two that matter to a name (`\\"` and `\\\\`); a key spelt any stranger way is
        compared as spelt, and the parse check after the rewrite catches what that misses."""
        inner = quoted[1:-1] if len(quoted) >= 2 and quoted[-1] == quoted[0] else quoted[1:]
        if quoted.startswith("'"):
            return inner
        return inner.replace('\\"', '"').replace("\\\\", "\\")

    @staticmethod
    def _string_end(text: str, index: int) -> int:
        """One past the end of the string that starts at `index` (any of TOML's four kinds; a
        multi-line one may end in up to two extra quotes, which are its content). The text was
        parsed as TOML before it is scanned, so every string is closed."""
        match = _STRING.match(text, index)
        return match.end() if match else len(text)

    # -- checking and writing ----------------------------------------------------------------

    def _check(
        self,
        path: Path,
        table: str,
        values: Mapping[str, object],
        before: Mapping[str, object],
        new: str,
    ) -> None:
        try:
            after = self._reader.parse(path, new)
        except ConfigError as exc:
            raise ConfigError(
                str(path), f"[{table}] cannot be rewritten exactly ({exc}); {_HAND_EDIT}"
            ) from exc
        others = {key: value for key, value in before.items() if key != table}
        rest = {key: value for key, value in after.items() if key != table}
        if after.get(table) != self._plain(values) or rest != others:
            raise ConfigError(
                str(path),
                f"[{table}] is spelt in a way vibey cannot rewrite exactly (dotted keys or an "
                f"inline table); {_HAND_EDIT}",
            )

    def _plain(self, value: object) -> object:
        """`value` as `tomllib` gives it back: tuples as lists, mappings as dicts."""
        if isinstance(value, Mapping):
            return {str(key): self._plain(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [self._plain(item) for item in value]
        return value

    def _replace(self, path: Path, data: bytes) -> None:
        real = Path(os.path.realpath(path))  # a symlinked config: written where it points
        try:
            real.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                dir=real.parent, prefix=f".{real.name}.", suffix=".tmp"
            )
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    os.fchmod(handle.fileno(), 0o600)
                    handle.write(data)
                    handle.flush()
                    self._fsync(handle.fileno())
                os.replace(temporary, real)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
            folder = os.open(real.parent, os.O_RDONLY)
            try:
                self._fsync(folder)
            finally:
                os.close(folder)
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be written: {exc}") from exc

    # -- rendering ---------------------------------------------------------------------------

    def _render(self, path: Path, table: str, values: Mapping[str, object]) -> str:
        try:
            return "\n".join(self._table([table], values, double=False)) + "\n"
        except TypeError as exc:
            raise ConfigError(str(path), f"[{table}] cannot be written: {exc}") from exc

    def _table(self, keys: list[str], values: Mapping[str, object], *, double: bool) -> list[str]:
        header = ".".join(self._key(key) for key in keys)
        lines = [f"[[{header}]]" if double else f"[{header}]"]
        later: list[str] = []
        for key, value in values.items():
            if isinstance(value, Mapping):
                later += ["", *self._table([*keys, key], value, double=False)]
            elif self._rows(value):
                for row in value:  # type: ignore[attr-defined]  # a list of mappings: _rows
                    later += ["", *self._table([*keys, key], row, double=True)]
            else:
                lines.append(f"{self._key(key)} = {self._value(value)}")
        return lines + later

    @staticmethod
    def _rows(value: object) -> bool:
        """Whether `value` is an array of tables: a non-empty list whose every item is a
        mapping, rendered as `[[...]]` blocks."""
        return (
            isinstance(value, list | tuple)
            and bool(value)
            and all(isinstance(item, Mapping) for item in value)
        )

    def _key(self, key: str) -> str:
        return key if _BARE_KEY.fullmatch(key) else self._string(key)

    def _value(self, value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return self._string(value)
        if isinstance(value, list | tuple):
            return "[" + ", ".join(self._value(item) for item in value) + "]"
        if isinstance(value, Mapping):
            pairs = (f"{self._key(str(k))} = {self._value(v)}" for k, v in value.items())
            return "{ " + ", ".join(pairs) + " }"
        raise TypeError(f"a value of type {type(value).__name__} is not one TOML holds exactly")

    @staticmethod
    def _string(text: str) -> str:
        out = ['"']
        for char in text:
            code = ord(char)
            if 0xD800 <= code <= 0xDFFF:
                raise TypeError("a string holding a lone surrogate is not one TOML holds")
            if char in _ESCAPES:
                out.append(_ESCAPES[char])
            elif code < 0x20 or code == 0x7F:
                out.append(f"\\u{code:04x}")
            else:
                out.append(char)
        out.append('"')
        return "".join(out)
