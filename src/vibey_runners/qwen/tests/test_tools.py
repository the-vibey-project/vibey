# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tools a local model reaches for by name: search, find and open_file.

Across 82 QwenStorm 3.0.0 runs gpt-oss:20b called `search` 401 times, `find` 22 times and
`open_file` 8 times, all answered "unknown tool". These tests pin the tools that now answer
those calls, the confinement they share with read_file, and the bounds they obey.
"""

from pathlib import Path

import pytest

from qwenloop.domain.config import ToolLimits
from qwenloop.domain.interfaces import ToolLimitsInterface
from qwenloop.domain.model import CODING_TOOL_NAMES
from qwenloop.infrastructure.interfaces import SandboxToolsInterface
from qwenloop.infrastructure.tools import SandboxTools


def _tree(root: Path) -> None:
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "engine_pool.py").write_text(
        "class EnginePool:\n    pass\n\n\ndef build() -> EnginePool:\n    return EnginePool()\n"
    )
    (root / "src" / "pkg" / "other.py").write_text("import os\nvalue = 'enginepool'\n")
    (root / "README.md").write_text("# Title\nEnginePool is documented here.\n")
    (root / "notes.txt").write_text("no match in this one\n")


@pytest.mark.asyncio
async def test_sandbox_tools_honour_their_interfaces(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path)
    assert isinstance(tools, SandboxToolsInterface)
    assert isinstance(ToolLimits(), ToolLimitsInterface)
    assert tools.limits == ToolLimits()
    assert tools.tool_names == CODING_TOOL_NAMES


def test_the_tool_catalogue_names_every_tool_the_model_is_given() -> None:
    assert CODING_TOOL_NAMES == (
        "read_file",
        "write_file",
        "edit_file",
        "shell",
        "search",
        "find",
        "open_file",
    )


@pytest.mark.asyncio
async def test_every_catalogued_tool_is_dispatched(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a\n")
    tools = SandboxTools(tmp_path)
    for name in CODING_TOOL_NAMES:
        result = await tools.execute(name, {"path": "a.txt"})
        assert "unknown tool" not in str(result.get("error", "")), name


@pytest.mark.asyncio
async def test_unknown_tool_error_lists_the_available_tools(tmp_path: Path) -> None:
    result = await SandboxTools(tmp_path).execute("tail", {"path": "x"})
    error = str(result["error"])
    assert error.startswith("unknown tool 'tail'")
    assert "available tools: " + ", ".join(CODING_TOOL_NAMES) in error


@pytest.mark.asyncio
async def test_a_namespaced_tool_name_resolves_to_the_tool(tmp_path: Path) -> None:
    # gpt-oss's harmony template namespaces tools (Ollama logged `repo_browser.open_file`).
    (tmp_path / "a.txt").write_text("hello\n")
    tools = SandboxTools(tmp_path)
    assert await tools.execute("repo_browser.open_file", {"path": "a.txt"}) == {
        "content": "hello\n"
    }
    assert await tools.execute("functions.read_file", {"path": "a.txt"}) == {"content": "hello\n"}
    unknown = await tools.execute("repo_browser.print_tree", {})
    assert str(unknown["error"]).startswith("unknown tool 'repo_browser.print_tree'")


# -- search -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_finds_literal_text_across_the_worktree(tmp_path: Path) -> None:
    _tree(tmp_path)
    result = await SandboxTools(tmp_path).execute("search", {"query": "EnginePool"})
    assert result == {
        "matches": [
            "README.md:2: EnginePool is documented here.",
            "src/pkg/engine_pool.py:1: class EnginePool:",
            "src/pkg/engine_pool.py:5: def build() -> EnginePool:",
            "src/pkg/engine_pool.py:6:     return EnginePool()",
        ],
        "count": 4,
        "truncated": False,
    }


@pytest.mark.asyncio
async def test_search_is_literal_unless_asked_for_a_regex(tmp_path: Path) -> None:
    _tree(tmp_path)
    tools = SandboxTools(tmp_path)
    literal = await tools.execute("search", {"query": "build("})
    assert literal["matches"] == ["src/pkg/engine_pool.py:5: def build() -> EnginePool:"]
    regex = await tools.execute("search", {"query": r"^class \w+Pool", "regex": True})
    assert regex["matches"] == ["src/pkg/engine_pool.py:1: class EnginePool:"]
    invalid = await tools.execute("search", {"query": "(", "regex": True})
    assert str(invalid["error"]).startswith("invalid regex")


@pytest.mark.asyncio
async def test_search_honours_case_path_and_glob(tmp_path: Path) -> None:
    _tree(tmp_path)
    tools = SandboxTools(tmp_path)
    folded = await tools.execute(
        "search", {"query": "enginepool", "ignore_case": True, "path": "src"}
    )
    assert folded["count"] == 4
    globbed = await tools.execute("search", {"query": "EnginePool", "glob": "*.md"})
    assert globbed["matches"] == ["README.md:2: EnginePool is documented here."]
    one_file = await tools.execute("search", {"query": "value", "path": "src/pkg/other.py"})
    assert one_file["matches"] == ["src/pkg/other.py:2: value = 'enginepool'"]


@pytest.mark.asyncio
async def test_search_accepts_the_argument_names_models_reach_for(tmp_path: Path) -> None:
    _tree(tmp_path)
    tools = SandboxTools(tmp_path)
    for key in ("query", "pattern", "text", "q", "term", "keyword", "search"):
        result = await tools.execute("search", {key: "documented"})
        assert result["count"] == 1, key
    for key in ("path", "dir", "directory", "root"):
        result = await tools.execute("search", {"query": "value", key: "src/pkg"})
        assert result["count"] == 1, key
    for key in ("glob", "include", "file_pattern", "files"):
        result = await tools.execute("search", {"query": "EnginePool", key: "*.md"})
        assert result["count"] == 1, key
    for key in ("case_insensitive", "ignore_case"):
        result = await tools.execute("search", {"query": "ENGINEPOOL", key: True})
        assert result["count"] == 5, key
    for key in ("max_results", "limit", "topn", "max_matches"):
        result = await tools.execute("search", {"query": "EnginePool", key: 1})
        assert (result["count"], result["truncated"]) == (1, True), key


@pytest.mark.asyncio
async def test_search_requires_a_query(tmp_path: Path) -> None:
    result = await SandboxTools(tmp_path).execute("search", {"path": "."})
    assert str(result["error"]).startswith("search needs a query")


@pytest.mark.asyncio
async def test_search_is_bounded_by_its_configured_limits(tmp_path: Path) -> None:
    (tmp_path / "many.txt").write_text("".join(f"hit {i} " + "x" * 50 + "\n" for i in range(10)))
    (tmp_path / "big.txt").write_text("hit\n" * 500)
    limits = ToolLimits(max_search_matches=3, max_line_chars=12, max_file_bytes=1000)
    tools = SandboxTools(tmp_path, limits=limits)
    result = await tools.execute("search", {"query": "hit"})
    # big.txt (2000 bytes) is over max_file_bytes and skipped; many.txt is cut at three.
    assert result == {
        "matches": [
            "many.txt:1: hit 0 xxxxxx…",
            "many.txt:2: hit 1 xxxxxx…",
            "many.txt:3: hit 2 xxxxxx…",
        ],
        "count": 3,
        "truncated": True,
    }
    # A model may ask for fewer than the limit, never for more.
    assert (await tools.execute("search", {"query": "hit", "max_results": 1}))["count"] == 1
    assert (await tools.execute("search", {"query": "hit", "max_results": 99}))["count"] == 3
    assert (await tools.execute("search", {"query": "hit", "max_results": "2"}))["count"] == 2
    assert (await tools.execute("search", {"query": "hit", "max_results": "lots"}))["count"] == 3
    assert (await tools.execute("search", {"query": "hit", "max_results": 0}))["count"] == 3


@pytest.mark.asyncio
async def test_search_skips_excluded_dirs_binaries_and_undecodable_files(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("needle\n")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "site.py").write_text("needle\n")
    (tmp_path / "image.png").write_bytes(b"needle\x00\x01")
    (tmp_path / "latin1.txt").write_bytes(b"needle \xff\n")
    (tmp_path / "kept.py").write_text("needle\n")
    result = await SandboxTools(tmp_path).execute("search", {"query": "needle"})
    assert result["matches"] == ["kept.py:1: needle"]
    custom = SandboxTools(tmp_path, limits=ToolLimits(skip_dirs=()))
    found = await custom.execute("search", {"query": "needle"})
    # A directory's own files come before its subdirectories', each level in name order.
    assert found["matches"] == [
        "kept.py:1: needle",
        ".git/config:1: needle",
        ".venv/lib/site.py:1: needle",
    ]


@pytest.mark.asyncio
async def test_search_never_reads_outside_the_worktree(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("needle\n")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "link.txt").symlink_to(outside / "secret.txt")
    (worktree / "linkdir").symlink_to(outside, target_is_directory=True)
    (worktree / "inside.txt").write_text("needle\n")
    tools = SandboxTools(worktree)
    result = await tools.execute("search", {"query": "needle"})
    assert result["matches"] == ["inside.txt:1: needle"]
    with pytest.raises(ValueError, match="escapes"):
        await tools.execute("search", {"query": "needle", "path": "../outside"})
    missing = await tools.execute("search", {"query": "needle", "path": "absent"})
    assert missing == {"error": "no such file or directory: absent"}


@pytest.mark.asyncio
async def test_search_reports_an_unreadable_file_instead_of_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.txt").write_text("needle\n")
    (tmp_path / "b.txt").write_text("needle\n")
    original = Path.read_bytes

    def flaky(self: Path) -> bytes:
        if self.name == "a.txt":
            raise PermissionError("denied")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", flaky)
    result = await SandboxTools(tmp_path).execute("search", {"query": "needle"})
    assert result["matches"] == ["b.txt:1: needle"]


# -- find ---------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_matches_file_names_by_substring_or_glob(tmp_path: Path) -> None:
    _tree(tmp_path)
    tools = SandboxTools(tmp_path)
    assert await tools.execute("find", {"pattern": "engine"}) == {
        "files": ["src/pkg/engine_pool.py"],
        "count": 1,
        "truncated": False,
    }
    by_glob = await tools.execute("find", {"pattern": "*.py"})
    assert by_glob["files"] == ["src/pkg/engine_pool.py", "src/pkg/other.py"]
    by_path_glob = await tools.execute("find", {"pattern": "src/*/other.py"})
    assert by_path_glob["files"] == ["src/pkg/other.py"]
    case_folded = await tools.execute("find", {"pattern": "readme"})
    assert case_folded["files"] == ["README.md"]
    under = await tools.execute("find", {"pattern": "", "path": "src"})
    assert under["files"] == ["src/pkg/engine_pool.py", "src/pkg/other.py"]


@pytest.mark.asyncio
async def test_find_accepts_the_argument_names_models_reach_for(tmp_path: Path) -> None:
    _tree(tmp_path)
    tools = SandboxTools(tmp_path)
    for key in ("pattern", "name", "glob", "query", "filename", "file"):
        result = await tools.execute("find", {key: "notes"})
        assert result["files"] == ["notes.txt"], key


@pytest.mark.asyncio
async def test_find_is_bounded_and_confined(tmp_path: Path) -> None:
    for index in range(5):
        (tmp_path / f"f{index}.txt").write_text("")
    tools = SandboxTools(tmp_path, limits=ToolLimits(max_find_results=2))
    result = await tools.execute("find", {"pattern": "*.txt"})
    assert result == {"files": ["f0.txt", "f1.txt"], "count": 2, "truncated": True}
    with pytest.raises(ValueError, match="escapes"):
        await tools.execute("find", {"pattern": "x", "path": ".."})
    missing = await tools.execute("find", {"pattern": "x", "path": "absent"})
    assert missing == {"error": "no such file or directory: absent"}


# -- open_file ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_file_reads_like_read_file(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\ntwo\n")
    tools = SandboxTools(tmp_path)
    assert await tools.execute("open_file", {"path": "a.txt"}) == await tools.execute(
        "read_file", {"path": "a.txt"}
    )
    assert "error" in await tools.execute("open_file", {"path": "missing.txt"})
    with pytest.raises(ValueError, match="escapes"):
        await tools.execute("open_file", {"path": "../x"})


@pytest.mark.asyncio
async def test_open_file_and_read_file_take_an_optional_line_range(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("".join(f"line {i}\n" for i in range(1, 11)))
    tools = SandboxTools(tmp_path)
    ranged = await tools.execute("open_file", {"path": "a.txt", "line_start": 3, "line_end": 4})
    assert ranged == {
        "content": "line 3\nline 4\n",
        "line_start": 3,
        "line_end": 4,
        "total_lines": 10,
    }
    assert await tools.execute("read_file", {"path": "a.txt", "line_start": 3, "line_end": 4}) == (
        ranged
    )
    open_ended = await tools.execute("open_file", {"path": "a.txt", "line_start": 9})
    assert open_ended["content"] == "line 9\nline 10\n"
    head = await tools.execute("open_file", {"path": "a.txt", "line_end": 1})
    assert (head["content"], head["line_start"]) == ("line 1\n", 1)
    clamped = await tools.execute("open_file", {"path": "a.txt", "line_start": 0, "line_end": 99})
    assert (clamped["line_start"], clamped["line_end"]) == (1, 10)
    past_end = await tools.execute("open_file", {"path": "a.txt", "line_start": 50})
    assert past_end["content"] == ""


@pytest.mark.asyncio
async def test_open_file_accepts_the_argument_names_models_reach_for(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("".join(f"line {i}\n" for i in range(1, 11)))
    tools = SandboxTools(tmp_path)
    for key in ("path", "file", "filename", "file_path"):
        assert (await tools.execute("open_file", {key: "a.txt"}))["content"].startswith("line 1")
    for start, end in (
        ("line_start", "line_end"),
        ("start_line", "end_line"),
        ("start", "end"),
    ):
        result = await tools.execute("open_file", {"path": "a.txt", start: "2", end: 3})
        assert result["content"] == "line 2\nline 3\n", (start, end)
    for start, count in (("line", "num_lines"), ("loc", "num_lines"), ("offset", "limit")):
        result = await tools.execute("open_file", {"path": "a.txt", start: 5, count: 2})
        assert result["content"] == "line 5\nline 6\n", (start, count)
    bad = await tools.execute("open_file", {"path": "a.txt", "line_start": "three"})
    assert str(bad["error"]).startswith("line numbers must be integers")


@pytest.mark.asyncio
async def test_reads_are_bounded_by_the_configured_character_limit(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("abcdef\nghijkl\n")
    tools = SandboxTools(tmp_path, limits=ToolLimits(max_read_chars=4))
    assert await tools.execute("read_file", {"path": "a.txt"}) == {"content": "abcd"}
    ranged = await tools.execute("open_file", {"path": "a.txt", "line_start": 2})
    assert ranged["content"] == "ghij"
