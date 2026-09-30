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

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

from vibey_gh.interfaces.context_sizer_interface import ContextSizerInterface

T = TypeVar("T")


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
        max_document_chars: int,
        sizer: ContextSizerInterface,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """`trim`, to what the model's window leaves beside the diff and the instructions
        (and never more than `max_document_chars`, the documents' own declared limit --
        never the diff's)."""

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

    @property
    def code_bytes(self) -> int:
        """Random bytes in each check code, so a caller can size a request as it is sent."""
        ...

    def seal(self, payload: Mapping[str, Any], head: str, tail: str) -> dict[str, Any]:
        """A copy of `payload` that asks the runner to refuse rather than cut an oversized
        prompt, and that carries check code `head` at the start of the system prompt and
        `tail` at the end of the user prompt, with a schema field to echo both in."""

    def size(self, payload: Mapping[str, Any]) -> int:
        """Every character `ask` would send for `payload`, sealed with check codes of the
        length it writes: what a caller sizes a request by before it sends one."""
        ...

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


@runtime_checkable
class DiffPartInterface(Protocol):
    """A run of a unified diff reviewed whole, and the files it carries."""

    @property
    def text(self) -> str: ...

    @property
    def paths(self) -> tuple[str, ...]: ...

    @property
    def split(self) -> tuple[str, ...]:
        """The files whose added hunk was split at line boundaries and has a piece in this
        part; empty when every hunk this part carries is whole."""
        ...


@runtime_checkable
class AddedHunkSplitterInterface(Protocol):
    """Splits a hunk that only adds lines -- a new file's, or an insertion -- at line
    boundaries, so a hunk larger than one part can still be reviewed whole across parts."""

    def added_only(self, hunk: str) -> bool:
        """Whether `hunk` (its `@@` header and its body) only adds lines, and its header
        agrees: no old lines, and exactly as many new lines as the body adds. A hunk with a
        context or removed line is never split -- the model must see a changed region whole."""
        ...

    def pieces(self, header: str, hunk: str, budget: int, where: str) -> list[str] | None:
        """`hunk` as consecutive pieces, each a hunk of its own with a synthesized `@@`
        header that numbers its new-side lines truly and says which piece of how many it
        is, and each at most `budget` characters with the file's `header` before it. None
        when `hunk` is not `added_only`, so the caller refuses it as before. Raises
        `ReviewRefused` when one line cannot fit a part alone: a line is never cut."""
        ...


@runtime_checkable
class DiffChunkerInterface(Protocol):
    """Splits a unified diff into parts a model can review whole: by file, then by hunk."""

    @property
    def split_added_hunks(self) -> bool:
        """Whether a hunk that only adds lines and is too large for one part is split at
        line boundaries (`AddedHunkSplitterInterface`) rather than refused."""
        ...

    def sections(self, diff: str) -> list[tuple[str, str]]:
        """`(path, text)` for each file in `diff`, in order. Text before the first file
        header travels with the first file; a diff with no file header is one section with
        no path."""
        ...

    def parts(self, diff: str, budget: int) -> Sequence[DiffPartInterface]:
        """Each file whole when it fits `budget` characters, else split between its hunks
        with its header repeated before each run. A file with no hunk boundary, or one hunk
        with its header, larger than `budget` is refused (`ReviewRefused`) -- never cut --
        except, with `split_added_hunks`, a hunk that only adds lines, which is split at
        line boundaries into labelled pieces; one line too large alone is still refused."""
        ...

    def chunks(self, diff: str, budget: int) -> Sequence[DiffPartInterface]:
        """`parts`, packed in order into as few runs of at most `budget` characters as
        they fit in."""
        ...


@runtime_checkable
class TransportRetryInterface(Protocol):
    """A bounded retry of a model call whose transport failed: unreachable or timed out."""

    @property
    def retries(self) -> int: ...

    @property
    def backoff_seconds(self) -> float: ...

    def run(self, call: Callable[[], T]) -> tuple[T, int]:
        """`call()`'s result and the attempts it took. A transport failure is retried up to
        `retries` times after a doubling backoff and then raised as `ReviewRefused` coded
        `model_timeout` or `model_unreachable`; anything else is raised as it came."""
        ...


@runtime_checkable
class SovereignReviewInterface(Protocol):
    """One review of one diff: a single request when it fits, bounded parts when not."""

    def room(self, documents: Mapping[str, str], *, part: bool) -> int:
        """How many characters of diff one request can carry beside everything else it
        sends, `documents` and -- for a part -- the part note included."""
        ...

    def plan(self, diff: str, documents: Mapping[str, str]) -> Sequence[DiffPartInterface] | None:
        """The parts `diff` is reviewed in, or None when the single request answers more
        honestly; `ReviewRefused` when neither can review it whole."""
        ...

    def run(self, diff: str) -> tuple[dict[str, Any], dict[str, Any], Any]:
        """`(verdict, shown, report)`: the composed verdict, what a whole review was shown
        (`kept`, `cut`, `dropped`), and how many parts and attempts it took."""
        ...

    def compose(
        self,
        parts: Sequence[DiffPartInterface],
        answers: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """One verdict from every part's: a boolean holds only when exactly `true` in every
        part, lists are joined in order, each part's text is kept under its number, and
        `review_parts` records what each part carried and answered."""
        ...
