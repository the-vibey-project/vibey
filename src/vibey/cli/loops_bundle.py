# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey loops marketplace | plugin | mcp | skills | snapshots`: what every loop is given
(SP-LOOPS Task 7; design Decisions 1, 3 and 9; ADR-0103).

- `marketplace add NAME SOURCE [--ref REF]` declares a marketplace in `[loops]`; nothing is
  fetched. `marketplace update [NAME]` fetches, checks and locks it (`vibey` re-hashes the one that
  ships in the wheel), and with no name does the shipped one and every declared one.
  `marketplace list` says what the lock holds of each, fetching and hashing nothing.
- `plugin add NAME@MARKETPLACE` and `plugin remove NAME` change `[loops] plugins` (the research
  default, `currency-research@vibey`, is written out the first time).
- `mcp add NAME --local -- CMD...` (the argv stored exactly, never through a shell) or
  `--remote URL` (`https://` only) adds an MCP server; `mcp list` prints them.
- `skills list` resolves the bundle as a run would, from the lock, with no network, and removes
  the listing's own snapshot afterwards; on a fresh install it lists the research skills.
- `snapshots prune` removes finished runs' snapshots older than an age.

**Whose files.** Every command reads and writes only the person's own `vibey.toml`
(`bootstrap.acp_user_config`, the one `UserConfigFolder.vibey_toml()`) and the store beside it
(`<their configuration folder>/loops`), never the folder it runs in, which may be a cloned
repository's. Only `marketplace update` of a git source reaches the network. A change is checked
whole with the bundle's own rule (`BundleSpec.from_mapping`, the reader every run uses) before it
is written, through the one table writer (`TomlTrustedTableWriter`: every byte outside `[loops]`
kept, 0600, atomic); a source and a ref are checked with `MarketplaceSourceRule` first.

**What a terminal sees.** Text that came from a marketplace or a remote -- skill names and
descriptions, skipped rows, git's last words -- is made one safe line with the resolver's own
cleaner (`SafeText`) before it is printed; `--json` prints the values as they are, typed.

Exit codes: 0 done; 1 a fetch, lock or run check failed, or nothing to act on; 2 a name, source,
ref, URL or command vibey refuses; 78 the person's `vibey.toml` cannot be read or rewritten (a
rewrite that would drop a comment prints the table to paste instead).
Declared by `interfaces/loops_bundle_interface.py::LoopsBundleCommandsInterface`.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Final

import typer
from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.defaults import (
    DEFAULT_MARKETPLACE_NAME,
    DEFAULT_RESEARCH_PLUGINS,
)
from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.interfaces.resolver_interface import (
    CapabilityResolverInterface,
)
from vibey_runners.common.capabilities.interfaces.safe_text_interface import SafeTextInterface
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.safe_text import SafeText
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot

from vibey.application.interfaces.loops_bundle_settings_interface import (
    LoopsBundleSettingsInterface,
)
from vibey.application.interfaces.trusted_table_reader_interface import (
    TrustedTableReaderInterface,
)
from vibey.bootstrap import (
    acp_user_config,
    loops_bundle_settings,
    loops_marketplace_store,
    loops_resolver,
    loops_shipped_source,
    loops_snapshot_pruner,
    loops_table_reader,
    loops_table_writer,
)
from vibey.cli.interfaces.loops_bundle_interface import LoopsBundleCommandsInterface
from vibey.domain.config import ConfigError
from vibey.domain.interfaces.marketplace_source_interface import MarketplaceSourceRuleInterface
from vibey.domain.marketplace_source import MARKETPLACE_SOURCE_RULE, MarketplaceSourceError
from vibey.infrastructure.interfaces.trusted_table_writer_interface import (
    TrustedTableWriterInterface,
)
from vibey.infrastructure.loops.interfaces.marketplace_store_interface import (
    MarketplaceStoreInterface,
)
from vibey.infrastructure.loops.interfaces.snapshot_pruner_interface import (
    SnapshotPrunerInterface,
)
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.snapshot_pruner import DEFAULT_AGE_DAYS

TABLE: Final = "loops"
EXIT_FAILED: Final = 1
EXIT_USAGE: Final = 2
EXIT_CONFIG: Final = 78
LINE_CHARS: Final = 300
"""The most of one marketplace- or remote-supplied text a printed line carries."""
DESCRIPTION_CHARS: Final = 120
"""The most of a skill description `skills list` prints (`--json` has all the run carries)."""
DAY_SECONDS: Final = 86_400
LOCKED: Final = "locked"
NOT_LOCKED: Final = "not locked"
STALE: Final = "lock pins another source or ref"
SHIPPED_FIRST: Final = "locks itself at first use"
SHIPPED_AGAIN: Final = "locks itself again at next use (a new release)"


class _Stop(Exception):
    """Ends a command with `code` after `message` is printed."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LoopsBundleCommands:
    """Declared by `LoopsBundleCommandsInterface`. Every collaborator is a seam; the defaults
    are the composition root's (`bootstrap.py`)."""

    def __init__(
        self,
        *,
        user_config: Callable[[], Path] = lambda: acp_user_config(),
        settings: LoopsBundleSettingsInterface | None = None,
        reader: TrustedTableReaderInterface | None = None,
        writer: TrustedTableWriterInterface | None = None,
        store: Callable[[Path], MarketplaceStoreInterface] = loops_marketplace_store,
        resolver: Callable[[MarketplaceStoreInterface], CapabilityResolverInterface] = (
            loops_resolver
        ),
        pruner: SnapshotPrunerInterface | None = None,
        shipped_source: Callable[[], str] = loops_shipped_source,
        rule: MarketplaceSourceRuleInterface = MARKETPLACE_SOURCE_RULE,
        text: SafeTextInterface | None = None,
        echo: Callable[[str], object] = typer.echo,
    ) -> None:
        self._user_config = user_config
        self._settings = settings or loops_bundle_settings()
        self._reader = reader or loops_table_reader()
        self._writer = writer or loops_table_writer()
        self._store = store
        self._resolver = resolver
        self._pruner = pruner or loops_snapshot_pruner()
        self._shipped_source = shipped_source
        self._rule = rule
        self._text = text or SafeText()
        self._echo = echo

    # -- marketplaces --------------------------------------------------------------------------

    def marketplace_add(self, name: str, source: str, ref: str | None) -> int:
        def change(raw: dict[str, object]) -> tuple[str, bool]:
            try:
                kind = self._rule.classify(source).kind
                if ref is not None and kind == "local":
                    raise _Stop(EXIT_USAGE, f"{source}: a local folder has no ref to pin")
                if ref is not None:
                    self._rule.check_ref(ref)
            except MarketplaceSourceError as exc:
                raise _Stop(EXIT_USAGE, str(exc)) from exc
            entry: dict[str, object] = {"name": name, "source": source}
            if ref is not None:
                entry["ref"] = ref
            raw["marketplaces"] = [*self._rows(raw, "marketplaces"), entry]
            return (
                f"added the marketplace {name} ({source}); nothing is fetched until "
                f"`vibey loops marketplace update {name}`",
                True,
            )

        return self._guarded(lambda: self._change(change))

    def marketplace_update(self, name: str | None) -> int:
        return self._guarded(lambda: self._update(name))

    def _update(self, name: str | None) -> int:
        bundle = self._bundle()
        declared = {spec.name: spec for spec in bundle.marketplaces}
        if name is None:
            targets = [DEFAULT_MARKETPLACE_NAME, *declared]
        elif name == DEFAULT_MARKETPLACE_NAME or name in declared:
            targets = [name]
        else:
            shown = self._clean(name)
            raise _Stop(
                EXIT_USAGE,
                f"{shown} is not a marketplace in [loops]; add it with "
                f"`vibey loops marketplace add {shown} SOURCE`",
            )
        store = self._store(self._user_config())
        code = 0
        for target in targets:
            spec = declared.get(target)
            try:
                if spec is None:
                    self._update_shipped(store)
                else:
                    self._update_declared(store, spec)
            except _Stop as stop:
                self._echo(stop.message)
                code = max(code, stop.code)
        return code

    def _update_shipped(self, store: MarketplaceStoreInterface) -> None:
        try:
            entry = self._resolver(store).lock_shipped(store.shipped_root())
        except (CapabilityResolutionError, OSError) as exc:
            raise _Stop(EXIT_FAILED, f"vibey not updated: {self._clean(exc)}") from exc
        self._echo(f"vibey locked {entry.digest} ({entry.source})")

    def _update_declared(self, store: MarketplaceStoreInterface, spec: MarketplaceSpec) -> None:
        try:
            update = store.update(spec)
        except MarketplaceSourceError as exc:
            raise _Stop(EXIT_USAGE, f"{spec.name} not updated: {exc}") from exc
        except MarketplaceFetchError as exc:
            raise _Stop(EXIT_FAILED, f"{spec.name} not updated: {self._clean(exc)}") from exc
        commit = update.fetched.commit
        at = f" at commit {commit}" if commit else ""
        self._echo(f"{spec.name} locked {update.entry.digest}{at} from {spec.source}")
        for path in update.fetched.left_out:
            self._echo(f"{spec.name} left out {self._clean(path)} (a symlink is never copied)")

    def marketplace_list(self, *, as_json: bool) -> int:
        return self._guarded(lambda: self._marketplace_list(as_json))

    def _marketplace_list(self, as_json: bool) -> int:
        bundle = self._bundle()
        store = self._store(self._user_config())
        lock = {entry.marketplace: entry for entry in self._locked(store)}
        rows = [self._shipped_row(lock.get(DEFAULT_MARKETPLACE_NAME))]
        rows += [self._declared_row(spec, lock.get(spec.name)) for spec in bundle.marketplaces]
        if as_json:
            self._echo(json.dumps({"lock": str(store.lock_path), "marketplaces": rows}, indent=2))
            return 0
        for row in rows:
            at = f" at {row['ref']}" if row["ref"] else ""
            kind = "shipped" if row["shipped"] else "added"
            digest = f" {row['digest']}" if row["digest"] else ""
            self._echo(
                self._clean(f"{row['name']}  {kind}  {row['source']}{at}  {row['state']}{digest}")
            )
        return 0

    def _shipped_row(self, entry: LockEntry | None) -> dict[str, object]:
        source = self._shipped_source()
        if entry is None:
            state = SHIPPED_FIRST
        else:
            state = LOCKED if entry.source == source else SHIPPED_AGAIN
        return self._row(DEFAULT_MARKETPLACE_NAME, source, None, True, state, entry)

    def _declared_row(self, spec: MarketplaceSpec, entry: LockEntry | None) -> dict[str, object]:
        if entry is None:
            state = NOT_LOCKED
        elif (entry.source, entry.ref) != (spec.source, spec.ref):
            state = STALE
        else:
            state = LOCKED
        return self._row(spec.name, spec.source, spec.ref, False, state, entry)

    @staticmethod
    def _row(
        name: str,
        source: str,
        ref: str | None,
        shipped: bool,
        state: str,
        entry: LockEntry | None,
    ) -> dict[str, object]:
        return {
            "name": name,
            "source": source,
            "ref": ref,
            "shipped": shipped,
            "state": state,
            "digest": entry.digest if entry is not None else None,
        }

    # -- plugins -------------------------------------------------------------------------------

    def plugin_add(self, spec: str) -> int:
        def change(raw: dict[str, object]) -> tuple[str, bool]:
            plugins = self._plugins(raw)
            if spec in plugins:
                return f"{spec} is already in [loops] plugins", False
            raw["plugins"] = [*plugins, spec]
            return f"added the plugin {spec}", True

        return self._guarded(lambda: self._change(change))

    def plugin_remove(self, name: str) -> int:
        def change(raw: dict[str, object]) -> tuple[str, bool]:
            plugins = self._plugins(raw)
            kept = [entry for entry in plugins if entry.split("@")[0] != name]
            if len(kept) == len(plugins):
                raise _Stop(EXIT_FAILED, f"{self._clean(name)} is not in [loops] plugins")
            raw["plugins"] = kept
            return f"removed the plugin {name}", True

        return self._guarded(lambda: self._change(change))

    @staticmethod
    def _plugins(raw: dict[str, object]) -> list[str]:
        """`[loops] plugins` as written, or the research default written out."""
        if "plugins" not in raw:
            return [f"{name}@{DEFAULT_MARKETPLACE_NAME}" for name in DEFAULT_RESEARCH_PLUGINS]
        return [str(entry) for entry in LoopsBundleCommands._rows(raw, "plugins")]

    # -- MCP servers ---------------------------------------------------------------------------

    def mcp_add(
        self,
        name: str,
        *,
        local: bool,
        remote: str | None,
        command: Sequence[str],
        env_allow: Sequence[str],
    ) -> int:
        def change(raw: dict[str, object]) -> tuple[str, bool]:
            if local == (remote is not None):
                raise _Stop(
                    EXIT_USAGE,
                    "give exactly one of --local (the stdio command after --) or --remote URL",
                )
            if local and not command:
                raise _Stop(
                    EXIT_USAGE,
                    "--local needs the command after --: vibey loops mcp add NAME --local -- "
                    "CMD ARG...",
                )
            if remote is not None and command:
                raise _Stop(EXIT_USAGE, "--remote takes no command; give the URL alone")
            entry: dict[str, object] = {"name": name}
            if local:
                entry.update(trust="local", command=list(command))
            else:
                entry.update(trust="remote", url=remote)
            if env_allow:
                entry["env_allow"] = list(env_allow)
            raw["mcp_servers"] = [*self._rows(raw, "mcp_servers"), entry]
            return f"added the MCP server {name}", True

        return self._guarded(lambda: self._change(change))

    def mcp_list(self, *, as_json: bool) -> int:
        return self._guarded(lambda: self._mcp_list(as_json))

    def _mcp_list(self, as_json: bool) -> int:
        servers = self._bundle().mcp_servers
        if as_json:
            rows = [
                {
                    "name": server.name,
                    "trust": server.trust,
                    "command": list(server.command) if server.command is not None else None,
                    "url": server.url,
                    "env_allow": list(server.env_allow),
                }
                for server in servers
            ]
            self._echo(json.dumps({"mcp_servers": rows}, indent=2))
            return 0
        if not servers:
            self._echo("no MCP servers in [loops]; add one with `vibey loops mcp add`")
        for server in servers:
            target = shlex.join(server.command) if server.command else str(server.url)
            keeps = f"  keeps {', '.join(server.env_allow)}" if server.env_allow else ""
            self._echo(self._clean(f"{server.name}  {server.trust}  {target}{keeps}"))
        return 0

    # -- skills --------------------------------------------------------------------------------

    def skills_list(self, *, as_json: bool) -> int:
        return self._guarded(lambda: self._skills_list(as_json))

    def _skills_list(self, as_json: bool) -> int:
        bundle = self._bundle()
        store = self._store(self._user_config())
        lock = self._locked(store)
        roots = store.roots(lock, [spec.name for spec in bundle.marketplaces])
        try:
            snapshot = self._resolver(store).resolve(bundle, lock, roots)
        except CapabilityResolutionError as exc:
            raise _Stop(EXIT_FAILED, self._clean(exc)) from exc
        try:
            self._print_skills(snapshot, Path(os.path.realpath(store.snapshots)), as_json)
        finally:
            self._discard(snapshot, store.snapshots)
        return 0

    def _print_skills(self, snapshot: CapabilitySnapshot, snapshots: Path, as_json: bool) -> None:
        skills = snapshot.skills
        skipped = [(self._inside_run(path, snapshots), reason) for path, reason in skills.skipped]
        if as_json:
            document = {
                "digest": snapshot.digest,
                "skills": [
                    {"plugin": s.plugin, "name": s.name, "description": s.description}
                    for s in skills.skills
                ],
                "skipped": [{"path": path, "reason": reason} for path, reason in skipped],
            }
            self._echo(json.dumps(document, indent=2))
            return
        if not skills.skills:
            self._echo("no skills: [loops] enables no plugin that has one")
        for skill in skills.skills:
            description = self._text.clean(skill.description, DESCRIPTION_CHARS)
            self._echo(self._clean(f"{skill.plugin}  {skill.name}  {description}"))
        for path, reason in skipped:
            self._echo(self._clean(f"skipped {path}: {reason}"))

    @staticmethod
    def _inside_run(path: Path, snapshots: Path) -> str:
        """A snapshot path as the person can read it once the snapshot is gone: relative to its
        run folder (`<marketplace>/plugins/...`)."""
        real = Path(os.path.realpath(path))
        if real.is_relative_to(snapshots):
            return Path(*real.relative_to(snapshots).parts[1:]).as_posix()
        return str(path)

    @staticmethod
    def _discard(snapshot: CapabilitySnapshot, snapshots: Path) -> None:
        """Removes the run folder the listing's resolve made: no run will load it."""
        base = Path(os.path.realpath(snapshots))
        for folder in snapshot.plugin_dirs:
            real = Path(os.path.realpath(folder))
            if real.is_relative_to(base) and real != base:
                shutil.rmtree(base / real.relative_to(base).parts[0], ignore_errors=True)

    # -- snapshots -----------------------------------------------------------------------------

    def snapshots_prune(self, older_than_days: int) -> int:
        if older_than_days < 1:
            self._echo("--older-than-days must be at least 1 (a running run's snapshot is young)")
            return EXIT_USAGE
        store = self._store(self._user_config())
        report = self._pruner.prune(
            store.snapshots, older_than_seconds=older_than_days * DAY_SECONDS
        )
        self._echo(
            f"removed {len(report.removed)} run snapshot(s) older than {older_than_days} days "
            f"from {store.snapshots}"
        )
        for path, reason in report.refused:
            self._echo(self._clean(f"left {path}: {reason}"))
        return 0

    # -- shared --------------------------------------------------------------------------------

    def _change(self, change: Callable[[dict[str, object]], tuple[str, bool]]) -> int:
        """Reads the person's `[loops]` as written, checks it, applies `change`, checks the
        result with the bundle's own rule and writes it with the one table writer."""
        path = self._user_config()
        raw = dict(self._reader.read_table(path, TABLE) or {})
        try:
            BundleSpec.from_mapping(raw)
        except BundleError as exc:
            raise ConfigError(str(path), str(exc)) from exc
        message, changed = change(raw)
        try:
            BundleSpec.from_mapping(raw)
        except BundleError as exc:
            raise _Stop(EXIT_USAGE, f"[loops] would be refused: {exc}") from exc
        if changed:
            try:
                self._writer.write_table(path, TABLE, raw)
            except ConfigError as exc:
                self._echo(f"vibey loops: {exc}")
                self._echo(f"paste this as [loops] in {path} instead:")
                self._echo(self._writer.render_table(TABLE, raw))
                return EXIT_CONFIG
        self._echo(message)
        return 0

    @staticmethod
    def _rows(raw: dict[str, object], key: str) -> list[object]:
        """A list key of a `[loops]` the bundle rule has already accepted."""
        value = raw.get(key, [])
        return list(value) if isinstance(value, list) else []

    def _bundle(self) -> BundleSpecInterface:
        return self._settings.load(self._user_config(), None).bundle

    @staticmethod
    def _locked(store: MarketplaceStoreInterface) -> tuple[LockEntry, ...]:
        try:
            return store.locked()
        except LockError as exc:
            raise _Stop(EXIT_FAILED, f"vibey loops: {exc}") from exc

    def _guarded(self, work: Callable[[], int]) -> int:
        try:
            return work()
        except ConfigError as exc:
            self._echo(f"vibey loops: {exc}")
            return EXIT_CONFIG
        except _Stop as stop:
            self._echo(stop.message)
            return stop.code

    def _clean(self, text: object) -> str:
        return self._text.clean(str(text), LINE_CHARS)


LOOPS_BUNDLE: Final[LoopsBundleCommandsInterface] = LoopsBundleCommands()
"""What the commands below run. Annotated with the interface so `mypy --strict` checks the class
against its declared seam."""

# -- the Typer commands, registered under `vibey loops` in cli/main.py -------------------------
# Module-level functions because Typer registers functions; each only hands its arguments to
# `LOOPS_BUNDLE` and exits with what it returns.

AsJson = Annotated[bool, typer.Option("--json", help="Print JSON for a program instead.")]
marketplace_app = typer.Typer(
    help="Marketplaces a loop's plugins come from: add, update (fetch and lock), list."
)
plugin_app = typer.Typer(help="Plugins every loop is given, written name@marketplace.")
mcp_app = typer.Typer(help="MCP servers every loop is given: local (stdio) or remote (https).")
skills_app = typer.Typer(help="The skills a run would get, from the lock, with no network.")
snapshots_app = typer.Typer(help="Each run's verified copy of its plugins.")


@marketplace_app.command("add")
def marketplace_add_cmd(
    name: Annotated[str, typer.Argument(help="A plain name: letters, digits, '.', '_', '-'.")],
    source: Annotated[
        str,
        typer.Argument(
            help="An https://, ssh:// or git:// URL, user@host:path, or an absolute folder."
        ),
    ],
    ref: Annotated[
        str | None, typer.Option("--ref", help="The branch, tag or commit to pin (git only).")
    ] = None,
) -> None:
    """Declare a marketplace in your own vibey.toml; nothing is fetched until `update`."""
    raise typer.Exit(LOOPS_BUNDLE.marketplace_add(name, source, ref))


@marketplace_app.command("update")
def marketplace_update_cmd(
    name: Annotated[
        str | None,
        typer.Argument(help="One marketplace (`vibey` is the shipped one); none for all."),
    ] = None,
) -> None:
    """Fetch, check and lock a marketplace: the only command that reaches the network."""
    raise typer.Exit(LOOPS_BUNDLE.marketplace_update(name))


@marketplace_app.command("list")
def marketplace_list_cmd(as_json: AsJson = False) -> None:
    """Each marketplace and what the lock holds of it; fetches and hashes nothing."""
    raise typer.Exit(LOOPS_BUNDLE.marketplace_list(as_json=as_json))


@plugin_app.command("add")
def plugin_add_cmd(
    spec: Annotated[str, typer.Argument(metavar="NAME@MARKETPLACE", help="The plugin to add.")],
) -> None:
    """Give every loop a plugin from a declared marketplace."""
    raise typer.Exit(LOOPS_BUNDLE.plugin_add(spec))


@plugin_app.command("remove")
def plugin_remove_cmd(
    name: Annotated[str, typer.Argument(help="The plugin's name, without @marketplace.")],
) -> None:
    """Stop giving every loop a plugin (the research default included)."""
    raise typer.Exit(LOOPS_BUNDLE.plugin_remove(name))


@mcp_app.command("add")
def mcp_add_cmd(
    name: Annotated[str, typer.Argument(help="A plain name for the server.")],
    command: Annotated[
        list[str] | None,
        typer.Argument(help="After --, the local server's command and arguments, as given."),
    ] = None,
    local: Annotated[
        bool, typer.Option("--local", help="A stdio server run from the command after --.")
    ] = False,
    remote: Annotated[
        str | None, typer.Option("--remote", help="An https:// URL of a remote server.")
    ] = None,
    env_allow: Annotated[
        list[str] | None,
        typer.Option("--env-allow", help="A variable a local server keeps (repeatable)."),
    ] = None,
) -> None:
    """Give every loop an MCP server: --local -- CMD ARG... or --remote URL."""
    raise typer.Exit(
        LOOPS_BUNDLE.mcp_add(
            name, local=local, remote=remote, command=command or [], env_allow=env_allow or []
        )
    )


@mcp_app.command("list")
def mcp_list_cmd(as_json: AsJson = False) -> None:
    """The MCP servers in your own vibey.toml."""
    raise typer.Exit(LOOPS_BUNDLE.mcp_list(as_json=as_json))


@skills_app.command("list")
def skills_list_cmd(as_json: AsJson = False) -> None:
    """The skills a run would get, resolved from the lock with no network."""
    raise typer.Exit(LOOPS_BUNDLE.skills_list(as_json=as_json))


@snapshots_app.command("prune")
def snapshots_prune_cmd(
    older_than_days: Annotated[
        int,
        typer.Option("--older-than-days", min=1, help="Remove run snapshots older than this."),
    ] = DEFAULT_AGE_DAYS,
) -> None:
    """Remove finished runs' snapshots past an age, under your own store only."""
    raise typer.Exit(LOOPS_BUNDLE.snapshots_prune(older_than_days))
