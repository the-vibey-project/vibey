# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate a change on its npm advisories, less the declared, expiring exceptions (`[advisories]`).

`npm audit --audit-level=high` fails on every advisory at high or worse, and has one answer to
an advisory nobody can fix yet: fail every pull request until a patched release exists. That
is how GHSA-86w9-cpqp-85rv stopped CI on 2026-10-01 -- node-forge 1.4.0, the latest release,
reached only through Expo's developer CLI -- and the only ways round it the tool offers are a
breaking downgrade it calls a fix, or dropping the gate.

This keeps the gate for everything nobody has decided about. An advisory with no fix can be
excepted in `[advisories] exceptions_file`, by a reviewed entry that names the advisory, the
package and the workspace, records why the vulnerable code is not reached, and expires within
`max_exception_days`. Nothing is skipped silently: every run prints each exception it honours
and until when, and an exception fails the check the moment it expires, stops matching
anything (so it is removed, not left to rot), or its package gets a patched release (so the
fix replaces it). A report the check cannot account for -- npm erroring, an unknown format, a
package at the audit level with no advisory behind it -- is refused, never passed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from vibey_gh.config import (
    AUDIT_LEVELS,
    AdvisoriesConfig,
    GhConfig,
    _repository_relative,
    load_config,
)
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.advisory_gate_interface import (
    Advisory,
    AdvisoryException,
    AdvisoryGateInterface,
    AdvisoryVerdict,
)
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

__all__ = ["AdvisoryGate"]

_GHSA = re.compile(r"GHSA(?:-[0-9a-z]{4}){3}")
# Least to most severe; `info` is below every level `--audit-level` accepts.
_RANK = {severity: rank for rank, severity in enumerate(("info", *AUDIT_LEVELS))}
_REQUIRED = ("advisory", "package", "workspace", "reason", "added", "expires", "retire_when")
_OPTIONAL = ("upstream",)
_LOCKFILE = "package-lock.json"


def _today() -> date:
    """Today in UTC, the clock CI runs on. A function, not a method: it is the default for an
    injected clock, which a class attribute would bind as a method."""
    return datetime.now(UTC).date()


class AdvisoryGate(AdvisoryGateInterface):
    """Implements `AdvisoryGateInterface`."""

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        npm: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        gh: GhTransportInterface | None = None,
        today: Callable[[], date] = _today,
    ) -> None:
        self._config = config
        self._npm = npm
        self._gh = gh if gh is not None else GhTransport()
        self._today = today

    # ------------------------------------------------------------------ the exceptions

    def exceptions(self, path: Path) -> tuple[AdvisoryException, ...]:
        if not path.is_file():
            return ()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"not valid TOML: {exc}") from exc
        extra = sorted(set(data) - {"exception"})
        if extra:
            raise ValueError(f"unknown key(s) {', '.join(extra)}; exceptions are [[exception]]")
        entries = data.get("exception", [])
        if not isinstance(entries, list):
            raise ValueError(  # noqa: TRY004 - a configuration error, like config.py's
                "exception must be an array of tables ([[exception]])"
            )
        limit = self._config().advisories.max_exception_days
        parsed = [self._exception(index, entry, limit) for index, entry in enumerate(entries, 1)]
        keys = [(e.advisory, e.package, e.workspace) for e in parsed]
        if len(set(keys)) != len(keys):
            raise ValueError("each advisory, package and workspace may be excepted only once")
        return tuple(parsed)

    @staticmethod
    def _exception(index: int, entry: object, limit: int) -> AdvisoryException:
        where = f"exception {index}"
        if not isinstance(entry, Mapping):
            raise ValueError(f"{where} must be a table")  # noqa: TRY004
        extra = sorted(set(entry) - {*_REQUIRED, *_OPTIONAL})
        if extra:
            raise ValueError(f"{where}: unknown key(s) {', '.join(extra)}")
        missing = [key for key in _REQUIRED if key not in entry]
        if missing:
            raise ValueError(f"{where}: missing {', '.join(missing)}")
        text = {}
        for key in ("advisory", "package", "reason", "retire_when"):
            value = entry[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{where}: {key} must be a non-empty string")
            text[key] = value.strip()
        if not _GHSA.fullmatch(text["advisory"]):
            raise ValueError(
                f"{where}: advisory must be a GitHub advisory id (GHSA-xxxx-xxxx-xxxx)"
            )
        if "\n" in text["package"]:
            raise ValueError(f"{where}: package must be a single line")
        workspace = _repository_relative(f"{where}: workspace", entry["workspace"])
        dates = {}
        for key in ("added", "expires"):
            value = entry[key]
            # A TOML datetime is a `datetime`, which is a `date`; only a bare date is a day.
            if not isinstance(value, date) or isinstance(value, datetime):
                raise ValueError(  # noqa: TRY004 - a configuration error
                    f"{where}: {key} must be a TOML date (YYYY-MM-DD, unquoted)"
                )
            dates[key] = value
        span = (dates["expires"] - dates["added"]).days
        if span < 1:
            raise ValueError(f"{where}: expires must be after added")
        if span > limit:
            raise ValueError(
                f"{where}: expires is {span} days after added; [advisories] max_exception_days"
                f" allows {limit}"
            )
        upstream = entry.get("upstream", [])
        if not isinstance(upstream, list) or not all(
            isinstance(link, str) and link.strip() for link in upstream
        ):
            raise ValueError(f"{where}: upstream must be a list of non-empty strings")
        return AdvisoryException(
            advisory=text["advisory"],
            package=text["package"],
            workspace=workspace,
            reason=text["reason"],
            added=dates["added"],
            expires=dates["expires"],
            retire_when=text["retire_when"],
            upstream=tuple(upstream),
        )

    # ------------------------------------------------------------------ the audit

    def audit(self, workspace: Path) -> Mapping[str, Any]:
        run = self._npm(
            ["npm", "audit", "--json"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        # npm exits non-zero whenever it finds anything, so the exit status says nothing about
        # whether an audit happened; the report does.
        try:
            report = json.loads(run.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"npm audit in {workspace} printed no audit report (exit {run.returncode}):"
                f" {run.stderr.strip()[-500:]}"
            ) from None
        return self._readable(report, str(workspace))

    @staticmethod
    def _readable(report: object, where: str) -> Mapping[str, Any]:
        """`report` when it is an npm audit report this gate can read, else `RuntimeError`."""
        if not isinstance(report, Mapping):
            raise RuntimeError(f"{where}: an npm audit report is a JSON object")  # noqa: TRY004
        if "error" in report:
            error = report["error"]
            summary = error.get("summary", error) if isinstance(error, Mapping) else error
            raise RuntimeError(f"{where}: npm audit failed: {summary}")
        if report.get("auditReportVersion") != 2 or not isinstance(
            report.get("vulnerabilities"), Mapping
        ):
            raise RuntimeError(
                f"{where}: not an npm audit report this check can read (auditReportVersion 2)"
            )
        return report

    # ------------------------------------------------------------------ the verdict

    def verdict(
        self,
        report: Mapping[str, Any],
        *,
        workspace: str,
        exceptions: Sequence[AdvisoryException],
        audit_level: str,
        today: date,
    ) -> AdvisoryVerdict:
        floor = _RANK[audit_level]

        def at_level(severity: object) -> bool:
            # A severity this check does not know is treated as the worst: refused, not passed.
            return _RANK.get(str(severity), len(_RANK)) >= floor

        vulnerabilities: Mapping[str, Any] = report["vulnerabilities"]
        advisories: dict[tuple[str, str], Advisory] = {}
        for name, entry in vulnerabilities.items():
            for via in entry.get("via", ()):
                if isinstance(via, Mapping):
                    advisory = self._advisory(name, via)
                    advisories[(advisory.id, advisory.package)] = advisory

        mine = [e for e in exceptions if e.workspace == workspace]
        live = {(e.advisory, e.package): e for e in mine if today < e.expires}
        expired = tuple(e for e in mine if today >= e.expires)
        blocking: list[Advisory] = []
        excepted: list[tuple[Advisory, AdvisoryException]] = []
        for key, advisory in sorted(advisories.items()):
            if not at_level(advisory.severity):
                continue
            if key in live:
                excepted.append((advisory, live[key]))
            else:
                blocking.append(advisory)
        used = {(advisory.id, advisory.package) for advisory, _ in excepted}
        stale = tuple(e for key, e in live.items() if key not in used)

        def roots(name: str, seen: set[str]) -> set[tuple[str, str]]:
            """Every advisory at the level that `name` is vulnerable through."""
            if name in seen:
                return set()
            seen.add(name)
            found: set[tuple[str, str]] = set()
            for via in vulnerabilities.get(name, {}).get("via", ()):
                if isinstance(via, Mapping):
                    advisory = self._advisory(name, via)
                    if at_level(advisory.severity):
                        found.add((advisory.id, advisory.package))
                else:
                    found |= roots(str(via), seen)
            return found

        unexplained: list[str] = []
        covered: list[str] = []
        excepted_packages = {advisory.package for advisory, _ in excepted}
        for name, entry in sorted(vulnerabilities.items()):
            if not at_level(entry.get("severity", "")):
                continue
            behind = roots(name, set())
            if not behind:
                unexplained.append(name)
            elif behind <= used and name not in excepted_packages:
                covered.append(name)
        return AdvisoryVerdict(
            workspace=workspace,
            blocking=tuple(blocking),
            excepted=tuple(excepted),
            expired=expired,
            stale=stale,
            unexplained=tuple(unexplained),
            covered=tuple(covered),
        )

    @staticmethod
    def _advisory(name: str, via: Mapping[str, Any]) -> Advisory:
        """One `via` object of the report entry for `name`, as an advisory."""
        url = str(via.get("url", ""))
        found = _GHSA.search(url)
        return Advisory(
            id=found.group(0) if found else url or f"npm advisory {via.get('source')}",
            package=str(via.get("name", name)),
            severity=str(via.get("severity", "")),
            title=str(via.get("title", "")),
            url=url,
            range=str(via.get("range", "")),
        )

    # ------------------------------------------------------------------ the fix

    def patched_version(self, advisory: str, package: str) -> str | None:
        try:
            data = self._gh.json(["api", f"/advisories/{advisory}"])
        except (RuntimeError, OSError, ValueError) as exc:
            raise RuntimeError(f"the advisory database could not be read: {exc}") from exc
        affected = data.get("vulnerabilities") if isinstance(data, Mapping) else None
        if not isinstance(affected, list):
            raise RuntimeError(  # noqa: TRY004 - an unreadable source, as every other here
                f"the advisory database returned no affected packages for {advisory}"
            )
        listed = False
        for item in affected:
            if not isinstance(item, Mapping):
                continue
            named = item.get("package", {})
            if not isinstance(named, Mapping) or named.get("name") != package:
                continue
            if named.get("ecosystem", "npm") != "npm":
                continue
            listed = True
            patched = item.get("first_patched_version")
            if isinstance(patched, Mapping):  # the older shape: {"identifier": "1.2.3"}
                patched = patched.get("identifier")
            if isinstance(patched, str) and patched.strip():
                return patched.strip()
        if not listed:
            raise RuntimeError(f"the advisory database does not list {package} under {advisory}")
        return None

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--workspace",
            action="append",
            default=None,
            metavar="PATH",
            help="a repository-relative directory holding a package-lock.json to audit"
            " (repeatable; default: the repository root)",
        )
        parser.add_argument(
            "--audit-file",
            type=Path,
            default=None,
            metavar="JSON",
            help="judge a saved `npm audit --json` report instead of running npm"
            " (one --workspace only)",
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        return cls().run(args.workspace or ["."], args.audit_file)

    def run(self, workspaces: Sequence[str], audit_file: Path | None = None) -> int:
        cfg = self._config()
        policy = cfg.advisories
        where = policy.exceptions_file
        try:
            declared = self.exceptions(cfg.root / where)
            names = [_repository_relative("--workspace", ws) for ws in workspaces]
        except ValueError as exc:
            print(f"::error::{where}: {exc}")
            return 1
        if audit_file is not None and len(names) != 1:
            print("::error::--audit-file judges one report, so it takes exactly one --workspace")
            return 1
        failed = False
        # An exception for a workspace that has no lockfile can never be checked, so it is
        # never honoured either: it is stale wherever the check runs.
        for exception in declared:
            if not (cfg.root / exception.workspace / _LOCKFILE).is_file():
                print(
                    f"::error::{where}: the exception for {exception.advisory} in"
                    f" {exception.package} names {exception.workspace}, which has no"
                    f" {_LOCKFILE}; remove it"
                )
                failed = True
        patched: dict[tuple[str, str], str | None | RuntimeError] = {}
        today = self._today()
        for name in names:
            try:
                if audit_file is not None:
                    report = self._readable(
                        json.loads(audit_file.read_text(encoding="utf-8")), str(audit_file)
                    )
                else:
                    report = self.audit(cfg.root / name)
            except (RuntimeError, OSError, ValueError) as exc:
                print(f"::error::{name}: {exc}")
                failed = True
                continue
            verdict = self.verdict(
                report,
                workspace=name,
                exceptions=declared,
                audit_level=policy.audit_level,
                today=today,
            )
            for advisory, exception in verdict.excepted:
                key = (exception.advisory, exception.package)
                if key not in patched:
                    try:
                        patched[key] = self.patched_version(*key)
                    except RuntimeError as exc:
                        patched[key] = exc
            if not self._print(verdict, report, patched, today, policy):
                failed = True
        return 1 if failed else 0

    def _print(
        self,
        verdict: AdvisoryVerdict,
        report: Mapping[str, Any],
        patched: Mapping[tuple[str, str], str | None | RuntimeError],
        today: date,
        policy: AdvisoriesConfig,
    ) -> bool:
        """Print one workspace's verdict; whether it passed."""
        level, where, ws = policy.audit_level, policy.exceptions_file, verdict.workspace
        counts = report.get("metadata", {}).get("vulnerabilities", {})
        print(
            f"vibey-gh: {ws}: npm audit at {level} or worse"
            f" ({counts.get('total', len(report['vulnerabilities']))} vulnerable package(s)"
            " reported in all)"
        )
        ok = verdict.ok
        for advisory, exception in verdict.excepted:
            left = (exception.expires - today).days
            print(
                f"  excepted  {advisory.id} in {advisory.package} ({advisory.severity}):"
                f" until {exception.expires}, {left} day(s) left -- declared in {where}"
            )
            print(f"            retires when: {exception.retire_when}")
            fix = patched[(exception.advisory, exception.package)]
            if isinstance(fix, RuntimeError):
                print(
                    f"::error::{ws}: could not confirm that no patched {exception.package}"
                    f" exists for {exception.advisory} ({fix}); an exception is honoured only"
                    " while that is known"
                )
                ok = False
            elif fix is not None:
                print(
                    f"::error::{ws}: {exception.package} {fix} fixes {exception.advisory};"
                    f" upgrade to it and remove the exception from {where}"
                )
                ok = False
            else:
                print(
                    f"            no patched {exception.package} is published (advisory database)"
                )
            if left <= policy.warn_days:
                print(
                    f"::warning::{ws}: the exception for {exception.advisory} in"
                    f" {exception.package} expires on {exception.expires}; take the fix or"
                    f" re-decide it in {where}"
                )
        for name in verdict.covered:
            print(
                f"  covered   {name}: {level} or worse only through the excepted advisories above"
            )
        for advisory in verdict.blocking:
            print(
                f"::error::{ws}: {advisory.id} in {advisory.package} ({advisory.severity}):"
                f" {advisory.title} -- {advisory.url or 'no URL reported'}"
            )
        for exception in verdict.expired:
            print(
                f"::error::{ws}: the exception for {exception.advisory} in {exception.package}"
                f" expired on {exception.expires}; take the fix, or re-decide it with fresh"
                f" evidence in {where}"
            )
        for exception in verdict.stale:
            print(
                f"::error::{ws}: the exception for {exception.advisory} in {exception.package}"
                f" matches nothing at {level} or worse; remove it from {where}"
            )
        for name in verdict.unexplained:
            print(
                f"::error::{ws}: npm audit puts {name} at {level} or worse with no advisory at"
                " that level behind it; refusing a report this check cannot account for"
            )
        if ok:
            print(
                f"vibey-gh: {ws}: no unexcepted advisory at {level} or worse;"
                f" {len(verdict.excepted)} excepted"
            )
        return ok
