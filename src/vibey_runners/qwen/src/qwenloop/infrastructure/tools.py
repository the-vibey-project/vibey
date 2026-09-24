# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Constrained local tool execution."""

import asyncio
import fnmatch
import json
import os
import re
import sys
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path

from qwenloop.domain.config import ToolLimits
from qwenloop.domain.model import CODING_TOOL_NAMES
from qwenloop.infrastructure.content_scanner import ContentScanner

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
# The directory holding the qwenloop package, so the isolated regex scanner imports the
# same qwenloop as this process without inheriting this process's environment.
_PACKAGE_ROOT = str(Path(__file__).resolve().parents[2])
_SCANNER_ENTRY = (
    "from qwenloop.infrastructure.content_scanner import ContentScanner; ContentScanner.run_stdio()"
)


class ShellEnvironment:
    """What a model-chosen shell command may see of this process's environment.

    An allow-list, never a copy with a few names removed: the shell tool used to pass
    everything but names containing KEY or TOKEN, so vibey's queue and ledger DSN
    (`VIBEY_PG_URL`), libpq's `PGPASSWORD` and any `*_SECRET` reached commands a model
    chose. Consistent with vibey's own engine environment (vibey ADR-0055): the system
    basics below, plus whatever the caller declares in `extra` -- and never vibey's own
    variables, libpq's, or anything shaped like a credential, whoever declares it.
    Declared by `interfaces/tools_interface.py`.
    """

    SYSTEM_NAMES: frozenset[str] = frozenset(
        {
            "PATH",
            "HOME",
            "USER",
            "LOGNAME",
            "SHELL",
            "TMPDIR",
            "TMP",
            "TEMP",
            "LANG",
            "LANGUAGE",
            "TZ",
            "TERM",
            "COLORTERM",
            "NO_COLOR",
            "COLUMNS",
            "LINES",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE",
            "NODE_EXTRA_CA_CERTS",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "no_proxy",
            "all_proxy",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "XDG_RUNTIME_DIR",
            "__CF_USER_TEXT_ENCODING",
        }
    )
    SYSTEM_PREFIXES: tuple[str, ...] = ("LC_",)
    FORBIDDEN_PREFIXES: tuple[str, ...] = ("VIBEY_", "PG")
    FORBIDDEN_MARKERS: tuple[str, ...] = (
        "KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "PASSWD",
        "CREDENTIAL",
        "DSN",
        "DATABASE_URL",
    )

    def __init__(
        self, source: Mapping[str, str] | None = None, *, extra: Iterable[str] = ()
    ) -> None:
        self._source = source
        self._extra = frozenset(extra)
        for name in self._extra:
            if self.forbids(name):
                raise ValueError(f"{name} can never be passed to a shell command")

    @classmethod
    def forbids(cls, name: str) -> bool:
        return name.startswith(cls.FORBIDDEN_PREFIXES) or any(
            marker in name for marker in cls.FORBIDDEN_MARKERS
        )

    def admits(self, name: str) -> bool:
        if self.forbids(name):
            return False
        return (
            name in self.SYSTEM_NAMES
            or name in self._extra
            or name.startswith(self.SYSTEM_PREFIXES)
        )

    def build(self) -> dict[str, str]:
        source = os.environ if self._source is None else self._source
        return {name: value for name, value in source.items() if self.admits(name)}


class SandboxTools:
    def __init__(
        self,
        worktree: Path,
        *,
        allow_network: bool = False,
        limits: ToolLimits | None = None,
        shell_environment: ShellEnvironment | None = None,
    ) -> None:
        self.worktree = worktree.resolve()
        self.allow_network = allow_network
        self.limits = limits or ToolLimits()
        self._shell_environment = shell_environment or ShellEnvironment()

    @property
    def tool_names(self) -> tuple[str, ...]:
        return CODING_TOOL_NAMES

    async def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        requested, name = name, self._canonical(name)
        if name in {"read_file", "open_file"}:
            return self._read(arguments)
        if name == "search":
            return await self._search(arguments)
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
            env = self._shell_environment.build()
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

    async def _search(self, arguments: Mapping[str, object]) -> dict[str, object]:
        """Lines matching a literal text (or, with regex=true, a pattern) under a path.

        A literal search is matched in-process. A regex is the model's own program, so it
        runs in a child interpreter killed at `search_timeout_seconds`: catastrophic
        backtracking costs one bounded call, never a worker thread.
        """
        query = self._first(arguments, _QUERY_KEYS)
        if not isinstance(query, str):
            return {
                "error": "search needs a query: the text to look for (a regular expression "
                "when regex is true)"
            }
        regex = self._flag(arguments.get("regex"))
        ignore_case = any(self._flag(arguments.get(key)) for key in _IGNORE_CASE_KEYS)
        pattern = query if regex else re.escape(query)
        flags = re.IGNORECASE if ignore_case else 0
        try:
            re.compile(pattern, flags)
        except re.error as exc:
            return {"error": f"invalid regex {query!r}: {exc}"}
        raw = str(self._first(arguments, _DIR_KEYS) or ".")
        base = self._path(raw)
        if not base.exists():
            return {"error": f"no such file or directory: {raw}"}
        glob = self._first(arguments, _GLOB_KEYS)
        candidates = await asyncio.to_thread(
            self._candidates, base, glob if isinstance(glob, str) else None
        )
        limit = self._requested_limit(arguments, self.limits.max_search_matches)
        if not regex:
            scanner = ContentScanner(
                max_file_bytes=self.limits.max_file_bytes,
                max_line_chars=self.limits.max_line_chars,
                max_skipped_examples=self.limits.max_skipped_examples,
            )
            return await asyncio.to_thread(scanner.scan, candidates, pattern, flags, limit)
        return await self._scan_isolated(
            {
                "candidates": candidates,
                "pattern": pattern,
                "flags": flags,
                "limit": limit,
                "max_file_bytes": self.limits.max_file_bytes,
                "max_line_chars": self.limits.max_line_chars,
                "max_skipped_examples": self.limits.max_skipped_examples,
            }
        )

    def _candidates(self, base: Path, glob: str | None) -> list[tuple[str, str]]:
        """(worktree-relative, absolute) paths of every confined file a search may read."""
        found: list[tuple[str, str]] = []
        for file in self._files(base):
            relative = file.relative_to(self.worktree).as_posix()
            if glob is None or self._glob_match(relative, glob):
                found.append((relative, str(file)))
        return found

    async def _scan_isolated(self, request: dict[str, object]) -> dict[str, object]:
        """Run ContentScanner in a child interpreter, killed at the search timeout. The
        child gets no environment beyond the path to qwenloop itself: no keys, no tokens."""
        timeout = self.limits.search_timeout_seconds
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                _SCANNER_ENTRY,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PYTHONPATH": _PACKAGE_ROOT},
                start_new_session=True,
            )
        except OSError as exc:
            return {"error": f"search failed: {exc}"}
        try:
            output, errors = await asyncio.wait_for(
                process.communicate(json.dumps(request).encode()), timeout=timeout
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return {
                "error": f"search timed out after {timeout}s; simplify the pattern (nested "
                "quantifiers such as (a+)+ backtrack without end) or search literally"
            }
        answer: object = None
        if process.returncode == 0:
            try:
                answer = json.loads(output)
            except json.JSONDecodeError:
                answer = None
        if not isinstance(answer, dict):
            detail = errors.decode(errors="replace").strip()[-500:] or "no result"
            return {"error": f"search failed: {detail}"}
        return answer

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
