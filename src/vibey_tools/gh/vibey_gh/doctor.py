# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh doctor`: will this repository's automation actually work?

`check` answers "is the provenance intact?". Nothing answered the question every adoption
failure this family suffered was an instance of — "will the machinery function?" — and
each of the checks below encodes one failure that cost real debugging time on a live
repository before it was understood:

- a configuration key in the wrong section is silently ignored, so the feature it
  configures silently stays at defaults while every render looks green;
- `pr_automation.enabled` defaults true, so a repository without pr-evaluate.yml and
  pr-review.yml has a
  merge train that refuses every pull request with "gate has not passed" — green,
  mergeable, and stuck forever (an error only where the gates or the merge train is
  installed: a repository whose `[install] workflows` declines them both gets a note instead);
- ruff configured to select E cannot coexist with the 230-character provenance header,
  so CI fails on every stamped file;
- two workflows both deploying GitHub Pages silently contend for the same site;
- a header carrying a superseded fingerprint text sits invisible under the current one.

Everything here reads files already on disk. No network, no credentials, no execution.
"""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass
from pathlib import Path

from vibey_gh import fingerprints
from vibey_gh.config import (
    CONFIG_NAME,
    AiConfig,
    AnnounceConfig,
    BranchSyncConfig,
    ConversationConfig,
    DocumentationConfig,
    EstimateConfig,
    GhConfig,
    GithubReleaseConfig,
    IssueAutomationConfig,
    LocalModelsConfig,
    MarketplaceConfig,
    PlatformConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    PrAutomationObservabilityConfig,
    RealignConfig,
    RepositoryProfileConfig,
    RunnersConfig,
    SabbathConfig,
    SocialSignalsConfig,
    TidyConfig,
    UnattendedApprovalConfig,
    WorkflowNamesConfig,
    YankConfig,
)


@dataclass
class Finding:
    # "error" breaks the automation and exits nonzero; "warning" is a real problem that
    # blocks nothing; "info" is a fact about a deliberate choice, printed and never counted.
    severity: str
    message: str


def _fields(cls: type) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


# What each toml section may contain. Nested dataclasses are derived with
# dataclasses.fields so a new config field is recognised here automatically; the composite
# sections (whose keys load onto GhConfig itself) are spelled out to match the loader.
_SECTION_KEYS: dict[str, set[str] | None] = {
    "fingerprint": {"sources", "text", "superseded_texts", "trailer"},
    "version": {"files", "content_paths", "code_paths"},
    "branches": {"integration", "release"},
    "merge_train": {"owner", "trusted_authors", "restack_conflicts", "protected_paths"},
    "install": {"workflows", "pin_version", "union_merge_paths", "self_source", "fallback_package"},
    "pr_automation": _fields(PrAutomationConfig) | {"observability", "fallback"},
    "unattended_approval": _fields(UnattendedApprovalConfig),
    "issue_automation": _fields(IssueAutomationConfig),
    "documentation": _fields(DocumentationConfig),
    "marketplace": _fields(MarketplaceConfig),
    "yank": _fields(YankConfig),
    "ai": _fields(AiConfig),
    "conversation": _fields(ConversationConfig),
    "branch_sync": _fields(BranchSyncConfig),
    "sabbath": _fields(SabbathConfig),
    "realign": _fields(RealignConfig),
    "github_release": _fields(GithubReleaseConfig),
    # `groups` and `type_words` are sub-tables, and fields of the dataclass.
    "announce": _fields(AnnounceConfig),
    "repository_profile": _fields(RepositoryProfileConfig),
    "social_signals": _fields(SocialSignalsConfig) | {"entries"},
    "tidy": _fields(TidyConfig),
    "platform": _fields(PlatformConfig),
    "runners": _fields(RunnersConfig),
    "workflow_names": _fields(WorkflowNamesConfig),
    # `requirements` is one table per stage, and stage names are adopter-defined; the
    # loader and `vibey_gh.feasibility` validate what is inside it, loudly.
    "estimate": _fields(EstimateConfig),
    "local_models": _fields(LocalModelsConfig),
    # free-form: per-branch tables validated by their own machinery
    "rulesets": None,
}
_NESTED_KEYS: dict[str, set[str]] = {
    "pr_automation.observability": _fields(PrAutomationObservabilityConfig),
    "pr_automation.fallback": _fields(PrAutomationFallbackConfig),
}


def _check_unknown_keys(root: Path) -> list[Finding]:
    """A key in the wrong section is silently ignored — observed as a Google Analytics id
    that landed inside a comment-matched section and left GA_ID empty while every check
    stayed green. Naming the stray is the whole fix."""
    path = root / CONFIG_NAME
    if not path.is_file():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    for section, value in data.items():
        if section not in _SECTION_KEYS:
            findings.append(
                Finding(
                    "error", f"[{section}] is not a section vibey-gh reads; its keys do nothing"
                )
            )
            continue
        allowed = _SECTION_KEYS[section]
        if allowed is None or not isinstance(value, dict):
            continue
        for key, sub in value.items():
            dotted = f"{section}.{key}"
            if dotted in _NESTED_KEYS:
                for nested in sub:
                    if nested not in _NESTED_KEYS[dotted]:
                        findings.append(
                            Finding(
                                "error",
                                f"[{dotted}] {nested} is not a key vibey-gh reads; it is silently ignored",
                            )
                        )
                continue
            if key not in allowed:
                findings.append(
                    Finding(
                        "error",
                        f"[{section}] {key} is not a key vibey-gh reads; it is silently ignored",
                    )
                )
    return findings


def _check_gate_installed(cfg: GhConfig) -> list[Finding]:
    """The stuck train, reported as an error only where a train can actually get stuck.

    Every adopter of the README's starter config (`[install] workflows =
    ["provenance.yml"]`) got this as an ERROR and a nonzero exit: `pr_automation.enabled`
    defaults true, and that repository deliberately took neither the gate nor the merge
    train, so nothing in it was broken. The failure is real exactly when the gate is
    managed but absent, or when the managed merge train will demand a gate that is not
    managed. A repository that declined both gets the fact as a note, because running
    `vibey-gh merge-train` by hand would still wait on a gate that never reports.
    """
    if not cfg.pr_automation.enabled:
        return []
    split = ("pr-evaluate.yml", "pr-review.yml")
    if all((cfg.root / ".github" / "workflows" / name).is_file() for name in split):
        return []
    # `managed_workflows` is `[install] workflows`; None (the key absent) means all of them.
    # Declining the gates AND the merge train is the note-worthy starter default; taking the
    # train but not the gates is the stuck train, an error.
    declined = cfg.managed_workflows is not None and not (
        (set(split) | {"merge-train.yml"}) & set(cfg.managed_workflows)
    )
    if declined:
        return [
            Finding(
                "info",
                "pr_automation.enabled is true (the default) but [install] workflows takes "
                "neither pr-evaluate.yml/pr-review.yml nor merge-train.yml, so nothing here "
                "runs the "
                "gate. Harmless unless you run `vibey-gh merge-train` by hand — it would "
                "wait on a gate that never reports. Set [pr_automation] enabled = false to "
                "say so explicitly.",
            )
        ]
    return [
        Finding(
            "error",
            "pr_automation.enabled is true but neither .github/workflows/pr-evaluate.yml nor "
            ".github/workflows/pr-review.yml is installed — the merge train will refuse "
            "every pull request with 'PR automation gates have not passed'. Add "
            '"pr-evaluate.yml" and "pr-review.yml" to [install] workflows and run '
            "`vibey-gh install`, or set [pr_automation] enabled = false.",
        )
    ]


def _check_ruff_e501(cfg: GhConfig) -> list[Finding]:
    """ruff selecting E cannot coexist with the exact 230-character header `check`
    enforces byte-for-byte: every stamped file fails E501. Observed as a red CI on every
    source file the moment a repository was stamped."""
    path = cfg.root / "pyproject.toml"
    if not path.is_file():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    lint = (data.get("tool", {}).get("ruff", {}) or {}).get("lint", {}) or {}
    select = lint.get("select", [])
    ignore = set(lint.get("ignore", []))
    selects_e = any(entry in ("E", "E5", "E501") for entry in select)
    if not selects_e or "E501" in ignore or "E" in ignore:
        return []
    limit = (data.get("tool", {}).get("ruff", {}) or {}).get("line-length", 88)
    if len(cfg.header) <= int(limit):
        return []
    return [
        Finding(
            "error",
            f"ruff selects E with line-length {limit}, and the provenance header is "
            f'{len(cfg.header)} characters — every stamped file fails E501. Add "E501" to '
            "[tool.ruff.lint] ignore; the formatter still enforces width on code.",
        )
    ]


def _check_pages_contention(cfg: GhConfig) -> list[Finding]:
    """Two workflows calling deploy-pages silently fight over one site; whichever runs
    last wins. Observed as a hand-authored docs.yml and release-surfaces.yml trading the
    front page."""
    workflows = cfg.root / ".github" / "workflows"
    if not workflows.is_dir():
        return []
    deployers = [
        p.name
        for p in sorted(workflows.glob("*.yml"))
        if "actions/deploy-pages" in p.read_text(encoding="utf-8")
    ]
    if len(deployers) <= 1:
        return []
    names = ", ".join(deployers)
    return [
        Finding(
            "error",
            f"{len(deployers)} workflows deploy GitHub Pages ({names}) — they contend for "
            "the same site and whichever runs last wins. Keep exactly one owner.",
        )
    ]


def _check_superseded_headers(cfg: GhConfig) -> list[Finding]:
    stale = [
        p
        for p in fingerprints.sources(cfg)
        if fingerprints.superseded_headers(p.read_text(encoding="utf-8"), cfg) > 0
    ]
    if not stale:
        return []
    return [
        Finding(
            "warning",
            f"{len(stale)} file(s) carry a superseded fingerprint header — "
            "`vibey-gh check --apply` replaces them in place.",
        )
    ]


def diagnose(cfg: GhConfig | None = None, root: Path | None = None) -> list[Finding]:
    from vibey_gh.config import load_config

    cfg = cfg or load_config(root)
    findings: list[Finding] = []
    findings += _check_unknown_keys(cfg.root)
    findings += _check_gate_installed(cfg)
    findings += _check_ruff_e501(cfg)
    findings += _check_pages_contention(cfg)
    findings += _check_superseded_headers(cfg)
    return findings
