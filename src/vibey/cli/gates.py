# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey gates`: every open gate, oldest first, with the command that answers it.

A gate is a job parked on a question only a person can answer (ADR-0009). Finding one used
to take a SQL query against `human_gate`. This lists them instead -- every project's, or
one project's -- with the project's name, the gate's kind and prompt, and `answer_with`,
the exact `vibey answer` command for it (`vibey.cli.gate_answers`). The human reading comes
first; `--json` is the same list for a program, `{"gates": [...]}`, and the VS Code
extension reads its keys (doctrine 7).
"""

import json
import textwrap
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC
from typing import Final
from uuid import UUID

import typer

from vibey.application.dto import HumanGateRecord, ProjectRecord
from vibey.bootstrap import AppResources, build_app
from vibey.cli.gate_answers import GATE_ANSWERS
from vibey.cli.interfaces.gate_answers_interface import GateAnswerCommandsInterface
from vibey.cli.interfaces.gates_interface import GatesCommandInterface, GatesPresenterInterface

DEFAULT_PROMPT_WIDTH: Final = 80
"""The column a gate's prompt is wrapped at in the human reading. The command line never
wraps: it has to paste as one line."""


class GatesPresenter:
    """Renders open gates as numbered paragraphs for a person, or as JSON for a program."""

    def __init__(
        self,
        *,
        answers: GateAnswerCommandsInterface = GATE_ANSWERS,
        width: int = DEFAULT_PROMPT_WIDTH,
    ) -> None:
        self._answers = answers
        self._width = width

    def gates(
        self,
        gates: Sequence[HumanGateRecord],
        names: Mapping[UUID, str],
        *,
        scope: str | None = None,
    ) -> list[str]:
        where = "" if scope is None else f" for project {scope}"
        if not gates:
            return [f"no open gates{where}: nothing is waiting for your answer"]
        count = len(gates)
        lines = [
            f"{count} open gate{'' if count == 1 else 's'}{where}, oldest first -- each is a "
            "job waiting for your answer:"
        ]
        for number, gate in enumerate(gates, start=1):
            lines += ["", *self._gate(number, gate, names[gate.project_id])]
        return lines

    def gates_json(self, gates: Sequence[HumanGateRecord], names: Mapping[UUID, str]) -> str:
        return json.dumps(
            {"gates": [self._record(gate, names[gate.project_id]) for gate in gates]}, indent=2
        )

    def _gate(self, number: int, gate: HumanGateRecord, name: str) -> list[str]:
        indent = " " * (len(str(number)) + 2)
        raised = gate.raised_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"{number}. {name}: {gate.kind} gate, raised {raised}",
            self._paragraph(gate.prompt, indent),
            f"{indent}answer with: {self._answers.command(gate)}",
        ]
        note = self._answers.rule(gate.kind).fill_in(gate)
        if note is not None:
            lines.append(f"{indent}(replace {note} before you run it)")
        return lines

    def _paragraph(self, prompt: str, indent: str) -> str:
        """The prompt as one paragraph: its line breaks and runs of spaces become single
        spaces, and it is wrapped without splitting a word, so a URL or an id survives."""
        text = " ".join(prompt.split())
        if not text:
            return f"{indent}(no prompt)"
        return textwrap.fill(
            text,
            width=self._width,
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )

    def _record(self, gate: HumanGateRecord, name: str) -> dict[str, object]:
        return {
            "gate_id": str(gate.gate_id),
            "project_id": str(gate.project_id),
            "project_name": name,
            "job_id": str(gate.job_id) if gate.job_id is not None else None,
            "kind": gate.kind,
            "prompt": gate.prompt,
            "options": list(gate.options),
            "default_answer": gate.default_answer,
            "raised_at": gate.raised_at.isoformat(),
            "timeout_at": gate.timeout_at.isoformat() if gate.timeout_at is not None else None,
            "answer_with": self._answers.command(gate),
        }


GATES_PRESENTER: Final[GatesPresenterInterface] = GatesPresenter()


class GatesCommand:
    """Reads the open gates -- every project's, or one project's -- and prints them."""

    def __init__(
        self,
        *,
        presenter: GatesPresenterInterface = GATES_PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._open_app = open_app

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None:
        scope: str | None = None
        projects: Sequence[ProjectRecord]
        async with self._open_app() as resources:
            if project_id is None:
                # Gates first: a gate never outlives its project (ON DELETE CASCADE), so
                # every project a gate read here names is still there to be read next.
                gates = await resources.gates.open_all()
                projects = await resources.projects.list_all()
            else:
                project = await resources.projects.get(project_id)
                if project is None:
                    # stderr, so a `--json` reader's stdout is never anything but JSON.
                    typer.echo(f"unknown project {project_id}", err=True)
                    raise typer.Exit(1)
                scope = project.name
                gates = await resources.gates.open_for_project(project_id)
                projects = (project,)
        names = {project.project_id: project.name for project in projects}
        # A gate whose project was deleted between the two reads went with it: it is no
        # longer waiting on anyone, so it is not listed.
        listed = tuple(gate for gate in gates if gate.project_id in names)
        if as_json:
            typer.echo(self._presenter.gates_json(listed, names))
        else:
            typer.echo("\n".join(self._presenter.gates(listed, names, scope=scope)))


GATES: Final[GatesCommandInterface] = GatesCommand()
"""The command `vibey gates` runs. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
