# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam that asks a local model the WHOLE exact-head review.

With no paid review declared (sub-doctrine 8.b, `[pr_automation] paid_review = false`) the
sovereign lane is the only automated reviewer, so it answers both halves of the review
contract: the diff-groundable verdict and the documentation-contract judgments. This
declares what asking it that takes -- the schema it is held to, the prompt it is handed,
the documents it judges against, and the labelling that keeps its verdict honest about
what it saw. `vibey_gh.local_review` supplies the one `vibey-gh local-review --scope full`
uses.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WholeReviewInterface(Protocol):
    """Builds, and then labels, one whole review asked of a local model."""

    def schema(self) -> dict[str, object]:
        """The JSON Schema the model is held to: the review contract's full schema."""

    def system_prompt(self) -> str:
        """The rules, and every documentation judgment with the question it asks."""

    def documents(self, directory: Path) -> dict[str, str]:
        """Every regular file under `directory` by repository-relative path, sorted.

        Symlinks are never followed; a missing directory is no documents at all.
        """

    def user_prompt(self, diff: str, documents: Mapping[str, str], max_chars: int) -> str:
        """The diff and the documents, each bounded by `max_chars`, and told when cut."""

    def finish(
        self, verdict: dict[str, Any], *, model: str, documents: Mapping[str, str]
    ) -> dict[str, Any]:
        """The verdict labelled as the whole review, naming the documents it judged against.

        Never writes a placeholder over a judgment the model made.
        """
