"""Word statistics for a piece of text, and two ways to print them."""

from __future__ import annotations

import re

STOPWORDS = frozenset({"the", "a", "an", "and", "of", "to", "in", "is"})

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lower-case words: letters a-z and digits, with apostrophes allowed inside a word."""
    return _WORD.findall(text.lower())


def word_counts(text: str, drop_stopwords: bool = False) -> dict[str, int]:
    """Occurrences of each word, in the order the words first appear."""
    counts: dict[str, int] = {}
    for word in tokenize(text):
        if drop_stopwords and word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def top_words(text: str, n: int = 3, drop_stopwords: bool = True) -> list[tuple[str, int]]:
    """The n most frequent words: highest count first, ties in alphabetical order."""
    if n <= 0:
        return []
    counts = word_counts(text, drop_stopwords)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


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


def summary(text: str, n: int = 3, fmt: str = "table") -> str:
    """The top n words of text, rendered as a table or as csv."""
    rows = top_words(text, n)
    if fmt == "table":
        return render_table(rows)
    if fmt == "csv":
        return render_csv(rows)
    raise ValueError(f"unknown format: {fmt}")
