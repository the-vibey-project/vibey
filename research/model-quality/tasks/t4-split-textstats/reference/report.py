"""Printing (word, count) rows as a table or as csv."""

from __future__ import annotations


def render_table(rows: list[tuple[str, int]]) -> str:
    """A two-column text table: word left-aligned, count right-aligned, no trailing newline."""
    word_width = max([len("word")] + [len(word) for word, _ in rows])
    count_width = max([len("count")] + [len(str(count)) for _, count in rows])
    lines = [f"{'word'.ljust(word_width)} | {'count'.rjust(count_width)}"]
    lines.append("-" * word_width + "-+-" + "-" * count_width)
    for word, count in rows:
        lines.append(f"{word.ljust(word_width)} | {str(count).rjust(count_width)}")
    return "\n".join(lines)


def render_csv(rows: list[tuple[str, int]]) -> str:
    """CSV with a header row. A word containing a comma or a double quote is quoted."""
    lines = ["word,count"]
    for word, count in rows:
        if "," in word or '"' in word:
            word = '"' + word.replace('"', '""') + '"'
        lines.append(f"{word},{count}")
    return "\n".join(lines) + "\n"
