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
from vibey_gh.interfaces.review_timings_interface import RequestLogInterface

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
        sources: Sequence[str] = (),
        sources_cut: Sequence[str] = (),
        sources_dropped: Sequence[str] = (),
    ) -> dict[str, Any]:
        """The verdict labelled as the whole review, naming the documents it judged against,
        which of them were cut and which were left out to fit the window -- and the
        reference `sources` it was shown, cut short or left out.

        When any document was cut or left out, the verdict claims the diff half alone, so it
        is never read as the whole review; a source cut or left out never does, because the
        documentation contract is never judged against a source. Never writes a placeholder
        over a judgment the model made.
        """


@runtime_checkable
class SourceContextInterface(Protocol):
    """The full post-change text of the files a diff changes, handed to a review as
    reference only: what the diff's lines refer to, never something to judge."""

    def files(self, directory: Path) -> dict[str, str]:
        """Every regular text file under `directory` by repository-relative path, sorted.
        Symlinks are never followed, a file holding a NUL byte is binary and left out, and a
        missing directory is no sources at all."""

    def select(self, sources: Mapping[str, str], paths: Sequence[str]) -> dict[str, str]:
        """The `sources` of `paths` alone, in the order of `paths`: the files a diff, or one
        part of it, changes."""

    def rules(self) -> str:
        """What the system prompt gains when sources are shown: what they are for, and that
        no finding may be reported on a line the diff did not change."""

    def cut_note(self, cut: Sequence[str], dropped: Sequence[str]) -> str:
        """What the model is told when sources were `cut` short or `dropped`, naming each;
        empty when nothing was."""

    def block(
        self,
        sources: Mapping[str, str],
        cut: Sequence[str] = (),
        dropped: Sequence[str] = (),
    ) -> str:
        """The `<sources>` block for the user prompt, each source framed by its path, then
        `cut_note`; empty when there is nothing to show or say."""

    def overhead(self, names: Sequence[str]) -> int:
        """Every character sources add to a request beyond their own frames: the rules, the
        block's opening and closing, and the cut note at its longest for `names`."""

    def changed(self, diff: str) -> dict[str, list[tuple[int, int]]]:
        """Each file's changed new-side line ranges in `diff`, first and last line, by the
        path its `diff --git` header names."""

    def excerpt(self, text: str, changed: Sequence[tuple[int, int]], room: int) -> str:
        """`text` in at most `room` characters: its first lines and the lines around each
        `changed` range, with the widest margin that fits, every run of lines left out
        marked with its numbers. When not even the changed lines fit, the start of them,
        cut at a line boundary."""

    def trim(
        self,
        sources: Mapping[str, str],
        budget: int,
        changed: Mapping[str, Sequence[tuple[int, int]]] | None = None,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """The sources that fit `budget` characters, framed: `(kept, cut, dropped)`, in the
        order given. The budget is shared, never first come first served: the smallest are
        kept whole and what is left is split evenly among the rest, each cut to its
        `excerpt` around its `changed` lines; one with no room at all is dropped."""

    def evidence(
        self,
        shown: Sequence[str],
        cut: Sequence[str] = (),
        dropped: Sequence[str] = (),
    ) -> str:
        """The sentence a verdict's summary carries naming the sources the review was
        shown, which were cut to fit, and which no request showed; empty with none."""


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
        deadline: RequestDeadlineInterface | None = None,
        slot: SlotWaitInterface | None = None,
        log: RequestLogInterface | None = None,
    ) -> dict[str, Any]:
        """Size `payload` from everything it sends, refuse it (`ReviewRefused`) when it
        does not fit the window beside the reserve, send it, and return `answer`'s reading
        of the reply. `what` names the part the caller cannot shrink -- "diff", "issue" --
        and `shown_chars` its length, for the refusal. A server's refusal (an HTTP error,
        such as the 400 for a prompt over the window) is a `ReviewRefused` carrying its
        message, never "unreachable".

        The model may write at most the sizer's reserve (`num_predict`). The request is sent
        with `deadline`'s seconds for its size, or `timeout` without one; with `slot`, only
        once the model has come free, and a request that started on a free slot and still
        ran past its deadline is a `ReviewRefused` coded `model_timeout` -- slow on this
        input, which a retry would not change -- rather than a transport failure.

        With `log`, the call is one attempt there, and the request is one `request` entry:
        what it sent, its deadline and how that was derived, how long it took, its outcome
        as a `code`, and Ollama's counters when the model answered. Recording it changes
        nothing the call decides, raises or returns."""

    @staticmethod
    def code(error: BaseException) -> str:
        """Why a request gave no verdict, in `vibey_gh.review_outcome`'s closed vocabulary:
        a refusal's own code, a transport failure's, `answer_unusable` for an answer that is
        not a verdict at all, else `unknown`."""
        ...

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
class RequestDeadlineInterface(Protocol):
    """How long one request to a local model may take, from what it sends and what it may
    write: reading the prompt and writing the answer each at a declared, measured rate."""

    @property
    def floor_seconds(self) -> int:
        """The least any request is given: the fixed timeout it had before it was scaled."""
        ...

    @property
    def scaled(self) -> bool:
        """Whether the deadline scales with the request; without rates it is the floor."""
        ...

    def seconds(self, prompt_tokens: int, output_tokens: int) -> int:
        """Whole seconds for a request of `prompt_tokens` that may write `output_tokens`:
        the time to read the one and write the other at the declared rates, never under
        `floor_seconds`."""
        ...

    def explain(self, prompt_tokens: int, output_tokens: int) -> str:
        """The arithmetic behind `seconds`, in words a refusal can carry."""
        ...

    def basis(self, prompt_tokens: int, output_tokens: int) -> dict[str, Any]:
        """The figures behind `seconds`, for a record: whether it scaled, the floor, the
        two declared rates, and the prompt and output tokens it was computed from."""
        ...


@runtime_checkable
class SlotWaitInterface(Protocol):
    """Waits, bounded, for a local model to come free before a request is sent to it."""

    @property
    def seconds(self) -> int:
        """The longest it waits; 0 never waits, and a request is sent at once."""
        ...

    def wait(self, base_url: str, model: str, num_ctx: int) -> float:
        """Seconds it took the model at `base_url` to answer a one-token request for `model`
        at `num_ctx` -- the window the request will ask for, so the model is loaded as it
        will be used. A runner that does not answer at all is a transport failure
        (`urllib.error.URLError`); one that answers but did not come free within `seconds`
        is `ReviewRefused` coded `model_busy`; one that refuses is coded `model_refused`."""
        ...


@runtime_checkable
class TransportRetryInterface(Protocol):
    """A bounded retry of a model call whose transport failed or whose model stayed busy."""

    @property
    def retries(self) -> int: ...

    @property
    def backoff_seconds(self) -> float: ...

    def run(self, call: Callable[[], T]) -> tuple[T, int]:
        """`call()`'s result and the attempts it took. A transport failure, or a model that
        stayed busy (`model_busy`), is retried up to `retries` times after a doubling backoff
        and then raised as `ReviewRefused` coded `model_timeout`, `model_unreachable` or
        `model_busy`; anything else -- a request slow on its own input included -- is raised
        as it came."""
        ...


@runtime_checkable
class SovereignReviewInterface(Protocol):
    """One review of one diff: a single request when it fits, bounded parts when not."""

    def room(self, documents: Mapping[str, str], *, part: bool) -> int:
        """How many characters of diff one request can carry beside everything else it
        sends, `documents` and -- for a part -- the part note included."""
        ...

    def fit_sources(
        self,
        diff: str,
        sources: Mapping[str, str],
        *,
        documents: Mapping[str, str],
        cut: Sequence[str] = (),
        dropped: Sequence[str] = (),
        part: tuple[int, int] | None = None,
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """The reference `sources` trimmed to what one request leaves beside everything
        else it sends, never past the declared limit: `(kept, cut, dropped)`. Empty, with
        nothing named, when not even their rules and note would fit."""
        ...

    def seen(
        self, sources: Mapping[str, str], kept: Mapping[str, str], cut: Sequence[str]
    ) -> dict[str, list[str]]:
        """What a request was shown of `sources`: `sources`, `sources_cut`, and every one
        not shown as `sources_dropped`."""
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
