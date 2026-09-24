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

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from vibey_gh.interfaces.context_sizer_interface import ContextSizerInterface


@runtime_checkable
class WholeReviewInterface(Protocol):
    """Builds, and then labels, one whole review asked of a local model."""

    def schema(self) -> dict[str, object]:
        """The JSON Schema the model is held to: the review contract's full schema."""

    def system_prompt(self) -> str:
        """The rules, and every documentation judgment with the question it asks."""

    def documents(self, directory: Path, order: Sequence[str] = ()) -> dict[str, str]:
        """Every regular file under `directory` by repository-relative path, in `order` --
        the order the repository declared them -- and any others after, sorted.

        Symlinks are never followed; a missing directory is no documents at all.
        """

    def cut_note(self, cut: Sequence[str], dropped: Sequence[str]) -> str:
        """What the model is told when documents were `cut` short or `dropped` entirely,
        naming each; empty when nothing was."""

    def user_prompt(
        self,
        diff: str,
        documents: Mapping[str, str],
        *,
        cut: Sequence[str] = (),
        dropped: Sequence[str] = (),
    ) -> str:
        """The whole diff -- never cut -- and the documents, with `cut_note` whenever any
        was cut or dropped, even when every one of them was."""

    def trim(
        self, documents: Mapping[str, str], budget: int
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """The documents that fit `budget` characters, framed: `(kept, cut, dropped)`, in
        the declared order, so the last declared gives way first."""

    def fit(
        self,
        diff: str,
        documents: Mapping[str, str],
        max_chars: int,
        sizer: ContextSizerInterface,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """`trim`, to what the model's window leaves beside the diff and the instructions
        (and never more than `max_chars`)."""

    def finish(
        self,
        verdict: dict[str, Any],
        *,
        model: str,
        documents: Mapping[str, str],
        cut: Sequence[str] = (),
        dropped: Sequence[str] = (),
    ) -> dict[str, Any]:
        """The verdict labelled as the whole review, naming the documents it judged against,
        which of them were cut and which were left out to fit the window.

        When any was cut or left out, the verdict claims the diff half alone, so it is never
        read as the whole review. Never writes a placeholder over a judgment the model made.
        """


@runtime_checkable
class SizedChatInterface(Protocol):
    """One chat request sized so the model reads all of it, and a reply read honestly."""

    def seal(self, payload: Mapping[str, Any], head: str, tail: str) -> dict[str, Any]:
        """A copy of `payload` that asks the runner to refuse rather than cut an oversized
        prompt, and that carries check code `head` at the start of the system prompt and
        `tail` at the end of the user prompt, with a schema field to echo both in."""

    def ask(
        self,
        base_url: str,
        payload: dict[str, Any],
        *,
        sizer: ContextSizerInterface,
        timeout: int,
        what: str,
        shown_chars: int,
    ) -> dict[str, Any]:
        """Size `payload` from everything it sends, refuse it (`ReviewRefused`) when it
        does not fit the window beside the reserve, send it, and return `answer`'s reading
        of the reply. `what` names the part the caller cannot shrink -- "diff", "issue" --
        and `shown_chars` its length, for the refusal. A server's refusal (an HTTP error,
        such as the 400 for a prompt over the window) is a `ReviewRefused` carrying its
        message, never "unreachable"."""

    def answer(
        self,
        body: Mapping[str, Any],
        *,
        num_ctx: int,
        reserve: int,
        codes: Sequence[str],
    ) -> dict[str, Any]:
        """The verdict in a reply, without its check-code field, or `ReviewRefused` naming
        why there is none: no count of what was read, a count past what the request was
        sized for, `done_reason` other than `stop`, reasoning with no answer, an answer that
        is not JSON, or one that does not echo every one of `codes`."""
