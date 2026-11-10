"""Splitting text into words and counting them."""

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
