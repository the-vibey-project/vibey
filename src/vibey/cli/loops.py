# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey loops`: the two loops, their engines by effort, and what each can do.

What a person or an editor needs to pick a loop, then an effort, then a model, and to run an
engine within one tier: every engine vibey knows grouped by the loop its tier puts it in
(sub-doctrine 8.c), every effort with the argv it passes and what it really achieves, the
escalation ladder, and each engine's run, control and event facts and the environment
names it reads. All of it is data vibey already holds -- the descriptors, the effort
vocabulary, and the local switches read as `vibey doctor` reads them (the environment
first, then `./vibey.toml`) -- so it needs no database and no network. The human reading
comes first; `--json` is the document the VS Code extension reads (doctrine 7).
"""

import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import typer

from vibey.application.dto import EffortRun, EngineContext, LoopEngine, LoopsReport, LoopView
from vibey.application.interfaces.loops import LoopCatalogInterface
from vibey.application.loops import LOOP_CATALOG
from vibey.cli.interfaces.loops_interface import LoopsCommandInterface, LoopsPresenterInterface
from vibey.domain.config import ConfigError
from vibey.domain.engine import EngineAffordances, EngineDescriptor
from vibey.infrastructure.engines.argv import RUN_ARGV_TEMPLATE
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS
from vibey.infrastructure.engines.interfaces.argv_interface import RunArgvTemplateInterface
from vibey.infrastructure.engines.interfaces.local_engines_interface import (
    LocalEndpointEnvironmentInterface,
    LocalEngineSettingsInterface,
)
from vibey.infrastructure.engines.local_engines import LocalEndpointEnvironment, LocalEngineSettings

MALFORMED_SETTING: Final = (
    "is malformed; `vibey loops` names the setting and never prints its value, which can "
    "carry a credential (a URL's user:token@)"
)
"""Why `vibey loops` stopped, said without the setting's value (contract amendment 6)."""


class LoopsPresenter:
    """Renders the loops as a small table per loop for a person, or as JSON for a program."""

    def lines(self, report: LoopsReport) -> list[str]:
        lines: list[str] = []
        for view in report.loops:
            lines += [*self._loop_lines(view, report), ""]
        lines.append(
            f"Canon 8.b names {report.paid_default_engine.value} the paid default; the "
            "selector does not apply it yet, and rotates paid engines by weight. "
            "`vibey loops --json` has every engine's full facts."
        )
        return lines

    def json(self, report: LoopsReport) -> str:
        return json.dumps(self._document(report), indent=2)

    def _loop_lines(self, view: LoopView, report: LoopsReport) -> list[str]:
        standing = (
            "the default loop by canon 8.b; a local engine runs only while its switch is on"
            if view.default
            else "declared only by canon 8.b; the selector does not read a paid declaration "
            "yet, and picks a paid engine whenever no local engine is eligible"
        )
        lines = [f"{view.loop.value} (tier {view.tier.value}): {standing}"]
        if not view.engines:
            return [*lines, "  no engines"]
        rows = [
            ["", *(engine.descriptor.engine_id.value for engine in view.engines)],
            ["switched on", *("yes" if engine.enabled else "no" for engine in view.engines)],
            [
                "$ per Mtok in/out",
                *(
                    f"{e.descriptor.cost_per_mtok_in:.2f}/{e.descriptor.cost_per_mtok_out:.2f}"
                    for e in view.engines
                ),
            ],
            ["model", *(engine.default_model or "-" for engine in view.engines)],
            *(
                [effort.name, *(self._cell(engine.efforts[index]) for engine in view.engines)]
                for index, effort in enumerate(report.efforts)
            ),
        ]
        widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
        lines += [
            "  " + "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
            for row in rows
        ]
        lines = [line.rstrip() for line in lines]
        for engine in view.engines:
            name = engine.descriptor.engine_id.value
            if engine.switch is not None and engine.on_by_default:
                lines.append(
                    f"  {name} is on unless switched off by {engine.switch}=0, or by its key "
                    "under [features] in vibey.toml"
                )
            elif engine.switch is not None:
                lines.append(
                    f"  {name} is switched on by {engine.switch}=1, or by its key under "
                    "[features] in vibey.toml"
                )
            lines += [f"  note on {name}: {note}" for note in engine.notes]
        return lines

    @staticmethod
    def _cell(run: EffortRun) -> str:
        """What one effort passes, its flags without their dashes, and what it really
        achieves when that is not what was asked."""
        passed = " ".join(token.removeprefix("--") for token in run.argv) or "(no flags)"
        return passed if run.achieved == run.effort else f"{passed} -> {run.achieved.name}"

    def _document(self, report: LoopsReport) -> dict[str, object]:
        return {
            "efforts": [effort.name for effort in report.efforts],
            "default_loop": report.default_loop.value,
            "paid_default_engine": report.paid_default_engine.value,
            "paid_default": report.paid_default_engine.value,
            "ladder": {
                "phase_base": {
                    phase.name: effort.name for phase, effort in report.ladder.phase_base.items()
                },
                "build_attempts": [effort.name for effort in report.ladder.build_attempts],
                "exhausted_after": report.ladder.exhausted_after,
                "rotates_when_effort_rises": report.ladder.rotates_when_effort_rises,
            },
            "loops": [self._loop(view) for view in report.loops],
        }

    def _loop(self, view: LoopView) -> dict[str, object]:
        return {
            "loop": view.loop.value,
            "tier": view.tier.value,
            "default": view.default,
            "declared_only": view.declared_only,
            "engines": [self._engine(engine) for engine in view.engines],
            "by_effort": {
                effort.name: [
                    {
                        "engine_id": choice.engine_id.value,
                        "model": choice.model,
                        "achieved": choice.achieved.name,
                    }
                    for choice in choices
                ]
                for effort, choices in view.by_effort.items()
            },
        }

    def _engine(self, engine: LoopEngine) -> dict[str, object]:
        descriptor = engine.descriptor
        return {
            "engine_id": descriptor.engine_id.value,
            "binary": descriptor.binary,
            "state_dir": descriptor.state_dir,
            "enabled": engine.enabled,
            "switch": engine.switch,
            "on_by_default": engine.on_by_default,
            "repealed": engine.repealed,
            "cost_per_mtok_in": descriptor.cost_per_mtok_in,
            "cost_per_mtok_out": descriptor.cost_per_mtok_out,
            "default_model": engine.default_model,
            "efforts": [
                {
                    "effort": run.effort.name,
                    "argv": list(run.argv),
                    "achieved": run.achieved.name,
                    "model": run.model,
                    "notes": run.notes,
                }
                for run in engine.efforts
            ],
            "capabilities": self._capabilities(descriptor.affordances),
            "done_marker": descriptor.done_marker,
            "plan_flag": descriptor.plan_flag,
            "supports_cwd_flag": descriptor.supports_cwd_flag,
            "base_weight": descriptor.base_weight,
            "run": list(engine.run),
            "controls": self._controls(descriptor),
            "events": {
                "path": descriptor.events.path,
                "envelope": (
                    descriptor.events.envelope.value
                    if descriptor.events.envelope is not None
                    else None
                ),
            },
            # Names only, as declared: the command never reads a variable's value.
            "env": {
                "auth": list(descriptor.auth_env),
                "passthrough": list(descriptor.env_passthrough),
            },
            "notes": list(engine.notes),
        }

    @staticmethod
    def _capabilities(affordances: EngineAffordances) -> dict[str, object]:
        return {
            "images": affordances.images,
            "files": affordances.files,
            "paste_text": affordances.paste_text,
            "paste_images": affordances.paste_images,
            "plugins": affordances.plugins.value if affordances.plugins is not None else None,
            "mcp": affordances.mcp,
            "evidence": dict(affordances.evidence),
        }

    @staticmethod
    def _controls(descriptor: EngineDescriptor) -> dict[str, object]:
        controls = descriptor.controls
        return {
            verb: list(argv) if argv is not None else None
            for verb, argv in (
                ("stop", controls.stop),
                ("wind_down", controls.wind_down),
                ("prompt", controls.prompt),
            )
        }


LOOPS_PRESENTER: Final[LoopsPresenterInterface] = LoopsPresenter()


class LoopsCommand:
    """Reads each engine as vibey's own resolvers see it right now, asks the one catalog to
    assemble the loops, prints.

    The resolvers are the ones `vibey doctor` reads: `settings` for the local switches and
    the claudeloop-local profile, `endpoint` for the model vibey hands a local engine. Left
    out, they are built when the command runs, from this process's environment and
    `./vibey.toml`.
    """

    def __init__(
        self,
        *,
        catalog: LoopCatalogInterface = LOOP_CATALOG,
        presenter: LoopsPresenterInterface = LOOPS_PRESENTER,
        templates: RunArgvTemplateInterface = RUN_ARGV_TEMPLATE,
        descriptors: Sequence[EngineDescriptor] = ALL_DESCRIPTORS,
        settings: LocalEngineSettingsInterface | None = None,
        endpoint: LocalEndpointEnvironmentInterface | None = None,
    ) -> None:
        self._catalog = catalog
        self._presenter = presenter
        self._templates = templates
        self._descriptors = descriptors
        self._settings = settings
        self._endpoint = endpoint

    def run(self, *, as_json: bool) -> None:
        try:
            contexts = self._contexts()
        except ConfigError as exc:
            # Named, never shown: the setting's value can carry a credential, and this
            # message reaches a terminal. `from None` keeps the original out of a traceback.
            raise ConfigError(exc.path, MALFORMED_SETTING) from None
        report = self._catalog.report(contexts)
        if as_json:
            typer.echo(self._presenter.json(report))
        else:
            typer.echo("\n".join(self._presenter.lines(report)))

    def _contexts(self) -> list[EngineContext]:
        """Every engine as `vibey doctor` would resolve it here: a local engine through its
        switch and the configured claudeloop-local profile, every other one as declared."""
        settings: LocalEngineSettingsInterface = (
            self._settings
            if self._settings is not None
            else LocalEngineSettings.from_toml(Path.cwd() / "vibey.toml", environ=os.environ)
        )
        endpoint: LocalEndpointEnvironmentInterface = (
            self._endpoint if self._endpoint is not None else LocalEndpointEnvironment(os.environ)
        )
        contexts: list[EngineContext] = []
        for declared in self._descriptors:
            switch = settings.switch_for(declared.engine_id)
            descriptor = declared if switch is None else settings.descriptor(declared.engine_id)
            contexts.append(
                EngineContext(
                    descriptor=descriptor,
                    # An engine with no switch is listed as on: the selector may pick it
                    # whenever it is eligible. Listing it does not select it.
                    enabled=switch is None or settings.enabled(declared.engine_id),
                    run=self._templates.template(descriptor),
                    switch=switch,
                    model=endpoint.model_for(declared.engine_id),
                    on_by_default=settings.on_by_default(declared.engine_id),
                )
            )
        return contexts


LOOPS: Final[LoopsCommandInterface] = LoopsCommand()
"""The command `vibey loops` runs. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
