"""Word statistics for a piece of text, and two ways to print them."""

from __future__ import annotations

from report import render_csv, render_table
from tokenizer import STOPWORDS, tokenize, top_words, word_counts

__all__ = [
    "STOPWORDS",
    "render_csv",
    "render_table",
    "summary",
    "tokenize",
    "top_words",
    "word_counts",
]


def summary(text: str, n: int = 3, fmt: str = "table") -> str:
    """The top n words of text, rendered as a table or as csv."""
    rows = top_words(text, n)
    if fmt == "table":
        return render_table(rows)
    if fmt == "csv":
        return render_csv(rows)
    raise ValueError(f"unknown format: {fmt}")
