# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for sizing a local model's context window to its prompt (ADR-0016).

Both local-model calls in `vibey_gh.local_review` -- the review and the triage -- ask the
same question: how many tokens of context does this prompt need? One declared seam
answers it for both, so the rule cannot drift between them, and a later slice of #135 can
size the window from the fit projection instead without either call site changing. A
test hands a caller an exact window through this seam rather than patching a module
function (sub-doctrine 9.b).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ContextSizerInterface(Protocol):
    """Chooses the `num_ctx` to request for one prompt."""

    def num_ctx(self, prompt_chars: int) -> int:
        """Tokens of context to ask the runner for, given a prompt of `prompt_chars`
        characters: enough to hold the prompt and the response, never so much that an
        enormous request exhausts the host instead of failing visibly."""
        ...
