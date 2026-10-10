# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey llm`: the conversation with the local model, as it happens.

`vibey llm tail` follows the wire log (`-vvv`, or `VIBEY_LLM_WIRE_LOG=path`): each request
the sovereign DESIGN and DECOMPOSE providers send, the answer and the reasoning as they
stream back, and the model's own counts and timings. It only reads."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV, default_wire_log_path
from vibey.infrastructure.engines.wire_log_reader import (
    WireFormatter,
    follow_records,
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
    """Follow the conversation with the local model, token by token.

    Starts at the latest call and keeps going until interrupted. Run any `vibey` command
    with -vvv (or VIBEY_LLM_WIRE_LOG=path) in another terminal to fill the log."""
    path = wire_log_path(file)
    formatter = WireFormatter(max_chars=max_chars)

    def show(record: dict[str, object]) -> None:
        if raw:
            typer.echo(json.dumps(record, ensure_ascii=False))
        else:
            typer.echo(formatter.render(record), nl=False)

    offset = 0
    if path.exists():
        records, offset = snapshot(path)
        for record in records if all_calls else records[start_of_latest_call(records) :]:
            show(record)
    elif follow:
        typer.echo(f"waiting for {path} (run a vibey command with -vvv)", err=True)
    else:
        typer.echo(f"no wire log at {path}; run a vibey command with -vvv first", err=True)
        raise typer.Exit(1)
    if not follow:
        return
    try:
        for record in follow_records(path, offset):
            show(record)
    except KeyboardInterrupt:
        typer.echo("")
