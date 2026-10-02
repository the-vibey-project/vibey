# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`MarkdownFences` reads fenced code the way CommonMark does.

The documentation deep scan counted backticks and failed, every night from 2026-09-28, on
a file every CommonMark parser renders correctly. `FAILING` is that file's construct, as
it stood in docs/plans/qwenstorm-3.0.0/specs/seo-cli-reference-examples.md.
"""

from __future__ import annotations

import pytest

from vibey_gh.interfaces.markdown_fences_interface import MarkdownFencesInterface, UnclosedFence
from vibey_gh.markdown_fences import MarkdownFences

FAILING = """\
# Spec

There are only 2 literal ` ``` ` fences in the whole file (`grep -c '```' cli.md`),
so insert one fenced ` ```bash ` block per command.

1. Add an example:

   ```bash
   vibey init my-project
   ```

- [ ] `grep -c '^```bash$' docs/reference/cli.md` is at least 16, each one a ` ```bash ` fence.

```python
import re

fence_re = re.compile(r"^```bash$")
```

    grep -c '^```bash$' docs/reference/cli.md
"""


def unclosed(text: str) -> UnclosedFence | None:
    return MarkdownFences().unclosed(text)


def test_it_implements_its_interface():
    assert isinstance(MarkdownFences(), MarkdownFencesInterface)


def test_the_construct_that_failed_the_deep_scan_has_every_fence_closed():
    assert FAILING.count("```") % 2 == 1  # what the old check counted, and failed on
    assert unclosed(FAILING) is None


def test_a_fence_that_never_closes_is_named_by_its_line_and_marker():
    assert unclosed("intro\n\n```bash\nls\n") == UnclosedFence(3, "```")
    assert unclosed(FAILING + "\n~~~~\nrest\n") == UnclosedFence(
        len(FAILING.splitlines()) + 2, "~~~~"
    )


@pytest.mark.parametrize(
    ("text", "open_"),
    [
        ("~~~\ncode\n~~~\n", False),
        ("````md\n```bash\nls\n```\n````\n", False),  # a longer fence around a shorter one
        ("```\ncode\n`````\n", False),  # a longer closer closes it
        ("````\ncode\n```\n", True),  # a shorter one does not
        ("```\ncode\n~~~\n", True),  # nor does the other character
        ("```\ncode\n``` not a closer\n", True),  # nor a run with text after it
        ("```\ncode\n   ```\n", False),  # three columns of indent is still a closer
        ("```\ncode\n    ```\n", True),  # four is content
        ("~~~ info with ` backticks\ncode\n~~~\n", False),  # a tilde info may hold one
        ("``` info with ` a backtick\n", False),  # a backtick info may not: no fence
        ("    ```\nindented code, not a fence\n", False),
        ("\t```\nindented by a tab, not a fence\n", False),
        ("para\n    ```\nstill the paragraph\n", False),
    ],
)
def test_fences_open_and_close_by_commonmark_rules(text, open_):
    assert (unclosed(text) is not None) is open_


def test_a_fence_in_a_block_quote_closes_inside_it_or_ends_with_it():
    assert unclosed("> ```\n> code\n> ```\n") is None
    # The quote ends at the unquoted line and takes its fence with it: CommonMark, not an error.
    assert unclosed("> ```\n> code\n\nafter\n") is None
    assert unclosed("> ```\n> code\n") == UnclosedFence(1, "```")
    assert unclosed(">> ```\n>> code\n>> ```\n") is None


def test_a_fence_in_a_list_item_belongs_to_the_item():
    assert unclosed("1. step\n\n   ```bash\n   ls\n\n   ```\n2. next\n") is None
    assert unclosed("- ```\n  code\n  ```\n") is None
    # A closer written less indented than the item ends the item, and opens a new fence
    # at the top level that runs to the end -- what every CommonMark renderer shows.
    assert unclosed("1. step\n\n   ```bash\n   ls\n```\n") == UnclosedFence(5, "```")
    assert unclosed("- item\n\n   > ```\n   > code\n   > ```\n") is None


@pytest.mark.parametrize(
    "text",
    [
        "-\n  ```\n  code\n  ```\n",  # an item that opens empty
        "-      ```\nindented code inside the item, not a fence\n",  # five spaces after it
        "* * *\n```\ncode\n```\n",  # a thematic break, not an item
        "para\n2. not an item here\n```\ncode\n```\n",
        "para\n-\n```\ncode\n```\n",
        "# heading\n```\ncode\n```\n",
        "para\n***\n```\n```\n",
    ],
)
def test_items_breaks_and_headings_do_not_hide_a_closed_fence(text):
    assert unclosed(text) is None


def test_lazy_continuation_keeps_a_container_open_and_a_block_start_ends_it():
    # "lazy" continues the quote's paragraph, so the next quoted fence is still in it.
    assert unclosed("> para\nlazy\n> ```\n> code\n> ```\n") is None
    # A fence cannot be lazy: it ends the quote and opens at the top level.
    assert unclosed("> para\n```\ncode\n") == UnclosedFence(2, "```")
    # Under an item that did not continue, a sibling numbered 2 starts a new item.
    assert unclosed("1. para\n2. ```\n   code\n   ```\n") is None
    # `<div>` ends the item and opens an HTML block that swallows the first ``` up to the
    # blank line; the second ``` is a fence of its own, and nothing closes it.
    assert unclosed("- para\n<div>\n```\n\n```\n") == UnclosedFence(5, "```")


@pytest.mark.parametrize(
    ("text", "open_"),
    [
        ("<!-- a comment\n```\nstill the comment -->\n", False),
        ("<!-- one line -->\n```\ncode\n", True),
        ("<pre>\n```\n</pre>\n", False),
        ("<?php\n```\n?>\n", False),
        ("<!DOCTYPE html\n```\n>\n", False),
        ("<![CDATA[\n```\n]]>\n", False),
        ("<details>\n```bash\n\n", False),  # an HTML block until the blank line
        ("<details>\n\n```bash\n", True),  # after it, a fence
        ("<custom-tag>\n```\n\n", False),  # a lone tag is an HTML block too
        ("para\n<custom-tag>\n```\n", True),  # but not one that interrupts a paragraph
        ("> <!--\n> ```\n\n```\n", True),  # an HTML block ends with its quote
    ],
)
def test_html_blocks_are_raw_html_not_fences(text, open_):
    assert (unclosed(text) is not None) is open_
