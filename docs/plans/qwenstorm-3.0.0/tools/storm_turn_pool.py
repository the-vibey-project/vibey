"""Build storm turns as the chat payloads qwenloop sends, for `vibey-gh slots corpus`.

Two sources, one output (`vibey-gh/turn-pool/1`, JSON lines):

- `lanes` -- the storm's own run records. qwenloop records each run as `events.jsonl` beside
  `meta.json`: every tool result, every fragment of answer text, every retry, and per turn the
  input tokens the runner reported. It does not record the payload, so this rebuilds it with
  qwenloop's OWN pieces -- the system prompt, the lane's `plan.md`, the repair text of a later
  attempt, tool-result truncation, the continue and retry prompts, and the transcript trim --
  imported from the storm's integration checkout, never copied. qwenloop logs a tool call's
  result but not its arguments, so each call is replayed with `{}`, and the recorded input
  tokens are the yardstick for what that loses.
- `specs` -- when no run records survive (they live under the storm's scratch directory, and
  a reboot that wipes `/private/tmp` takes them; it did on 2026-09-24). Each run is one of the
  storm's COMMITTED lane specs, planned with qwenloop's own `build_plan` and system prompt,
  followed by `read_file` turns with their real arguments whose results are the repository's
  real files, truncated as the runner truncates them -- the work 96.7% of lane time went to,
  reading code into context. Depth is recorded as characters / 3, the fit calculus's own
  conservative characters-per-token (`vibey_gh.fit.DEFAULT_CHARS_PER_TOKEN`), and runs stop
  before that estimate reaches the window, so no payload the pool holds can overflow it. The
  runner's own token count on replay is the measurement; this estimate only stratifies.

Messages are written in Ollama's native `/api/chat` shape (tool-call arguments as an object,
tool results named by `tool_name`), because the calibration replays through that API: it is
the one that honours `truncate: false`.

Usage:
  python storm_turn_pool.py lanes [--lanes DIR] [--qwenloop-src DIR] --out POOL.jsonl
  python storm_turn_pool.py specs [--repo DIR] [--runs 40] [--seed 0] --out POOL.jsonl
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from interfaces.storm_turn_pool_interface import (  # noqa: E402
    SpecTurnPoolInterface,
    TurnPoolBuilderInterface,
)

REPO = HERE.parents[3]
POOL_SCHEMA = "vibey-gh/turn-pool/1"
ARGUMENTS_NOTE = (
    "Assistant tool-call arguments: qwenloop's run log records each tool's result but not the"
    " arguments the model sent, so every call is replayed with {} arguments. Each turn's"
    " recorded input tokens are the reference for how much of the prompt that removes."
)
SPECS_NOTE = (
    "Storm-shaped, not replayed: each run is a committed QwenStorm lane spec, planned with"
    " qwenloop's own build_plan and system prompt, followed by read_file turns (with their"
    " real arguments) whose results are the repository's real files at the corpus's commit,"
    " truncated as qwenloop truncates them. The lanes' own payloads were not recorded durably"
    " and were lost when /private/tmp was wiped on 2026-09-24. Depth in the pool is"
    " characters / 3 (conservative); the runner's prompt_eval_count on replay is the"
    " measured depth."
)
#: `vibey_gh.fit.DEFAULT_CHARS_PER_TOKEN`: the family's conservative estimate, restated here
#: because the storm's tools do not import vibey-gh; `test_storm_turn_pool.py` holds the two
#: equal so they cannot drift.
CHARS_PER_TOKEN = 3


class QwenloopRunner:
    """qwenloop's own runner pieces, imported from the given source tree."""

    def __init__(self, qwenloop_src: Path) -> None:
        if str(qwenloop_src) not in sys.path:
            sys.path.insert(0, str(qwenloop_src))
        from qwenloop.application import runner  # the lanes' own runner, not a copy
        from qwenloop.domain.model import DONE_MARKER, ChatMessage
        from qwenloop.infrastructure.inference import _CODING_TOOLS

        self.runner = runner
        self.message = ChatMessage
        self.done = DONE_MARKER
        self.tools = _CODING_TOOLS

    @staticmethod
    def native(message: Any, tool_name: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            out["tool_calls"] = [
                {
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": json.loads(call["function"].get("arguments") or "{}"),
                    }
                }
                for call in message.tool_calls
            ]
        if tool_name is not None:
            out["tool_name"] = tool_name
        return out


class QwenloopTurnPool(TurnPoolBuilderInterface):
    """Rebuilds qwenloop runs from their records with qwenloop's own runner functions."""

    def __init__(self, qwenloop_src: Path, *, max_attempts: int = 3) -> None:
        self._q = QwenloopRunner(qwenloop_src)
        self._repair = self.repair_text(HERE / "qwenlane.py")
        self._max_attempts = max_attempts

    @staticmethod
    def repair_text(qwenlane: Path) -> str:
        """`qwenlane.REPAIR`, read rather than imported: importing the lane driver would run
        its whole lane machinery to fetch one string the lanes appended verbatim."""
        for node in ast.parse(qwenlane.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "REPAIR" for target in node.targets
            ):
                return str(ast.literal_eval(node.value))
        raise ValueError(f"{qwenlane} no longer defines REPAIR")

    @staticmethod
    def _started(run: Path) -> str:
        for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("type") == "turn.completed":
                return str(event.get("started_at", ""))
        return ""

    def runs(self, lanes: Path) -> list[Path]:
        found: list[Path] = []
        if not lanes.is_dir():
            return found
        for lane in sorted(p for p in lanes.iterdir() if (p / ".qwenloop" / "runs").is_dir()):
            runs = [
                r for r in (lane / ".qwenloop" / "runs").iterdir() if (r / "events.jsonl").is_file()
            ]
            found.extend(sorted(runs, key=self._started))
        return found

    def build(self, run_dirs: Iterable[Path]) -> Iterator[dict[str, Any]]:
        attempts: dict[Path, int] = {}
        for run_dir in run_dirs:
            lane = run_dir.parents[2]
            attempts[lane] = attempts.get(lane, 0) + 1
            plan_file = lane / ".qwenstorm" / "plan.md"
            if not plan_file.is_file():
                continue
            yield self._one(run_dir, lane, plan_file.read_text(encoding="utf-8"), attempts[lane])

    def _one(self, run_dir: Path, lane: Path, plan: str, attempt: int) -> dict[str, Any]:
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        window = int(meta.get("context_window") or 65536)
        cwd = Path(meta.get("cwd") or lane)
        if attempt > 1:
            plan += self._repair.format(attempt=attempt, max_attempts=self._max_attempts)
        q = self._q
        r, message = q.runner, q.message
        transcript = [message("system", r._system_prompt(cwd)), message("user", plan)]
        preamble = [q.native(m) for m in transcript]
        turns: list[dict[str, Any]] = []
        texts: list[str] = []
        results: list[tuple[str, Any]] = []
        before: list[Any] = []
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            kind = event.get("type")
            if kind == "text_delta":
                texts.append(str(event.get("text", "")))
            elif kind == "tool_result":
                results.append((str(event.get("name", "")), event.get("result")))
            elif kind == "turn.retried":
                before.append(message("user", r._TOOL_CALL_RETRY_PROMPT))
            elif kind == "turn.completed":
                # What the runner sent this turn: the transcript, trimmed as it trimmed it,
                # with any retry prompt this turn appended before the call that answered.
                sent_base = r._trim_transcript(transcript, window)
                sent = [*sent_base, *before]
                entry: dict[str, Any] = {
                    "turn": int(event.get("turn", len(turns) + 1)),
                    "recorded_input_tokens": int(event.get("input_tokens", 0)),
                    "recorded_output_tokens": int(event.get("output_tokens", 0)),
                    "recorded_model_ms": int(event.get("model_ms", 0)),
                    "before": [q.native(m) for m in before],
                }
                if len(sent_base) != len(transcript):
                    entry["messages"] = [q.native(m) for m in sent]
                transcript = sent
                answer = "".join(texts)
                # What the runner appended once the answer came (runner.py, after the stream):
                # the assistant message with its tool calls, each tool result truncated as it
                # truncates them, then the invalid-completion or continue prompt.
                after: list[tuple[Any, str | None]] = []
                if results:
                    calls = tuple(
                        {
                            "id": f"t{entry['turn']}c{i}",
                            "type": "function",
                            "function": {"name": name, "arguments": "{}"},
                        }
                        for i, (name, _) in enumerate(results)
                    )
                    after.append((message("assistant", answer, tool_calls=calls), None))
                    for (name, result), call in zip(results, calls, strict=True):
                        text = r._truncate_tool_result(str(result))
                        after.append((message("tool", text, tool_call_id=call["id"]), name))
                elif answer:
                    after.append((message("assistant", answer), None))
                if q.done in answer:
                    after.append((message("user", r._INVALID_COMPLETION_PROMPT), None))
                elif after and after[-1][0].role == "assistant":
                    after.append((message("user", r._CONTINUE_PROMPT), None))
                entry["after"] = [q.native(m, name) for m, name in after]
                transcript = [*transcript, *(m for m, _ in after)]
                turns.append(entry)
                texts, results, before = [], [], []
        return {
            "schema": POOL_SCHEMA,
            "run": str(meta.get("run_id", run_dir.name)),
            "source": str(run_dir),
            "tools": q.tools,
            "preamble": preamble,
            "turns": turns,
            "notes": [ARGUMENTS_NOTE],
        }


class SpecTurnPool(SpecTurnPoolInterface):
    """Storm-shaped runs from the storm's committed specs and the repository's own files."""

    #: Where the storm's lanes read. Everything tracked here is text a lane could read.
    READABLE = re.compile(r"^(src|tests|docs|deploy|scripts)/.+\.(py|md|toml|ya?ml|sh|json)$")
    MENTIONED = re.compile(r"`?((?:src|tests|docs|deploy|scripts)/[\w./-]+\.\w+)`?")

    def __init__(
        self,
        qwenloop_src: Path,
        repo: Path,
        *,
        seed: int = 0,
        context_window: int = 65536,
        response_reserve: int = 2048,
        author: str = "Adam Matthew Steinberger",
    ) -> None:
        self._q = QwenloopRunner(qwenloop_src)
        from qwenloop.application.storm import build_plan
        from qwenloop.domain.model import RepoItem

        self._build_plan = build_plan
        self._item = RepoItem
        self._repo = repo
        self._rng = random.Random(seed)
        self._budget_chars = (context_window - response_reserve) * CHARS_PER_TOKEN
        self._author = author
        rules = repo / "docs/plans/qwenstorm-3.0.0/EDITING-RULES.md"
        self._rules = rules.read_text(encoding="utf-8") if rules.is_file() else ""
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.splitlines()
        self._files = sorted(path for path in tracked if self.READABLE.match(path))
        self.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    @staticmethod
    def depth(messages: list[dict[str, Any]]) -> int:
        """Characters / 3 over what is sent: a conservative estimate, never a measurement."""
        return sum(len(json.dumps(message)) for message in messages) // CHARS_PER_TOKEN

    def _reads(self, spec_text: str) -> list[str]:
        """The files the spec names first, in its order; then others, seeded."""
        named = [p for p in self.MENTIONED.findall(spec_text) if p in self._files]
        rest = [p for p in self._files if p not in named]
        self._rng.shuffle(rest)
        return list(dict.fromkeys(named)) + rest

    def build(self, specs: list[Path]) -> Iterator[dict[str, Any]]:
        q = self._q
        r, message = q.runner, q.message
        for number, spec in enumerate(specs, start=1):
            text = spec.read_text(encoding="utf-8")
            title = next(
                (line.lstrip("# ").strip() for line in text.splitlines() if line.strip()), spec.stem
            )
            plan = self._build_plan(
                repo="vibey",
                issues=[self._item(number=number, title=title, body=text + self._rules)],
                pull_requests=[],
                author=self._author,
            )
            cwd = self._repo / "lanes" / spec.stem
            preamble = [
                q.native(message("system", r._system_prompt(cwd))),
                q.native(message("user", plan)),
            ]
            sent = list(preamble)
            turns: list[dict[str, Any]] = []
            for path in self._reads(text):
                depth = self.depth(sent)
                result = {
                    "content": (self._repo / path).read_text(encoding="utf-8", errors="replace")
                }
                call = {
                    "id": f"t{len(turns) + 1}c0",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": json.dumps({"path": path})},
                }
                after = [
                    q.native(message("assistant", "", tool_calls=(call,))),
                    q.native(
                        message(
                            "tool", r._truncate_tool_result(str(result)), tool_call_id=call["id"]
                        ),
                        "read_file",
                    ),
                ]
                if (depth + self.depth(after)) * CHARS_PER_TOKEN > self._budget_chars:
                    break
                turns.append(
                    {
                        "turn": len(turns) + 1,
                        "recorded_input_tokens": depth,
                        "recorded_output_tokens": 0,
                        "before": [],
                        "after": after,
                    }
                )
                sent.extend(after)
            yield {
                "schema": POOL_SCHEMA,
                "run": f"spec:{spec.stem}",
                "source": f"{spec.relative_to(self._repo)}@{self.commit[:12]}",
                "tools": q.tools,
                "preamble": preamble,
                "turns": turns,
                "notes": [SPECS_NOTE],
            }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", choices=("lanes", "specs"))
    storm = HERE.parent
    parser.add_argument("--lanes", type=Path, default=storm / "lanes")
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--qwenloop-src", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=40, help="specs mode: how many specs")
    parser.add_argument("--seed", type=int, default=0, help="specs mode: which specs and files")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.source == "lanes":
        src = args.qwenloop_src or storm / "integration/src/vibey_runners/qwen/src"
        pool = QwenloopTurnPool(src)
        lines: Iterable[dict[str, Any]] = pool.build(pool.runs(args.lanes))
    else:
        src = args.qwenloop_src or args.repo / "src/vibey_runners/qwen/src"
        specs = sorted((args.repo / "docs/plans/qwenstorm-3.0.0/specs").glob("*.md"))
        random.Random(args.seed).shuffle(specs)
        lines = SpecTurnPool(src, args.repo, seed=args.seed).build(specs[: args.runs])
    count = turns = 0
    with args.out.open("w", encoding="utf-8") as out:
        for line in lines:
            out.write(json.dumps(line, sort_keys=True) + "\n")
            count += 1
            turns += len(line["turns"])
    print(f"{count} runs, {turns} turns -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
