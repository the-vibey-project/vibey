# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Constrained local tool execution."""

import asyncio
import fnmatch
import os
import re
from collections.abc import Iterator, Mapping
from pathlib import Path

from qwenloop.domain.config import ToolLimits
from qwenloop.domain.model import CODING_TOOL_NAMES

# The argument names a model uses for the same thing, first match wins. The canonical
# name (first in each tuple) is the one the tool schema advertises; the rest are the
# spellings of tools gpt-oss was trained on (its harmony `browser` and `repo_browser`
# tools: `query`/`topn`, `pattern`, `line_start`/`line_end`, `loc`/`num_lines`) and of
# grep- and editor-shaped tools. Accepting them costs nothing; refusing them costs a turn.
_QUERY_KEYS = ("query", "pattern", "text", "q", "term", "keyword", "search")
_DIR_KEYS = ("path", "dir", "directory", "root")
_GLOB_KEYS = ("glob", "include", "file_pattern", "files")
_IGNORE_CASE_KEYS = ("ignore_case", "case_insensitive")
_LIMIT_KEYS = ("max_results", "limit", "topn", "max_matches")
_FIND_KEYS = ("pattern", "name", "glob", "query", "filename", "file")
_FILE_KEYS = ("path", "file", "filename", "file_path")
_LINE_START_KEYS = ("line_start", "start_line", "start", "line", "loc", "offset")
_LINE_END_KEYS = ("line_end", "end_line", "end")
_LINE_COUNT_KEYS = ("num_lines", "limit")
_GLOB_CHARACTERS = frozenset("*?[")


class SandboxTools:
    def __init__(
        self, worktree: Path, *, allow_network: bool = False, limits: ToolLimits | None = None
    ) -> None:
        self.worktree = worktree.resolve()
        self.allow_network = allow_network
        self.limits = limits or ToolLimits()

    @property
    def tool_names(self) -> tuple[str, ...]:
        return CODING_TOOL_NAMES

    async def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        requested, name = name, self._canonical(name)
        if name in {"read_file", "open_file"}:
            return self._read(arguments)
        if name == "search":
            return await asyncio.to_thread(self._search, arguments)
        if name == "find":
            return await asyncio.to_thread(self._find, arguments)
        if name == "write_file":
            path = self._path(str(arguments.get("path", "")))
            content = str(arguments.get("content", ""))
            refusal = self._shrink_refusal(path, content, arguments.get("allow_shrink") is True)
            if refusal is not None:
                return {"error": refusal}
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            except OSError as exc:
                return {"error": str(exc)}
            return {"written": len(content)}
        if name == "edit_file":
            return self._edit(arguments)
        if name == "shell":
            argv = arguments.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                return {"error": "argv must be a non-empty string list"}
            if argv[0] in {"sudo", "rm", "shutdown", "reboot"}:
                return {"error": "command denied by policy"}
            env = {
                key: value
                for key, value in os.environ.items()
                if "KEY" not in key and "TOKEN" not in key
            }
            if not self.allow_network:
                env["QWENLOOP_NETWORK"] = "disabled"
            try:
                process = await asyncio.create_subprocess_exec(
                    *argv,
                    cwd=self.worktree,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as exc:
                return {"error": str(exc)}
            try:
                output, _ = await asyncio.wait_for(process.communicate(), timeout=120)
            except TimeoutError:
                process.kill()
                await process.wait()
                return {"error": "command timed out"}
            return {
                "exit_code": process.returncode,
                "output": output.decode(errors="replace")[-100_000:],
            }
        return {
            "error": f"unknown tool {requested!r}; available tools: {', '.join(self.tool_names)}"
        }

    def _canonical(self, name: str) -> str:
        """The tool a call names. A namespaced name resolves to its last segment when that
        is a tool: gpt-oss's harmony template addresses tools as `repo_browser.open_file`
        or `functions.read_file`, and Ollama has been seen passing the prefix through."""
        if name in self.tool_names:
            return name
        bare = name.rpartition(".")[2]
        return bare if bare in self.tool_names else name

    def _read(self, arguments: Mapping[str, object]) -> dict[str, object]:
        """read_file, and open_file, its alias: a whole file, or the lines a range names.

        Without a range the answer is exactly what read_file always returned. A range is
        1-based and inclusive, clamped to the file, and may be given as a start and an
        end, or as a start and a line count.
        """
        path = self._path(str(self._first(arguments, _FILE_KEYS) or ""))
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return {"error": str(exc)}
        try:
            start = self._integer(self._first(arguments, _LINE_START_KEYS))
            end = self._integer(self._first(arguments, _LINE_END_KEYS))
            count = self._integer(self._first(arguments, _LINE_COUNT_KEYS))
        except ValueError as exc:
            return {"error": f"line numbers must be integers: {exc}"}
        if start is None and end is None and count is None:
            return {"content": text[: self.limits.max_read_chars]}
        lines = text.splitlines(keepends=True)
        first = max(1, start or 1)
        if end is None and count is not None:
            end = first + count - 1
        last = len(lines) if end is None else min(end, len(lines))
        return {
            "content": "".join(lines[first - 1 : last])[: self.limits.max_read_chars],
            "line_start": first,
            "line_end": last,
            "total_lines": len(lines),
        }

    def _search(self, arguments: Mapping[str, object]) -> dict[str, object]:
        """Lines matching a literal text (or, with regex=true, a pattern) under a path."""
        query = self._first(arguments, _QUERY_KEYS)
        if not isinstance(query, str):
            return {
                "error": "search needs a query: the text to look for (a regular expression "
                "when regex is true)"
            }
        ignore_case = any(self._flag(arguments.get(key)) for key in _IGNORE_CASE_KEYS)
        source = query if self._flag(arguments.get("regex")) else re.escape(query)
        try:
            matcher = re.compile(source, re.IGNORECASE if ignore_case else 0)
        except re.error as exc:
            return {"error": f"invalid regex {query!r}: {exc}"}
        raw = str(self._first(arguments, _DIR_KEYS) or ".")
        base = self._path(raw)
        if not base.exists():
            return {"error": f"no such file or directory: {raw}"}
        glob = self._first(arguments, _GLOB_KEYS)
        limit = self._requested_limit(arguments, self.limits.max_search_matches)
        matches: list[str] = []
        for file in self._files(base):
            relative = file.relative_to(self.worktree).as_posix()
            if isinstance(glob, str) and not self._glob_match(relative, glob):
                continue
            text = self._searchable_text(file)
            if text is None:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if not matcher.search(line):
                    continue
                if len(matches) == limit:
                    return {"matches": matches, "count": len(matches), "truncated": True}
                matches.append(f"{relative}:{number}: {self._clip(line)}")
        return {"matches": matches, "count": len(matches), "truncated": False}

    def _find(self, arguments: Mapping[str, object]) -> dict[str, object]:
        """File paths under a path whose name matches: a glob when the pattern has glob
        characters, otherwise a case-insensitive substring. An empty pattern lists all."""
        pattern = self._first(arguments, _FIND_KEYS)
        text = pattern if isinstance(pattern, str) else ""
        raw = str(self._first(arguments, _DIR_KEYS) or ".")
        base = self._path(raw)
        if not base.exists():
            return {"error": f"no such file or directory: {raw}"}
        limit = self._requested_limit(arguments, self.limits.max_find_results)
        is_glob = not _GLOB_CHARACTERS.isdisjoint(text)
        found: list[str] = []
        for file in self._files(base):
            relative = file.relative_to(self.worktree).as_posix()
            hit = self._glob_match(relative, text) if is_glob else text.lower() in relative.lower()
            if not hit:
                continue
            if len(found) == limit:
                return {"files": found, "count": len(found), "truncated": True}
            found.append(relative)
        return {"files": found, "count": len(found), "truncated": False}

    def _files(self, base: Path) -> Iterator[Path]:
        """Every file under `base`, in a stable order, that resolves inside the worktree.

        Symlinked directories are not followed and a symlinked file that resolves outside
        the worktree is skipped: the same confinement `_path` enforces on a named path.
        """
        if base.is_file():
            yield base
            return
        for root, dirs, names in os.walk(base):
            dirs[:] = sorted(item for item in dirs if item not in self.limits.skip_dirs)
            for name in sorted(names):
                candidate = Path(root) / name
                if self._contains(candidate.resolve()):
                    yield candidate

    def _searchable_text(self, file: Path) -> str | None:
        """A file's text, or None for one too large, binary, undecodable or unreadable."""
        try:
            if file.stat().st_size > self.limits.max_file_bytes:
                return None
            data = file.read_bytes()
        except OSError:
            return None
        if b"\0" in data:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _clip(self, line: str) -> str:
        limit = self.limits.max_line_chars
        return line if len(line) <= limit else f"{line[:limit]}…"

    @staticmethod
    def _glob_match(relative: str, pattern: str) -> bool:
        return fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(
            relative.rpartition("/")[2], pattern
        )

    @staticmethod
    def _first(arguments: Mapping[str, object], keys: tuple[str, ...]) -> object:
        """The first of `keys` the call set to something other than null or empty."""
        for key in keys:
            value = arguments.get(key)
            if value is not None and value != "":
                return value
        return None

    @staticmethod
    def _flag(value: object) -> bool:
        return value is True or (isinstance(value, str) and value.strip().lower() == "true")

    @staticmethod
    def _integer(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
        raise ValueError(f"expected an integer, got {value!r}")

    def _requested_limit(self, arguments: Mapping[str, object], ceiling: int) -> int:
        """The model's own result limit when it is a positive integer below `ceiling`:
        a call may narrow the configured bound, never widen it."""
        raw = self._first(arguments, _LIMIT_KEYS)
        try:
            requested = self._integer(raw) or 0
        except ValueError:
            requested = 0
        return min(requested, ceiling) if requested > 0 else ceiling

    def _edit(self, arguments: dict[str, object]) -> dict[str, object]:
        """Replace exactly one occurrence of `old_string` in an existing file.

        The targeted alternative to write_file: a small model cannot reproduce a long file
        byte for byte, and a whole-file rewrite that drops lines is the failure this exists
        to prevent (#346).
        """
        raw = str(arguments.get("path", ""))
        old = str(arguments.get("old_string", ""))
        new = str(arguments.get("new_string", ""))
        path = self._path(raw)
        if not old:
            return {"error": "old_string must not be empty; use write_file to create a file"}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return {"error": f"cannot edit {raw}: {exc}; use write_file to create a new file"}
        count = text.count(old)
        if count == 0:
            return {
                "error": f"old_string not found in {raw}; read the file again and copy the text exactly"
            }
        if count > 1:
            return {
                "error": f"old_string matches {count} times in {raw}; include more surrounding lines"
            }
        try:
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
        except OSError as exc:
            return {"error": str(exc)}
        return {"replaced": 1, "path": raw}

    @staticmethod
    def _shrink_refusal(path: Path, content: str, allowed: bool) -> str | None:
        """Why a write would gut an existing file, or None when it may proceed."""
        if allowed or not path.is_file():
            return None
        try:
            before = path.read_text(encoding="utf-8").count("\n")
        except (OSError, UnicodeDecodeError):
            return None
        after = content.count("\n")
        if before < 40 or after * 2 >= before:
            return None
        return (
            f"write_file would remove {before - after} of {before} lines from {path.name}; use "
            "edit_file for a targeted change, or pass allow_shrink=true to replace the file"
        )

    def _path(self, raw: str) -> Path:
        target = (self.worktree / raw).resolve()
        if not self._contains(target):
            raise ValueError("path escapes the worktree")
        return target

    def _contains(self, target: Path) -> bool:
        """Whether a resolved path is the worktree or inside it."""
        return target == self.worktree or self.worktree in target.parents
