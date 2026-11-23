# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writing one table of the person's own `vibey.toml` (SP-LOOPS Task 7).

The `vibey loops marketplace | plugin | mcp` commands change `[loops]` and nothing else: every byte
outside the table -- other tables, comments, blank lines -- is kept as it was, the file is replaced
atomically with mode 0600, and a file the writer cannot rewrite without loss (a comment inside the
table, the table spelt as dotted keys or inline) is refused with nothing written.
"""

from __future__ import annotations

import os
import stat
import tomllib
from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.interfaces.trusted_table_writer_interface import (
    TrustedTableWriterInterface,
)
from vibey.infrastructure.trusted_table_writer import TomlTrustedTableWriter

LOOPS = {
    "plugins": ["currency-research@vibey", "lint@acme"],
    "marketplaces": [{"name": "acme", "source": "https://example.test/acme.git", "ref": "v1"}],
    "mcp_servers": [
        {"name": "files", "trust": "local", "command": ["fake-mcp", "--stdio"]},
        {"name": "tickets", "trust": "remote", "url": "https://mcp.example.test/v1"},
    ],
}


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _read(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_the_writer_satisfies_its_interface() -> None:
    assert isinstance(TomlTrustedTableWriter(), TrustedTableWriterInterface)


def test_a_missing_file_and_folder_are_made_private_and_hold_only_the_table(
    tmp_path: Path,
) -> None:
    path = tmp_path / "config" / "vibey" / "vibey.toml"
    TomlTrustedTableWriter().write_table(path, "loops", LOOPS)
    assert _read(path) == {"loops": LOOPS}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_everything_outside_the_table_is_kept_byte_for_byte(tmp_path: Path) -> None:
    before = (
        "# my settings, by hand\n"
        'top = "x"  # a trailing comment\n'
        "\n"
        "[web]\n"
        "# keep me\n"
        "max_chars = 100\n"
        "\n"
    )
    after = "# the hub, below\n[hub]\nport = 1\n"
    path = _write(
        tmp_path / "vibey.toml",
        before + '[loops]\nskills = ["old"]\n\n[[loops.marketplaces]]\nname = "x"\n'
        'source = "/srv/x"\n\n' + after,
    )
    TomlTrustedTableWriter().write_table(path, "loops", LOOPS)
    text = path.read_text(encoding="utf-8")
    assert text.startswith(before)
    assert text.endswith(after)
    assert _read(path) == {
        "top": "x",
        "web": {"max_chars": 100},
        "hub": {"port": 1},
        "loops": LOOPS,
    }


def test_pieces_of_the_table_spread_through_the_file_become_one_block(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "vibey.toml",
        '[loops]\nskills = ["a"]\n[web]\nmax_chars = 1\n[[loops.mcp_servers]]\nname = "s"\n'
        'trust = "remote"\nurl = "https://x.test/"\n[hub]\nport = 2\n',
    )
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["b"]})
    text = path.read_text(encoding="utf-8")
    assert text.startswith('[loops]\nskills = ["b"]\n')
    assert text.count("loops") == 1
    assert _read(path) == {"loops": {"skills": ["b"]}, "web": {"max_chars": 1}, "hub": {"port": 2}}


def test_a_file_without_the_table_gets_it_at_the_end(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", "[web]\nmax_chars = 1")  # no final newline
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": []})
    assert path.read_text(encoding="utf-8") == "[web]\nmax_chars = 1\n\n[loops]\nskills = []\n"


@pytest.mark.parametrize(
    "header",
    ["[ loops ]", '["loops"]', "[\t'loops'\t]", "[[loops . marketplaces]]", '[["loops".x]]'],
)
def test_every_spelling_of_the_table_header_is_the_table(tmp_path: Path, header: str) -> None:
    body = 'name = "x"\nsource = "/s"\n' if "marketplaces" in header else "y = 1\n"
    path = _write(tmp_path / "vibey.toml", f"[web]\nmax_chars = 1\n{header}\n{body}")
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["z"]})
    assert _read(path) == {"web": {"max_chars": 1}, "loops": {"skills": ["z"]}}


def test_a_table_whose_name_only_starts_alike_is_another_table(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", '[loopsy]\nkeep = true\n["loops-x"]\nkeep = 1\n')
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": []})
    assert _read(path) == {
        "loopsy": {"keep": True},
        "loops-x": {"keep": 1},
        "loops": {"skills": []},
    }


def test_text_that_only_looks_like_a_header_is_not_one(tmp_path: Path) -> None:
    """A `[loops]` inside a multi-line string, and an array whose rows start with `[`, are values:
    the scan knows strings and arrays, and the result is checked against the original anyway."""
    original = (
        "[web]\n"
        'notes = """\n[loops]\nnot a header, \\""" still the string\n"""\n'
        "literal = '''\n[[loops.mcp_servers]]\n'''\n"
        "grid = [\n  [1, 2],\n  [3, 4],\n]\n"
        'quoted = "a ] b [ # c"\n'
        "single = 'a # not a comment'\n"
    )
    path = _write(tmp_path / "vibey.toml", original + "[loops]\nskills = []\n")
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["s"]})
    assert path.read_text(encoding="utf-8").startswith(original)
    assert _read(path)["loops"] == {"skills": ["s"]}


def test_comments_after_the_table_belong_to_what_follows(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "vibey.toml",
        '[loops]\nskills = ["a"]\n\n# ---- web ----\n\n[web]\nmax_chars = 1\n',
    )
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": []})
    assert path.read_text(encoding="utf-8") == (
        "[loops]\nskills = []\n\n# ---- web ----\n\n[web]\nmax_chars = 1\n"
    )


@pytest.mark.parametrize(
    "table",
    [
        "[loops]\n# why I chose these\nskills = []\n",
        "[loops] # mine\nskills = []\n",
        '[loops]\nskills = [\n  "a", # the first\n]\n',
        '[loops]\nskills = []\n[[loops.marketplaces]]\nname = "x" # mine\nsource = "/s"\n',
    ],
)
def test_a_comment_inside_the_table_is_never_dropped_the_write_is_refused(
    tmp_path: Path, table: str
) -> None:
    path = _write(tmp_path / "vibey.toml", "[web]\nmax_chars = 1\n" + table)
    before = path.read_bytes()
    with pytest.raises(ConfigError, match=r"comments inside \[loops\]") as caught:
        TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["new"]})
    assert caught.value.path == str(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "text",
    [
        'loops.skills = ["a"]\n[web]\nmax_chars = 1\n',
        "loops = { skills = [] }\n",
        '[loops]\nskills = []\n[web]\nloops = "a key of [web]"\n[web.inner]\nx = 1\n',
    ],
)
def test_a_table_the_writer_cannot_rewrite_exactly_is_refused(tmp_path: Path, text: str) -> None:
    path = _write(tmp_path / "vibey.toml", text)
    before = path.read_bytes()
    try:
        TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["new"]})
    except ConfigError as error:
        assert "edit it by hand" in str(error)
        assert path.read_bytes() == before
    else:  # only a table the writer could rewrite exactly may have been written
        assert _read(path)["loops"] == {"skills": ["new"]}
        assert {k: v for k, v in _read(path).items() if k != "loops"} == {
            k: v for k, v in tomllib.loads(text).items() if k != "loops"
        }


def test_dotted_keys_at_the_root_are_refused_with_nothing_written(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", 'loops.skills = ["a"]\n')
    with pytest.raises(ConfigError, match="edit it by hand"):
        TomlTrustedTableWriter().write_table(path, "loops", {"skills": ["b"]})
    assert path.read_text(encoding="utf-8") == 'loops.skills = ["a"]\n'


def test_values_are_rendered_so_toml_reads_them_back_exactly(tmp_path: Path) -> None:
    values: dict[str, object] = {
        "text": 'quote " backslash \\ tab \t newline \n del \x7f bell \x07 ünïcødé ☃',
        "flag": True,
        "off": False,
        "count": 3,
        "empty": [],
        "nested": [[1, 2], ["a"]],
        "inline": [{"k": "v"}, 4],
        "a key": "needs quotes",
        "sub": {"x": 1, "deeper": {"y": "z"}},
        "rows": [{"name": "r", "sub": {"q": 1}, "items": [{"n": 1}]}],
    }
    path = tmp_path / "vibey.toml"
    TomlTrustedTableWriter().write_table(path, "loops", values)
    assert _read(path) == {"loops": values}


def test_the_rendered_table_is_offered_for_pasting(tmp_path: Path) -> None:
    rendered = TomlTrustedTableWriter().render_table("loops", {"skills": ["a"], "sub": {"x": 1}})
    assert rendered == '[loops]\nskills = ["a"]\n\n[loops.sub]\nx = 1\n'


@pytest.mark.parametrize("value", [1.5, None, object(), "lone \ud800 surrogate", {"k": None}])
def test_a_value_toml_cannot_hold_is_refused(tmp_path: Path, value: object) -> None:
    path = tmp_path / "vibey.toml"
    with pytest.raises(ConfigError, match="cannot be written"):
        TomlTrustedTableWriter().write_table(path, "loops", {"v": value})
    assert not path.exists()


def test_a_symlinked_config_is_written_where_it_points_and_stays_a_link(tmp_path: Path) -> None:
    (tmp_path / "dotfiles").mkdir()
    real = _write(tmp_path / "dotfiles" / "vibey.toml", "[web]\nmax_chars = 1\n")
    link = tmp_path / "config" / "vibey.toml"
    link.parent.mkdir()
    link.symlink_to(real)
    TomlTrustedTableWriter().write_table(link, "loops", {"skills": []})
    assert link.is_symlink()
    assert _read(real) == {"web": {"max_chars": 1}, "loops": {"skills": []}}


def test_a_wider_file_is_narrowed_to_0600(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", "[web]\nmax_chars = 1\n")
    path.chmod(0o644)
    TomlTrustedTableWriter().write_table(path, "loops", {"skills": []})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_failed_write_leaves_the_old_file_and_no_temporary_file(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", "[web]\nmax_chars = 1\n")

    def failing(descriptor: int) -> None:
        raise OSError(28, "No space left on device")

    with pytest.raises(ConfigError, match="cannot be written: .*No space"):
        TomlTrustedTableWriter(fsync=failing).write_table(path, "loops", {"skills": []})
    assert path.read_text(encoding="utf-8") == "[web]\nmax_chars = 1\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["vibey.toml"]


def test_a_write_fsyncs_the_file_and_then_its_folder(tmp_path: Path) -> None:
    synced: list[bool] = []

    def recording(descriptor: int) -> None:
        synced.append(stat.S_ISDIR(os.fstat(descriptor).st_mode))

    TomlTrustedTableWriter(fsync=recording).write_table(tmp_path / "vibey.toml", "loops", {})
    assert synced == [False, True]


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda p: os.mkfifo(p), "is not a regular file"),
        (lambda p: p.write_text("[loops\n", encoding="utf-8"), "is not valid TOML"),
        (lambda p: p.write_bytes(b"\xff\xfe"), "is not valid TOML"),
    ],
)
def test_a_file_that_cannot_be_read_is_refused_and_left(
    tmp_path: Path, setup: object, reason: str
) -> None:
    path = tmp_path / "vibey.toml"
    setup(path)  # type: ignore[operator]
    with pytest.raises(ConfigError, match=reason):
        TomlTrustedTableWriter().write_table(path, "loops", {"skills": []})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["vibey.toml"]


def test_an_unclosed_header_or_string_is_left_to_toml_to_refuse(tmp_path: Path) -> None:
    """A scan that meets an unterminated string or header stops at the end of the text; the file
    is not valid TOML, which the reader says before anything is written."""
    for text in ('[web]\nx = "open\n', "[web]\nx = '''open\n", '[web]\nx = """open\n', "[loo"):
        path = _write(tmp_path / "vibey.toml", text)
        with pytest.raises(ConfigError, match="is not valid TOML"):
            TomlTrustedTableWriter().write_table(path, "loops", {})


def test_a_rewrite_that_would_not_read_back_as_intended_is_refused(tmp_path: Path) -> None:
    """The safety net under the scan: whatever the scan missed, the new text is parsed first and
    must hold the new table and everything else the file held, or nothing is written."""
    from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

    class Losing(TomlTrustedTableReader):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def parse(self, path: Path, text: str) -> dict[str, object]:  # type: ignore[override]
            self.calls += 1
            document = TomlTrustedTableReader.parse(path, text)
            return document if self.calls == 1 else {"loops": document["loops"]}

    path = _write(tmp_path / "vibey.toml", "[web]\nmax_chars = 1\n")
    with pytest.raises(ConfigError, match="cannot rewrite exactly"):
        TomlTrustedTableWriter(reader=Losing()).write_table(path, "loops", {"skills": []})
    assert path.read_text(encoding="utf-8") == "[web]\nmax_chars = 1\n"
