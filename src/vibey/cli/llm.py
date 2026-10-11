# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey llm`: the conversation with the local model, as it happens, in every phase.

`vibey llm tail` follows the wire log (`-vvv`, or `VIBEY_LLM_WIRE_LOG=path`): each request the
sovereign DESIGN and DECOMPOSE providers send, the answer and the reasoning as they stream
back, and the model's own counts and timings. BUILD and REVIEW run in an engine's own process,
so the worker notes each engine session in the same log, and the tail follows that session's
events too (every tool call and its result, the streamed answer, the reasoning, each turn's
time and tokens). It moves to the next session by itself when one starts. It only reads."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV, default_wire_log_path
from vibey.infrastructure.engines.wire_log_reader import (
    RunEventFormatter,
    WireFormatter,
    follow_live,
    last_session_index,
    session_events,
    snapshot,
    start_of_latest_call,
)

llm_app = typer.Typer(name="llm", no_args_is_help=True, help="The conversation with the model.")


def wire_log_path(explicit: Path | None) -> Path:
    """The file to read: `--file`, else `VIBEY_LLM_WIRE_LOG`, else where `-vvv` writes."""
    if explicit is not None:
        return explicit
    declared = os.environ.get(WIRE_LOG_ENV, "").strip()
    return Path(declared).expanduser() if declared else default_wire_log_path()


@llm_app.command("tail")
def tail(
    file: Annotated[
        Path | None,
        typer.Option(
            "--file", help="The wire log (default: VIBEY_LLM_WIRE_LOG, else the -vvv log)"
        ),
    ] = None,
    all_calls: Annotated[
        bool,
        typer.Option("--all", help="Start from the beginning of the file, not the latest call"),
    ] = False,
    follow: Annotated[
        bool,
        typer.Option("--follow/--no-follow", help="Keep following as the log grows (default)"),
    ] = True,
    raw: Annotated[bool, typer.Option("--raw", help="Print the JSON lines as written")] = False,
    max_chars: Annotated[
        int | None,
        typer.Option("--max-chars", min=1, help="Cut each prompt message to this many characters"),
    ] = None,
) -> None:
    """Follow the conversation with the local model, in every phase, as it happens.

    Starts at the latest call or engine session and keeps going until interrupted, switching
    to each new engine session by itself. Run any `vibey` command with -vvv (or
    VIBEY_LLM_WIRE_LOG=path) in another terminal to fill the log."""
    path = wire_log_path(file)
    wire = WireFormatter(max_chars=max_chars)
    engine = RunEventFormatter(max_chars=max_chars)
    last: list[str] = []  # which stream wrote last: "wire" or "run"

    def show(source: str, record: dict[str, object]) -> None:
        if raw:
            typer.echo(json.dumps(record, ensure_ascii=False))
            return
        if last and last[-1] != source:
            # Output moves between streams: end the answer the other one left open.
            typer.echo((wire if last[-1] == "wire" else engine).close(), nl=False)
        last[:] = [source]
        typer.echo((wire if source == "wire" else engine).render(record), nl=False)

    offset = 0
    session: dict[str, object] | None = None
    session_offset = 0
    if path.exists():
        records, offset = snapshot(path)
        newest = last_session_index(records) or 0
        first = 0 if all_calls else max(start_of_latest_call(records), newest)
        for record in records[first:]:
            show("wire", record)
            if record.get("kind") == "session":
                events, session_offset = session_events(record)
                session = record
                for event in events:
                    show("run", event)
    elif follow:
        typer.echo(f"waiting for {path} (run a vibey command with -vvv)", err=True)
    else:
        typer.echo(f"no wire log at {path}; run a vibey command with -vvv first", err=True)
        raise typer.Exit(1)
    if not follow:
        return
    try:
        for source, record, _ in follow_live(
            path, offset, session=session, session_offset=session_offset
        ):
            show(source, record)
    except KeyboardInterrupt:
        typer.echo("")
