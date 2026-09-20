# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ledger export` and `vibey ledger site`: publish a project's ledger.

Sub-doctrine 7.a says anyone can search the ledger -- the full ledger where a
deployment holds it, or the shard a repository holds. These two commands make the
shard and the static surface built from it:

- `vibey ledger export PROJECT --out FILE` reads the project's whole ledger (it
  needs the database), runs every event through the default-deny publication
  policy with credential redaction on top, and writes the shard: a header line,
  then the published records. It prints how many events it published, how many
  the policy withheld and why, what it removed from inside published records,
  and the ledger's chain head.
- `vibey ledger site --from FILE --out DIR --json-only` needs no database. It
  checks the shard and writes `records/<event_id>.json`, `index.json` and
  `manifest.json`. `--json-only` is required for now: the human-first record
  pages come next, and a script written today must not change meaning the day
  they arrive.
"""

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.interfaces import (
    LedgerExporterInterface,
    LedgerShardInterface,
    LedgerShardStore,
    LedgerSiteBuilderInterface,
    LedgerSitePlanInterface,
    LedgerSiteWriter,
    ShardHeaderInterface,
)
from vibey.application.ledger_publication import (
    InvalidLedgerShard,
    LedgerExporter,
    LedgerSiteBuilder,
)
from vibey.bootstrap import AppResources, build_app
from vibey.cli.interfaces.ledger_publication_interface import (
    LedgerExportCommandInterface,
    LedgerSiteCommandInterface,
    PublicationPresenterInterface,
)
from vibey.domain.interfaces.ledger_chain_interface import LedgerChainInterface
from vibey.domain.interfaces.publication_policy_interface import PublicationPolicyInterface
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.publication_policy import (
    BILLING_POLICY,
    DEFAULT_RULES,
    PublicationPolicy,
    WithheldReason,
)
from vibey.infrastructure.ledger.redact import CREDENTIAL_REDACTOR
from vibey.infrastructure.ledger.static_export import JsonlShardStore, StaticSiteWriter

PUBLIC_POLICY: Final[PublicationPolicyInterface] = PublicationPolicy(
    DEFAULT_RULES, redactor=CREDENTIAL_REDACTOR
)
"""The default-deny rules with credential redaction on top: what `export` applies."""

SHARD_STORE: Final[LedgerShardStore] = JsonlShardStore()
SITE_WRITER: Final[LedgerSiteWriter] = StaticSiteWriter()


class PublicationPresenter:
    """Says what was published and what was withheld, in lines a person reads."""

    def exported(self, shard: LedgerShardInterface, out: Path) -> list[str]:
        header = shard.header
        return [
            f"exported {header.published_count} of {header.ledger_event_count} ledger "
            f"event(s) of project {header.project_name} ({header.project_id}) to {out}",
            *self._withheld(header),
            self._chain(header),
        ]

    def built(self, plan: LedgerSitePlanInterface, out: Path) -> list[str]:
        header = plan.shard.header
        return [
            f"built the JSON surface of project {header.project_name} ({header.project_id}) "
            f"in {out}: {header.published_count} record document(s), an index and a manifest",
            *self._withheld(header),
        ]

    @staticmethod
    def _withheld(header: ShardHeaderInterface) -> list[str]:
        count = header.events_withheld
        reasons = ", ".join(
            f"{header.withheld.get(reason, 0)} {reason.value.replace('_', ' ')}"
            for reason in WithheldReason
        )
        trimmed = header.trimmed
        return [
            f"{count} event{'' if count == 1 else 's'} withheld by policy ({reasons})",
            f"from published records: {trimmed.fields} field(s) withheld, {trimmed.paths} "
            f"absolute path(s) and {trimmed.emails} email address(es) stripped, "
            f"{trimmed.credentials} record(s) with a credential redacted",
        ]

    @staticmethod
    def _chain(header: ShardHeaderInterface) -> str:
        where = (
            "at genesis (the ledger is empty)"
            if header.ledger_last_seq is None
            else f"at seq {header.ledger_last_seq}"
        )
        if header.chain_findings:
            return (
                f"chain head {header.chain_head} {where}: the ledger's chain walk found "
                f"{header.chain_findings} disagreement(s), so the head is published unverified"
            )
        return f"chain head {header.chain_head} {where}, verified"


PRESENTER: Final[PublicationPresenterInterface] = PublicationPresenter()


class LedgerExportCommand:
    """Resolves the project, exports its shard, prints what happened."""

    def __init__(
        self,
        *,
        policy: PublicationPolicyInterface = PUBLIC_POLICY,
        store: LedgerShardStore = SHARD_STORE,
        chain: LedgerChainInterface = LEDGER_CHAIN,
        presenter: PublicationPresenterInterface = PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
        billing_policy: PublicationPolicyInterface = BILLING_POLICY,
    ) -> None:
        self._policy = policy
        self._store = store
        self._chain = chain
        self._presenter = presenter
        self._open_app = open_app
        self._billing_policy = billing_policy

    async def run(self, project_id: UUID, out: Path, *, billing: bool = False) -> None:
        async with self._open_app() as resources:
            project = await resources.projects.get(project_id)
            if project is None:
                typer.echo(f"unknown project {project_id}")
                raise typer.Exit(1)
            policy = self._billing_policy if billing else self._policy
            exporter: LedgerExporterInterface = LedgerExporter(
                ledger=resources.ledger, store=self._store, policy=policy, chain=self._chain
            )
            # The name and the id, never the row: `repo_path` is never published.
            shard = await exporter.export(project.project_id, project.name, out)
        typer.echo("\n".join(self._presenter.exported(shard, out)))


class LedgerSiteCommand:
    """Builds the static JSON surface from a shard file. Opens no database."""

    def __init__(
        self,
        *,
        store: LedgerShardStore = SHARD_STORE,
        writer: LedgerSiteWriter = SITE_WRITER,
        presenter: PublicationPresenterInterface = PRESENTER,
    ) -> None:
        self._store = store
        self._writer = writer
        self._presenter = presenter

    def run(self, source: Path, out: Path, *, json_only: bool) -> None:
        if not json_only:
            # A usage error, exit 2 -- the same code typer gives its own checks.
            raise typer.BadParameter(
                "the human-first record pages are not built yet; pass --json-only to "
                "build the JSON surface (one document per record, an index, a manifest)",
                param_hint="--json-only",
            )
        builder: LedgerSiteBuilderInterface = LedgerSiteBuilder(
            store=self._store, writer=self._writer
        )
        try:
            plan = builder.build(source, out)
        except InvalidLedgerShard as exc:
            typer.echo(f"invalid shard {source}: {exc}")
            raise typer.Exit(1) from exc
        typer.echo("\n".join(self._presenter.built(plan, out)))


LEDGER_EXPORT: Final[LedgerExportCommandInterface] = LedgerExportCommand()
"""The command `vibey ledger export` runs. Annotated with the interface so `mypy
--strict` checks the class against its declared seam."""

LEDGER_SITE: Final[LedgerSiteCommandInterface] = LedgerSiteCommand()
"""The command `vibey ledger site` runs."""


def ledger_export(
    project_id: Annotated[UUID, typer.Argument(help="The project whose ledger to publish.")],
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            "-o",
            dir_okay=False,
            help="The shard file to write (JSON Lines). Replaced if it exists.",
        ),
    ],
    billing: Annotated[
        bool,
        typer.Option(
            "--billing",
            help="Write the operator-scoped billing projection for vibey-gh forecast.",
        ),
    ] = False,
) -> None:
    """Write a project's public shard, or the explicit operator billing projection."""
    # A module-level function because typer builds a command's options from a
    # plain function's signature. It holds no logic; the command class does.
    asyncio.run(LEDGER_EXPORT.run(project_id, out, billing=billing))


def ledger_site(
    source: Annotated[
        Path,
        typer.Option(
            "--from",
            exists=True,
            dir_okay=False,
            readable=True,
            help="A shard file written by `vibey ledger export`.",
        ),
    ],
    out: Annotated[
        Path,
        typer.Option("--out", "-o", file_okay=False, help="The directory to write the site into."),
    ],
    json_only: Annotated[
        bool,
        typer.Option(
            "--json-only",
            help="Build the JSON surface: records/<event_id>.json, index.json, manifest.json. "
            "Required until the human-first record pages exist.",
        ),
    ] = False,
) -> None:
    """Build the static site of a published shard. Needs no database."""
    # A module-level function because typer builds a command's options from a
    # plain function's signature. It holds no logic; the command class does.
    LEDGER_SITE.run(source, out, json_only=json_only)
