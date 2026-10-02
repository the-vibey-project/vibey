# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The advisory gate: npm audit's verdict, less only declared, expiring, reviewed exceptions.

`krypton-app-node-forge.json` is the real `npm audit --json` of clients/app on 2026-10-01,
when GHSA-86w9-cpqp-85rv (node-forge <= 1.4.0, no patched release) first failed CI; and
`GHSA-86w9-cpqp-85rv.json` is the real advisory-database record for it. Every failure mode
the gate promises -- an unexcepted advisory, an expired, stale or superseded exception, an
unreadable audit or database, a report it cannot account for -- is pinned here.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import cli
from vibey_gh.advisories import AdvisoryGate, _today
from vibey_gh.config import AdvisoriesConfig, GhConfig, load_config
from vibey_gh.interfaces.advisory_gate_interface import (
    Advisory,
    AdvisoryException,
    AdvisoryGateInterface,
    AdvisoryVerdict,
)

FIXTURES = Path(__file__).parent / "fixtures" / "advisories"
GHSA = "GHSA-86w9-cpqp-85rv"
TODAY = date(2026, 10, 1)
APP = "clients/app"


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def node_forge_report() -> dict[str, Any]:
    return fixture("krypton-app-node-forge.json")


ENTRY = f"""
[[exception]]
advisory = "{GHSA}"
package = "node-forge"
workspace = "{APP}"
added = 2026-10-01
expires = 2026-10-31
reason = "only @expo/cli reaches it"
retire_when = "a patched node-forge"
upstream = ["https://github.com/digitalbazaar/forge/pull/1152"]
"""


def exception(**changes: Any) -> AdvisoryException:
    base = AdvisoryException(
        advisory=GHSA,
        package="node-forge",
        workspace=APP,
        reason="only @expo/cli reaches it",
        added=date(2026, 10, 1),
        expires=date(2026, 10, 31),
        retire_when="a patched node-forge",
        upstream=("https://github.com/digitalbazaar/forge/pull/1152",),
    )
    return dataclasses.replace(base, **changes)


class FakeGh:
    """The advisory database as `gh api` answers it, counting the calls."""

    executable = "gh"

    def __init__(self, answer: object = None, error: Exception | None = None) -> None:
        self.answer = fixture(f"{GHSA}.json") if answer is None else answer
        self.error = error
        self.calls: list[list[str]] = []

    def json(self, args, *, cwd=None, stdin=None):
        self.calls.append(list(args))
        if self.error is not None:
            raise self.error
        return self.answer


def npm_answering(stdout: str, returncode: int = 1, stderr: str = ""):
    seen: list[tuple[list[str], Any]] = []

    def run(argv, **kwargs):
        seen.append((argv, kwargs["cwd"]))
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    run.seen = seen  # type: ignore[attr-defined]
    return run


def repository(tmp_path: Path, exceptions: str | None = ENTRY, workspaces=(".", APP)) -> Path:
    """A repository with a lockfile in each workspace and, optionally, an exceptions file."""
    for workspace in workspaces:
        (tmp_path / workspace).mkdir(parents=True, exist_ok=True)
        (tmp_path / workspace / "package-lock.json").write_text("{}\n", encoding="utf-8")
    if exceptions is not None:
        (tmp_path / ".github").mkdir(exist_ok=True)
        (tmp_path / ".github" / "advisory-exceptions.toml").write_text(exceptions, encoding="utf-8")
    return tmp_path


def gate_for(
    root: Path,
    *,
    reports: dict[str, object] | None = None,
    gh: FakeGh | None = None,
    today: date = TODAY,
    **changes: Any,
) -> AdvisoryGate:
    """A gate over `root` whose npm answers each workspace with its report in `reports`."""
    cfg = dataclasses.replace(GhConfig(root=root), **changes)
    answers = {".": fixture("clean.json"), APP: node_forge_report(), **(reports or {})}

    def npm(argv, *, cwd, **kwargs):
        assert argv == ["npm", "audit", "--json"]
        workspace = Path(cwd).relative_to(root).as_posix() or "."
        answer = answers[workspace]
        stdout = answer if isinstance(answer, str) else json.dumps(answer)
        return subprocess.CompletedProcess(argv, 1, stdout, "")

    return AdvisoryGate(
        config=lambda: cfg,
        npm=npm,
        gh=gh if gh is not None else FakeGh(),
        today=lambda: today,
    )


def test_the_gate_implements_its_interface():
    assert isinstance(AdvisoryGate(gh=FakeGh()), AdvisoryGateInterface)


def test_the_default_clock_is_a_utc_date():
    assert isinstance(_today(), date)


# ---------------------------------------------------------------------- the exceptions


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "exceptions.toml"
    path.write_text(text, encoding="utf-8")
    return path


def parse(tmp_path: Path, text: str, **changes: Any) -> tuple[AdvisoryException, ...]:
    return gate_for(tmp_path, **changes).exceptions(write(tmp_path, text))


def test_a_missing_exceptions_file_declares_none(tmp_path):
    assert gate_for(tmp_path).exceptions(tmp_path / "absent.toml") == ()


def test_an_exception_is_read_whole_and_its_workspace_normalised(tmp_path):
    (parsed,) = parse(tmp_path, ENTRY.replace(f'"{APP}"', f'"{APP}/"'))
    assert parsed == exception()


def test_upstream_is_optional(tmp_path):
    text = "\n".join(line for line in ENTRY.splitlines() if not line.startswith("upstream"))
    assert parse(tmp_path, text) == (exception(upstream=()),)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[[exception]\n", "not valid TOML"),
        ('other = 1\n[[exception]]\nadvisory = "x"\n', "unknown key"),
        ('exception = "nope"\n', "array of tables"),
        ("exception = [1]\n", "must be a table"),
        (ENTRY + 'extra = "x"\n', "unknown key"),
        ("[[exception]]\n", "missing advisory"),
        (ENTRY.replace('reason = "only @expo/cli reaches it"', 'reason = "  "'), "reason must be"),
        (ENTRY.replace('package = "node-forge"', "package = 7"), "package must be"),
        (ENTRY.replace(f'"{GHSA}"', '"CVE-2026-85393"'), "GitHub advisory id"),
        (ENTRY.replace('package = "node-forge"', 'package = """a\nb"""'), "single line"),
        (ENTRY.replace(f'"{APP}"', '"/abs"'), "repository-relative"),
        (ENTRY.replace(f'"{APP}"', '"../up"'), "repository-relative"),
        (ENTRY.replace("added = 2026-10-01", 'added = "2026-10-01"'), "TOML date"),
        (ENTRY.replace("expires = 2026-10-31", "expires = 2026-10-31T00:00:00"), "TOML date"),
        (ENTRY.replace("expires = 2026-10-31", "expires = 2026-10-01"), "after added"),
        (ENTRY.replace("expires = 2026-10-31", "expires = 2026-11-01"), "allows 30"),
        (
            ENTRY.replace('upstream = ["https', 'upstream = "https').replace('1152"]', '1152"'),
            "upstream",
        ),
        (ENTRY.replace('upstream = ["https', 'upstream = ["", "https'), "upstream"),
        (ENTRY + ENTRY, "only once"),
    ],
)
def test_a_malformed_exception_is_refused_by_name(tmp_path, text, message):
    with pytest.raises(ValueError, match=message):
        parse(tmp_path, text)


def test_the_span_limit_is_the_configured_one(tmp_path):
    short = AdvisoriesConfig(max_exception_days=7)
    with pytest.raises(ValueError, match="allows 7"):
        parse(tmp_path, ENTRY, advisories=short)


# ---------------------------------------------------------------------- the audit


def test_the_audit_runs_npm_in_the_workspace_and_reads_a_failing_exit_as_a_report(tmp_path):
    npm = npm_answering(json.dumps(node_forge_report()), returncode=1)
    report = AdvisoryGate(npm=npm, gh=FakeGh()).audit(tmp_path)
    assert report["metadata"]["vulnerabilities"]["high"] == 4
    assert npm.seen == [(["npm", "audit", "--json"], tmp_path)]


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        ("npm ERR! network", "printed no audit report"),
        ("[]", "is a JSON object"),
        (json.dumps({"error": {"code": "ENOLOCK", "summary": "no lockfile"}}), "no lockfile"),
        (json.dumps({"error": "registry down"}), "registry down"),
        (json.dumps({"auditReportVersion": 1, "advisories": {}}), "auditReportVersion 2"),
        (json.dumps({"auditReportVersion": 2, "vulnerabilities": []}), "auditReportVersion 2"),
    ],
)
def test_an_audit_that_cannot_be_read_is_refused(tmp_path, stdout, message):
    with pytest.raises(RuntimeError, match=message):
        AdvisoryGate(npm=npm_answering(stdout), gh=FakeGh()).audit(tmp_path)


# ---------------------------------------------------------------------- the verdict


def judge(report=None, exceptions=(), level="high", today=TODAY, workspace=APP) -> AdvisoryVerdict:
    return AdvisoryGate(gh=FakeGh()).verdict(
        node_forge_report() if report is None else report,
        workspace=workspace,
        exceptions=exceptions,
        audit_level=level,
        today=today,
    )


def test_without_an_exception_node_forge_blocks_exactly_as_npm_audit_does():
    verdict = judge()
    assert [(a.id, a.package, a.severity) for a in verdict.blocking] == [
        (GHSA, "node-forge", "high")
    ]
    assert verdict.blocking[0].range == "<=1.4.0"
    assert not verdict.ok
    assert verdict.excepted == verdict.covered == verdict.unexplained == ()


def test_an_exception_covers_the_advisory_and_every_package_high_only_through_it():
    verdict = judge(exceptions=[exception()])
    assert verdict.ok
    assert verdict.blocking == ()
    ((advisory, honoured),) = verdict.excepted
    assert (advisory.id, honoured) == (GHSA, exception())
    assert verdict.covered == ("@expo/cli", "@expo/code-signing-certificates", "expo")


def test_a_lower_audit_level_still_blocks_what_the_exception_does_not_name():
    verdict = judge(exceptions=[exception()], level="moderate")
    assert {a.id for a in verdict.blocking} == {"GHSA-vcc3-ghjq-m6fr", "GHSA-w5hq-g745-h8pq"}


def test_an_expired_exception_is_reported_and_covers_nothing():
    verdict = judge(exceptions=[exception()], today=date(2026, 10, 31))
    assert verdict.expired == (exception(),)
    assert [a.id for a in verdict.blocking] == [GHSA]
    assert not verdict.ok


def test_an_exception_matching_nothing_is_stale():
    verdict = judge(fixture("clean.json"), [exception()])
    assert verdict.stale == (exception(),)
    assert not verdict.ok


def test_an_exception_below_the_audit_level_is_stale_not_honoured():
    verdict = judge(exceptions=[exception()], level="critical")
    assert verdict.stale == (exception(),)
    assert verdict.excepted == verdict.blocking == ()


def test_an_exception_for_another_workspace_neither_covers_nor_goes_stale():
    verdict = judge(exceptions=[exception(workspace="elsewhere")])
    assert verdict.stale == verdict.excepted == ()
    assert [a.id for a in verdict.blocking] == [GHSA]


def entry(severity: str, via: list[object]) -> dict[str, Any]:
    return {"severity": severity, "via": via}


def report_of(vulnerabilities: dict[str, Any]) -> dict[str, Any]:
    return {"auditReportVersion": 2, "vulnerabilities": vulnerabilities}


def test_a_package_at_the_level_with_no_advisory_at_that_level_behind_it_is_refused():
    moderate = {
        "name": "b",
        "severity": "moderate",
        "url": "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
    }
    verdict = judge(
        report_of(
            {
                "a": entry("high", ["b", "ghost"]),
                "b": entry("moderate", ["a", moderate]),
            }
        )
    )
    assert verdict.unexplained == ("a",)
    assert verdict.blocking == ()
    assert not verdict.ok


def test_an_unknown_severity_is_treated_as_the_worst():
    odd = {
        "name": "a",
        "severity": "dire",
        "url": "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
    }
    verdict = judge(report_of({"a": entry("dire", [odd])}))
    assert [a.severity for a in verdict.blocking] == ["dire"]


def test_an_advisory_without_a_ghsa_id_is_reported_by_url_or_source():
    by_url = {
        "name": "a",
        "severity": "high",
        "url": "https://example.test/advisory/1",
        "source": 1,
    }
    bare = {"name": "b", "severity": "critical", "source": 2}
    verdict = judge(report_of({"a": entry("high", [by_url]), "b": entry("critical", [bare])}))
    assert sorted(a.id for a in verdict.blocking) == [
        "https://example.test/advisory/1",
        "npm advisory 2",
    ]


# ---------------------------------------------------------------------- the fix


def test_the_real_advisory_names_no_patched_node_forge():
    gh = FakeGh()
    assert AdvisoryGate(gh=gh).patched_version(GHSA, "node-forge") is None
    assert gh.calls == [["api", f"/advisories/{GHSA}"]]


def with_patch(patched: object, *, name: str = "node-forge", ecosystem: str = "npm") -> dict:
    record = copy.deepcopy(fixture(f"{GHSA}.json"))
    record["vulnerabilities"][0]["first_patched_version"] = patched
    record["vulnerabilities"][0]["package"] = {"name": name, "ecosystem": ecosystem}
    return record


@pytest.mark.parametrize("patched", ["1.4.1", {"identifier": "1.4.1"}])
def test_a_published_patch_is_found_in_either_shape(patched):
    assert (
        AdvisoryGate(gh=FakeGh(with_patch(patched))).patched_version(GHSA, "node-forge") == "1.4.1"
    )


@pytest.mark.parametrize(
    ("gh", "message"),
    [
        (FakeGh(error=RuntimeError("gh api: HTTP 502")), "HTTP 502"),
        (FakeGh(error=FileNotFoundError("gh")), "could not be read"),
        (FakeGh(answer=[]), "no affected packages"),
        (FakeGh(answer={"vulnerabilities": "x"}), "no affected packages"),
        (FakeGh(answer={"vulnerabilities": ["junk", {"package": "x"}]}), "does not list"),
        (FakeGh(answer=with_patch("1.4.1", name="other")), "does not list"),
        (FakeGh(answer=with_patch("1.4.1", ecosystem="pip")), "does not list"),
    ],
)
def test_an_advisory_database_that_cannot_answer_is_an_error_not_a_no(gh, message):
    with pytest.raises(RuntimeError, match=message):
        AdvisoryGate(gh=gh).patched_version(GHSA, "node-forge")


# ---------------------------------------------------------------------- the command


def test_with_the_exception_the_check_passes_and_says_what_it_honoured(tmp_path, capsys):
    gate = gate_for(repository(tmp_path))
    assert gate.run([".", APP]) == 0
    out = capsys.readouterr().out
    assert "vibey-gh: .: no unexcepted advisory at high or worse; 0 excepted" in out
    assert (
        f"excepted  {GHSA} in node-forge (high): until 2026-10-31, 30 day(s) left"
        " -- declared in .github/advisory-exceptions.toml"
    ) in out
    assert "retires when: a patched node-forge" in out
    assert "no patched node-forge is published" in out
    assert "covered   @expo/cli: high or worse only through the excepted advisories above" in out
    assert f"vibey-gh: {APP}: no unexcepted advisory at high or worse; 1 excepted" in out
    assert "::error::" not in out and "::warning::" not in out


def test_without_the_exception_the_check_fails_on_node_forge(tmp_path, capsys):
    assert gate_for(repository(tmp_path, exceptions=None)).run([APP]) == 1
    out = capsys.readouterr().out
    assert f"::error::{APP}: {GHSA} in node-forge (high): node-forge RSA PKCS#1" in out
    assert "no unexcepted advisory" not in out


def test_a_published_patch_retires_the_exception(tmp_path, capsys):
    gate = gate_for(repository(tmp_path), gh=FakeGh(with_patch("1.4.1")))
    assert gate.run([APP]) == 1
    out = capsys.readouterr().out
    assert f"::error::{APP}: node-forge 1.4.1 fixes {GHSA}; upgrade to it and remove" in out


def test_an_unconfirmed_patch_status_is_refused(tmp_path, capsys):
    gate = gate_for(repository(tmp_path), gh=FakeGh(error=RuntimeError("offline")))
    assert gate.run([APP]) == 1
    assert "could not confirm that no patched node-forge exists" in capsys.readouterr().out


def test_an_expiring_exception_warns_out_loud(tmp_path, capsys):
    assert gate_for(repository(tmp_path), today=date(2026, 10, 24)).run([APP]) == 0
    out = capsys.readouterr().out
    assert "7 day(s) left" in out
    assert f"::warning::{APP}: the exception for {GHSA} in node-forge expires on 2026-10-31" in out


def test_an_expired_exception_fails_the_check(tmp_path, capsys):
    assert gate_for(repository(tmp_path), today=date(2026, 10, 31)).run([APP]) == 1
    out = capsys.readouterr().out
    assert f"::error::{APP}: the exception for {GHSA} in node-forge expired on 2026-10-31" in out
    assert f"::error::{APP}: {GHSA} in node-forge (high)" in out


def test_a_stale_exception_fails_the_check_so_it_is_removed(tmp_path, capsys):
    gate = gate_for(repository(tmp_path), reports={APP: fixture("clean.json")})
    assert gate.run([APP]) == 1
    assert "matches nothing at high or worse; remove it from" in capsys.readouterr().out


def test_an_exception_naming_a_workspace_with_no_lockfile_fails_everywhere(tmp_path, capsys):
    root = repository(tmp_path, ENTRY.replace(f'"{APP}"', '"gone"'), workspaces=(".",))
    assert gate_for(root).run(["."]) == 1
    assert "names gone, which has no package-lock.json; remove it" in capsys.readouterr().out


def test_a_malformed_exceptions_file_fails_the_check(tmp_path, capsys):
    assert gate_for(repository(tmp_path, "exception = 3\n")).run(["."]) == 1
    assert "::error::.github/advisory-exceptions.toml: exception must be" in capsys.readouterr().out


def test_a_workspace_outside_the_repository_is_refused(tmp_path, capsys):
    assert gate_for(repository(tmp_path)).run(["../elsewhere"]) == 1
    assert "--workspace must be a repository-relative path" in capsys.readouterr().out


def test_an_unreadable_audit_fails_its_workspace_and_the_rest_still_run(tmp_path, capsys):
    gate = gate_for(repository(tmp_path), reports={".": "npm ERR! registry"})
    assert gate.run([".", APP]) == 1
    out = capsys.readouterr().out
    assert "::error::.: npm audit in" in out
    assert f"vibey-gh: {APP}: no unexcepted advisory" in out


def test_an_unexplained_report_fails_the_check(tmp_path, capsys):
    report = report_of({"a": entry("high", ["ghost"])})
    assert gate_for(repository(tmp_path, exceptions=None), reports={".": report}).run(["."]) == 1
    out = capsys.readouterr().out
    assert "npm audit puts a at high or worse with no advisory at that level behind it" in out
    assert "(1 vulnerable package(s) reported in all)" in out


def test_a_blocking_advisory_without_a_url_says_so(tmp_path, capsys):
    report = report_of({"a": entry("high", [{"name": "a", "severity": "high", "source": 9}])})
    assert gate_for(repository(tmp_path, exceptions=None), reports={".": report}).run(["."]) == 1
    assert "npm advisory 9 in a (high):  -- no URL reported" in capsys.readouterr().out


def test_the_database_is_asked_once_per_exception_however_many_workspaces_use_it(tmp_path):
    shared = ENTRY + ENTRY.replace(f'"{APP}"', '"."')
    gh = FakeGh()
    gate = gate_for(repository(tmp_path, shared), reports={".": node_forge_report()}, gh=gh)
    assert gate.run([".", APP]) == 0
    assert len(gh.calls) == 1


def test_a_saved_report_is_judged_in_place_of_running_npm(tmp_path, capsys):
    saved = tmp_path / "audit.json"
    saved.write_text(json.dumps(node_forge_report()), encoding="utf-8")

    def npm(*args, **kwargs):  # never called: the point is that npm does not run
        raise AssertionError("npm ran")

    root = repository(tmp_path)
    cfg = GhConfig(root=root)
    gate = AdvisoryGate(config=lambda: cfg, npm=npm, gh=FakeGh(), today=lambda: TODAY)
    assert gate.run([APP], saved) == 0
    assert gate.run([".", APP], saved) == 1
    assert "takes exactly one --workspace" in capsys.readouterr().out


def test_an_unreadable_saved_report_is_refused(tmp_path, capsys):
    saved = tmp_path / "audit.json"
    saved.write_text("not json", encoding="utf-8")
    assert gate_for(repository(tmp_path)).run([APP], saved) == 1
    assert f"::error::{APP}:" in capsys.readouterr().out


def test_the_cli_subcommand_dispatches_through_the_class(monkeypatch, tmp_path):
    seen: list[tuple[Any, ...]] = []
    monkeypatch.setattr(AdvisoryGate, "run", lambda self, *a: seen.append(a) or 0)
    assert cli.main(["advisory-check"]) == 0
    saved = tmp_path / "a.json"
    assert cli.main(["advisory-check", "--workspace", APP, "--audit-file", str(saved)]) == 0
    assert seen == [(["."], None), ([APP], saved)]


def test_the_cli_declares_its_options():
    parser = AdvisoryGate.declare(argparse.ArgumentParser())
    args = parser.parse_args(["--workspace", "a", "--workspace", "b"])
    assert args.workspace == ["a", "b"]


# ---------------------------------------------------------------------- the configuration


def test_advisories_load_from_toml_with_safe_defaults(tmp_path):
    assert load_config(tmp_path).advisories == AdvisoriesConfig()
    assert AdvisoriesConfig().audit_level == "high"
    (tmp_path / ".vibey-gh.toml").write_text(
        '[advisories]\naudit_level = "critical"\nexceptions_file = "sec/x.toml"\n'
        "max_exception_days = 14\nwarn_days = 3\n",
        encoding="utf-8",
    )
    assert load_config(tmp_path).advisories == AdvisoriesConfig("critical", "sec/x.toml", 14, 3)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"audit_level": "info"}, "audit_level must be one of"),
        ({"exceptions_file": "/etc/x"}, "exceptions_file"),
        ({"max_exception_days": 0}, "max_exception_days must be an integer of at least 1"),
        ({"max_exception_days": True}, "max_exception_days"),
        ({"warn_days": -1}, "warn_days must be an integer of at least 0"),
        ({"warn_days": 31}, "must not exceed max_exception_days"),
    ],
)
def test_a_malformed_advisories_table_is_refused(changes, message):
    with pytest.raises(ValueError, match=message):
        AdvisoriesConfig(**changes)


def test_an_unknown_advisories_key_is_refused():
    with pytest.raises(ValueError, match="advisories: unknown key"):
        AdvisoriesConfig.from_table({"skip": True})


def test_the_advisory_value_type_is_plain_data():
    advisory = Advisory("GHSA-a", "p", "high", "t", "u", "r")
    assert dataclasses.asdict(advisory)["package"] == "p"
