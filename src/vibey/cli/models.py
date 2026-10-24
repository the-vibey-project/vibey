# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey models`: the local model families, and what the Ollama on this machine says about them.

Two halves. The families are data vibey holds (ADR-0093): each with the Ollama tag to start
from and the command that fetches it, so they need no network. The installed models come
from the Ollama at `VIBEY_OLLAMA_URL`, with the capabilities that Ollama itself reports for
each, because tool-calling cannot be read off a model's name or template. No Ollama is
reported, not fatal: the families still print. The human reading comes first; `--json` is
the same facts for a program.
"""

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final

import typer

from vibey.cli.interfaces.models_interface import ModelsCommandInterface, ModelsPresenterInterface
from vibey.domain.interfaces.model_families_interface import ModelFamiliesInterface
from vibey.domain.model_families import MODEL_FAMILY_CATALOG
from vibey.infrastructure.interfaces.ollama_models_interface import OllamaModelsInterface
from vibey.infrastructure.ollama_models import DEFAULT_OLLAMA_URL, OllamaModels, OllamaUnavailable


@dataclass(frozen=True, slots=True)
class FamilyView:
    key: str
    label: str
    suggested_tag: str
    pull: str


@dataclass(frozen=True, slots=True)
class InstalledView:
    tag: str
    family: str | None
    size_gb: float
    capabilities: tuple[str, ...] | None
    jobs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelsReport:
    families: tuple[FamilyView, ...]
    ollama_url: str
    installed: tuple[InstalledView, ...]
    problem: str | None


class ModelsPresenter:
    def lines(self, report: ModelsReport) -> list[str]:
        lines = ["Model families (a starting tag for each; fetch it with the command shown):"]
        for family in report.families:
            lines.append(f"  {family.label:<15} {family.suggested_tag:<22} {family.pull}")
        lines += ["", f"Installed in the Ollama at {report.ollama_url}:"]
        if report.problem is not None:
            lines.append(f"  {report.problem}")
            return lines
        if not report.installed:
            lines.append("  no models yet")
        for model in report.installed:
            belongs = model.family or "outside the families above"
            lines.append(f"  {model.tag}  ({belongs}, {model.size_gb:.1f} GB)")
            if model.capabilities is None:
                lines.append("      this Ollama does not say what it can do: unknown")
                continue
            lines.append(f"      Ollama reports: {', '.join(model.capabilities) or 'nothing'}")
            lines += [f"      can be tried for: {job}" for job in model.jobs]
        lines += ["", "`vibey models --json` has the same facts for a program."]
        return lines

    def json(self, report: ModelsReport) -> str:
        return json.dumps(
            {
                "families": [vars_of(f) for f in report.families],
                "ollama_url": report.ollama_url,
                "problem": report.problem,
                "installed": [
                    {
                        "tag": m.tag,
                        "family": m.family,
                        "size_gb": m.size_gb,
                        "capabilities": None if m.capabilities is None else list(m.capabilities),
                        "jobs": list(m.jobs),
                    }
                    for m in report.installed
                ],
            },
            indent=2,
        )


def vars_of(family: FamilyView) -> dict[str, str]:
    return {
        "key": family.key,
        "label": family.label,
        "suggested_tag": family.suggested_tag,
        "pull": family.pull,
    }


class ModelsCommand:
    def __init__(
        self,
        *,
        families: ModelFamiliesInterface = MODEL_FAMILY_CATALOG,
        presenter: ModelsPresenterInterface | None = None,
        client_for: Callable[[str], OllamaModelsInterface] = OllamaModels,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._families = families
        self._presenter = presenter or ModelsPresenter()
        self._client_for = client_for
        self._environ = environ

    def run(self, *, as_json: bool) -> None:
        report = self.report()
        if as_json:
            typer.echo(self._presenter.json(report))
        else:
            typer.echo("\n".join(self._presenter.lines(report)))

    def report(self) -> ModelsReport:
        environ = os.environ if self._environ is None else self._environ
        url = environ.get("VIBEY_OLLAMA_URL") or DEFAULT_OLLAMA_URL
        views = tuple(
            FamilyView(f.key, f.label, f.suggested_tag, f"ollama pull {f.suggested_tag}")
            for f in self._families.all()
        )
        try:
            installed = self._client_for(url).installed()
        except OllamaUnavailable as exc:
            return ModelsReport(views, url, (), str(exc))
        found = []
        for model in installed:
            family = self._families.family_of(model.tag)
            capabilities = None if model.capabilities is None else tuple(sorted(model.capabilities))
            jobs = () if model.capabilities is None else self._families.jobs(model.capabilities)
            found.append(
                InstalledView(
                    model.tag,
                    None if family is None else family.label,
                    round(model.size_bytes / 1e9, 1),
                    capabilities,
                    jobs,
                )
            )
        return ModelsReport(views, url, tuple(found), None)


MODELS: Final[ModelsCommandInterface] = ModelsCommand()
"""The command `vibey models` runs, annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
