# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""EventsTail reads an append-only JSONL file by byte offset, never losing a partial line."""

from pathlib import Path

from vibey.infrastructure.engines.events_tail import EventsTail


def _append(path: Path, data: bytes) -> None:
    with path.open("ab") as handle:
        handle.write(data)


def test_returns_only_new_complete_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventsTail(path)
    _append(path, b"a\nb\n")
    assert tail.read_new() == ["a", "b"]
    _append(path, b"c\n")
    assert tail.read_new() == ["c"]
    assert tail.read_new() == []


def test_holds_back_a_half_written_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventsTail(path)
    _append(path, b'{"x":')
    assert tail.read_new() == []
    _append(path, b"1}\n")
    assert tail.read_new() == ['{"x":1}']


def test_flush_returns_a_final_unterminated_line_once(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventsTail(path)
    _append(path, b"a\nb")
    assert tail.read_new() == ["a"]
    assert tail.flush() == ["b"]
    assert tail.flush() == []


def test_missing_file_reads_as_empty(tmp_path: Path) -> None:
    tail = EventsTail(tmp_path / "absent.jsonl")
    assert tail.read_new() == []
    assert tail.flush() == []


def test_multibyte_character_split_across_reads_is_not_corrupted(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventsTail(path)
    _append(path, b"\xc3")
    assert tail.read_new() == []
    _append(path, b"\xa9\n")
    assert tail.read_new() == ["é"]


def test_blank_lines_are_returned_as_empty_strings(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    tail = EventsTail(path)
    _append(path, b"a\n\nb\n")
    assert tail.read_new() == ["a", "", "b"]
