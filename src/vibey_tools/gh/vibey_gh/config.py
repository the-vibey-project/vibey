# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Configuration for the GitHub automation, read from `.vibey-gh.toml`.

Every project-specific decision lives here so the logic beside it can stay general:

    [fingerprint]
    text     = "Made with love by Vibey, ..."      # the source-header comment
    trailer  = "Made-With: Made with ❤️ by ..."    # the commit trailer
    sources  = ["tools/*.py", ".github/workflows/*.yml"]

    [version]
    files         = ["src/pkg/__init__.py", "manifest.json"]
    content_paths = ["plugins/"]     # a change here is a MINOR release
    code_paths    = ["src/"]         # a change here alone is a PATCH

    [branches]
    integration = "develop"
    release     = "main"

    [install]
    workflows = []            # omit for all of them; [] for hooks and the CLI only
    fallback_package = "vibey"  # the distribution a rendered workflow or hook installs
                              # this tooling from when the repository has no copy of it
    pin_version = false       # pin that rendered `pip install vibey` to the exact
                              # version that rendered it, instead of the latest release

    [issue_automation]
    enabled        = true               # propose a solution branch for a published issue
    branch_prefix  = "vibey-gh/issue"   # namespace every proposal branch lives under
    required_label = "vibey-gh:solve"   # what opts an outside author's issue in

    [platform]
    kind = "github"         # which forge the repository lives on; github is the one adapter
    host = "github.com"     # that forge's host, for GitHub Enterprise Server and its like
    repository = "owner/name"  # optional namespace; otherwise read origin's URL
    token_env = "GITLAB_TOKEN"  # name of the environment variable, never the secret itself

Absent keys fall back to the defaults below, so a repository that agrees with them needs
    no file at all. `tomllib` is stdlib from 3.11, and this package requires Python 3.12+.
"""

from __future__ import annotations

import dataclasses
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from vibey_gh.forge import ForgeKind

CONFIG_NAME = ".vibey-gh.toml"


def _finite_forecast_number(name: str, value: object) -> float:
    """Return a real finite forecast number, rejecting bool's ``int`` inheritance."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be a finite number: {value!r}")  # noqa: TRY004
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number: {value!r}")
    return float(value)


DEFAULT_TEXT = (
    "Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), "
    "Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) "
    "([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/))."
)
# Every text this project has EVER stamped. When `fingerprint.text` changes, `check
# --apply` must REPLACE a header carrying one of these rather than stack the new header
# above it — stacking is exactly what happened the last time the text changed, and it left
# 770 files across five repositories carrying two provenance comments while `check`
# reported ok. The version deriver discounts these the same way it discounts the current
# text, so a migration sweep is not a release.
DEFAULT_SUPERSEDED_TEXTS = (
    # The old text keeps the OLD url on purpose: this list exists to RECOGNISE what was
    # previously stamped, and a sweep that "fixes" this line breaks the recognition.
    #
    # The repositories moved to the `the-vibey-project` organisation, and GitHub Pages
    # follows the repository: `adammatthewsteinberger.github.io/vibey/` now lives only as
    # long as GitHub's transfer redirect does. The product link in the header had to move
    # with it. The author link did not — the person is unchanged by the transfer.
    (
        "Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), "
        "Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) "
        "([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/))."
    ),
    (
        "Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), "
        "Developed by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com/) "
        "([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/))."
    ),
    "Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.",
)
DEFAULT_TRAILER_KEY = "Made-With"
DEFAULT_TRAILER = f"{DEFAULT_TRAILER_KEY}: {DEFAULT_TEXT}"
DEFAULT_SOURCES = ("tools/*.py", "src/**/*.py", ".github/workflows/*.yml")
# Workflows whose completion makes a pull request worth re-evaluating. Only names a
# repository plausibly has: "API drift (Cloud Agents OpenAPI)" used to be here and is not
# an adopter's workflow at all — it is this project's own five-surface self-test, so every
# adopter had to notice it and take it back out.
# This list is two things at once, and the second is easy to miss: it names the workflows
# whose completion re-triggers evaluation, *and* it is rendered into `pr-evaluate.yml`'s
# `workflow_run` trigger. So a workflow whose check gates a merge but is absent here can
# never announce that it finished — the rollup counts it as pending, the last scan to
# complete triggers the final evaluation, and if this one finishes after that, nothing
# looks again. `Conventional Commits` is in this list for exactly that reason: it is a
# managed template, its `enforce` check gates, and leaving it out deadlocked a pull
# request that had nothing wrong with it.
DEFAULT_SCAN_WORKFLOWS = (
    "CI",
    "Provenance",
    "CodeQL",
    "Docs",
    "Conventional Commits",
)
# Files every branch appends to, so two branches almost always touch the same lines.
# Git's built-in `union` driver keeps both sides instead of reporting a conflict, which is
# exactly right for an append-only log and wrong for anything with structure.
DEFAULT_UNION_MERGE_PATHS = ("CHANGELOG.md",)
DEFAULT_IGNORED_CHECKS = (
    # The two gates the split PR automation renders: the scan gate (`pr-evaluate.yml`)
    # and the review gate (`pr-review.yml`). `PR automation / gate` is kept for the
    # check runs a pre-split workflow left on today's heads: ignoring them costs
    # nothing, and a green run of an automation that no longer exists must never be
    # counted as a scan that repaired itself.
    "PR evaluate / gate",
    "PR review / gate",
    "PR automation / gate",
    "gate",
    "Merge train / merge",
)
# A required status check names a *check run* — for Actions, a job's `name:` — not the
# workflow that contains it. `DEFAULT_SCAN_WORKFLOWS` above names workflows and must never
# be reused here, however tempting the overlap looks: "CI" and "Docs" are workflows whose
# jobs are called "Lint"/"Build"/"Test (…)" and "Documentation contract", so a ruleset
# requiring "CI" waits for a check that cannot arrive and blocks every merge to the branch
# it protects. Rulesets have no implicit admin override, so that state is not recoverable
# by merging past it — only by editing the ruleset.
#
# These are the jobs the bundled templates render, which is the whole of what a fresh
# install can promise. An adopter's test suite is deliberately absent: vibey-gh ships no
# `ci.yml`, so naming one here would reintroduce exactly the failure above.
DEFAULT_RULESET_CHECKS = (
    "Provenance",
    "Analyze Python",
    "Documentation contract",
)
DEFAULT_INTEGRATION_RULESET_CHECKS = DEFAULT_RULESET_CHECKS + (
    "PR evaluate / gate",
    "PR review / gate",
)
DEFAULT_RELEASE_RULESET_CHECKS = DEFAULT_RULESET_CHECKS
# The repository admin role. A required check can always stop reporting — an outage, an
# exhausted budget, a renamed job, a workflow the repository chose not to install — and
# with no bypass actor that locks the branch outright, because a ruleset (unlike the
# classic branch protection it replaced) never exempts administrators on its own. This
# grants an admin no authority they lack: anyone who can bypass a ruleset can already
# rewrite it. It only removes the detour.
# Bypass actor types the rulesets API identifies by type alone. Every other type is a
# `<type>:<numeric id>` pair, and requiring the id is what keeps a typo from silently
# granting bypass to the wrong team. These two have no id to give: GitHub returns
# `actor_id: null` for them, and sending one is rejected.
IDLESS_BYPASS_ACTOR_TYPES = ("OrganizationAdmin", "DeployKey")

DEFAULT_RULESET_BYPASS_ACTORS = ("RepositoryRole:5",)
# Managed issue-automation labels. They live here rather than beside the policy because
# `IssueAutomationConfig` defaults name one of them, and configuration must not import
# the module that imports configuration.
SOLVE_LABEL = "vibey-gh:solve"
SOLVING_LABEL = "vibey-gh:solving"
PROPOSED_LABEL = "vibey-gh:solution-proposed"
SOLVE_EXHAUSTED_LABEL = "vibey-gh:solve-exhausted"
SOLVE_BLOCKED_LABEL = "vibey-gh:solve-blocked"
DEFAULT_IGNORED_ISSUE_LABELS = (
    "question",
    "discussion",
    "duplicate",
    "wontfix",
    SOLVE_BLOCKED_LABEL,
)
GOOGLE_ANALYTICS_ID_PATTERN = re.compile(r"^G-[A-Z0-9]+$")
# A GitHub secret name, which is what `${{ secrets.NAME }}` will be rendered around. Only
# this shape is accepted, so a configured name cannot close the expression and append an
# arbitrary one of its own.
SECRET_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Where a repository's automation documentation lives. Deliberately NOT `.github/README.md`:
# GitHub resolves a repository's landing README as `.github/README.md` first and the root
# `README.md` only if that is absent, so requiring the former replaced every adopter's
# product README with maintainer-facing automation notes on their repository's front page.
# Both this project and its first adopter were serving the wrong document, and nothing in
# the file itself could fix it — the name is what GitHub reads.
DEFAULT_AUTOMATION_DOC = ".github/AUTOMATION.md"
# The agent-docs layout every repository this tool manages is expected to carry. These
# files describe the ADOPTER's own project and make it navigable to an agent, so unlike the
# narrative contracts on `DocumentationConfig` — which default to empty and are declared
# per repository — they are a standard worth holding everyone to.
DEFAULT_DOCUMENTATION_FILES = (
    ".claude-plugin/marketplace.json",
    ".claude/settings.json",
    ".claude/skills/README.md",
    ".cursor/rules/project.mdc",
    ".agents/skills/README.md",
    ".agent/rules/project.md",
    ".githooks/README.md",
    DEFAULT_AUTOMATION_DOC,
    "docs/index.md",
    "docs/project.mmd",
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GEMINI.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
)


@dataclass(frozen=True)
class WorkflowNamesConfig:
    """Every workflow name the rendered templates depend on.

    Templates chain by `workflow_run`, which matches a workflow's display NAME.
    Those names were hardcoded, which silently assumed every adopter calls its
    pipeline "CI" and its publish step "Release". vibey-bootstrap names its
    pipeline "CI/CD Pipeline", so the trigger never matched, its channel site
    never deployed, and its Pages URL served a fossil from an older publisher —
    with no error anywhere, because a `workflow_run` trigger that never matches
    simply never runs. The silence is the whole danger.

    Two kinds live here. `ci` and `release` name workflows the ADOPTER owns and
    vibey-gh never renders, so they genuinely differ per repository. The rest
    name vibey-gh's own templates; they are configurable so an adopter may
    rename them, and each template renders its own `name:` from the same field
    the other templates trigger on — so a rename moves both sides at once and
    the chain cannot drift.
    """

    # The adopter's own workflows — vibey-gh renders neither.
    ci: str = "CI"
    release: str = "Release"
    # vibey-gh's own templates.
    provenance: str = "Provenance"
    pr_evaluate: str = "PR evaluate"
    pr_review: str = "PR review"
    merge_train: str = "Merge train"
    promote: str = "Promote"
    release_surfaces: str = "Release surfaces"
    release_repair: str = "Release repair"
    github_release: str = "GitHub Release"
    repository_profile: str = "Repository profile"


# The forges `[platform] kind` accepts today: the ones with an adapter. `ForgeKind` names
# more, because the standard is written for every forge (#138), but a kind with no adapter
# is refused here, at load, rather than accepted and then quietly driven as GitHub by every
# module that has not moved onto the adapter yet. `ForgeSelector.kinds` must equal this,
# and a test holds them together.
ADAPTED_PLATFORM_KINDS = tuple(kind.value for kind in ForgeKind)

# A bare host name, optionally with a port: what `gh` takes as `GH_HOST`. No scheme, path,
# user or whitespace, so the value cannot smuggle anything else into the client's reading.
_HOST_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::[0-9]{1,5})?")


@dataclass(frozen=True)
class PlatformConfig:
    """Which forge this repository lives on, and where (#138).

    `kind` selects the forge adapter, which is the only code allowed to know what platform
    it is speaking to. `host` is that forge's host: `github.com`, the default, is the host
    `gh` assumes on its own and changes nothing; any other host (a GitHub Enterprise Server)
    is handed to `gh` as `GH_HOST`, so every call the adapter makes goes there.

    Only the calls that have moved onto the adapter read this — today the clean-repo
    survey's two forge reads. Every other command still runs `gh` the way it always has,
    which is exactly why a kind without an adapter is refused rather than half-honoured.
    """

    kind: str = ForgeKind.GITHUB.value
    host: str = "github.com"
    repository: str = ""
    token_env: str = ""

    def __post_init__(self) -> None:
        kinds = tuple(kind.value for kind in ForgeKind)
        if self.kind not in kinds:
            raise ValueError(f"platform.kind must be one of {', '.join(kinds)}: {self.kind!r}")
        if (
            self.kind not in ADAPTED_PLATFORM_KINDS
        ):  # pragma: no cover - enum and adapters move together
            raise ValueError(self.not_adapted(self.kind))
        if not isinstance(self.host, str) or not _HOST_RE.fullmatch(self.host):
            raise ValueError(
                "platform.host must be a bare host name, optionally with a port "
                f"(no scheme or path): {self.host!r}"
            )
        if self.repository and (
            self.repository.startswith("/")
            or self.repository.endswith("/")
            or any(part == "" for part in self.repository.split("/"))
            or any(char.isspace() for char in self.repository)
        ):
            raise ValueError("platform.repository must be a forge namespace such as 'owner/name'")
        if self.token_env and not SECRET_NAME_PATTERN.fullmatch(self.token_env):
            raise ValueError(
                "platform.token_env must be an environment variable name, not a secret"
            )

    @staticmethod
    def not_adapted(kind: str) -> str:
        """The one sentence for a forge the standard names but no adapter drives yet."""
        return (
            f"platform.kind = {kind!r}: the {kind} adapter is not implemented yet; "
            f"vibey-gh drives {', '.join(ADAPTED_PLATFORM_KINDS)} only (#138)"
        )


@dataclass(frozen=True)
class TidyConfig:
    """The clean repo (sub-doctrine 9.a): technical clutter is drag and does not
    accumulate; human messiness is expressly welcome and never touched.

    `enabled` gates the survey's presence in `check --ci` (cloud classes only
    there — an ephemeral runner has no worktrees worth judging). `keep_branches`
    extends the always-kept set beyond the integration and release branches."""

    enabled: bool = True
    keep_branches: tuple[str, ...] = ()
    # Does clutter found by `check --ci` FAIL the build, or is it an advisory line?
    # The verdict is a key rather than a hard-coded judgment (ADR-0018), and it
    # defaults to advisory because the survey judges a repository's ACCUMULATED
    # past: an adopter upgrading into the release that added it would otherwise
    # find its CI red for branches that were already there, over a class of mess
    # no commit in the pull request created. Turn it on once the repository is
    # clean, and clutter can never come back.
    fail_check: bool = False
    # Squash/rebase flows rewrite SHAs, so ancestry cannot prove a merged branch's
    # content landed — the forge deleting the remote branch at merge time is the
    # proof instead. True admits that proof for [gone] locals; false reports them
    # and touches nothing.
    trust_forge_deletions: bool = True


SOCIAL_SIGNAL_KINDS = (
    # Comprehensive to the authentic social-signal classes of the current day
    # (sub-doctrine 4.a). Extend this tuple when the world grows a new REAL one.
    "testimony",  # a person's own words about the work
    "endorsement",  # an institution's backing — a government, a company, a body
    "adoption",  # a named adopter: "this is used by"
    "case-study",  # a written account of real use
    "review",  # a rating or review on a third-party surface
    "community",  # a human-generated count: stars, members, contributors
    "citation",  # scholarly citation of the project's work
    "press",  # media coverage by a named author and outlet
    "contributor",  # a named human who built part of this
    "backer",  # a person or institution that funded the work
    "talk",  # a conference or meetup appearance by a named speaker
    "certification",  # an accreditation issued by a real institution
)


@dataclass(frozen=True)
class SocialSignalEntry:
    """One authentic social signal from one real human agent.

    `agent` names the person or institution whose signal this is; `source` is the
    provenance hyperlink rendered at the point of reference; `human_attested` is the
    operator's own attestation — set by the human who added the entry — that the
    signal is genuine and comes from a real human agent, never a machine. Validation
    refuses an entry without all three: machine-manufactured social proof is false
    witness, and the config layer is the first gate that stops it.
    """

    kind: str
    agent: str
    source: str
    human_attested: bool = False
    # The 4.a amendment — verification expires: the ISO date the operator last
    # verified this signal's authenticity. Required; a claim without a date cannot
    # age, and every authenticity claim must age.
    attested_on: str = ""
    # A signal discovered inauthentic is revoked: it renders nowhere, forever, and
    # can never be re-attested — the tombstone outlives every optimism.
    revoked: bool = False
    quote: str = ""
    role: str = ""
    org: str = ""
    date: str = ""
    value: str = ""


@dataclass(frozen=True)
class SocialSignalsConfig:
    """The social-signals surface (sub-doctrine 4.a): opt-in, forever available.

    Off by default and enabled per repository — but the FEATURE is permanently
    available, at all times and in all places, as the sub-doctrine demands. Every
    rendered signal is 100% authentic and from a real human agent (a person, or an
    institution of persons such as a government); never from a machine.
    """

    enabled: bool = False
    heading: str = "Real people, real words"
    # The 4.a amendment: authenticity is re-verified, never remembered. An
    # attestation older than this blocks the check until a human re-verifies and
    # re-dates it. Zero would mean attestations never age; validation refuses it.
    max_attestation_age_days: int = 365
    entries: tuple[SocialSignalEntry, ...] = ()

    def validate(self) -> None:
        if not self.enabled:
            return
        if self.max_attestation_age_days <= 0:
            raise ValueError(
                "social_signals.max_attestation_age_days must be positive: the 4.a"
                " amendment forbids attestations that never age — authenticity is"
                " re-verified, never remembered"
            )
        import datetime

        for i, e in enumerate(self.entries):
            where = f"social_signals.entries[{i}]"
            if e.revoked:
                if e.human_attested:
                    raise ValueError(
                        f"{where}: revoked and attested cannot coexist — a signal"
                        " discovered inauthentic is removed permanently and can never"
                        " be re-attested, no exceptions ever (4.a amendment)"
                    )
                continue
            if e.kind not in SOCIAL_SIGNAL_KINDS:
                raise ValueError(f"{where}: unknown kind {e.kind!r}; one of {SOCIAL_SIGNAL_KINDS}")
            if not e.agent.strip():
                raise ValueError(f"{where}: every signal names its real human agent")
            if not e.source.startswith("https://"):
                raise ValueError(f"{where}: source must be an https provenance link")
            if not e.human_attested:
                raise ValueError(
                    f"{where}: human_attested = true is the operator's own attestation that"
                    " this signal is genuine and from a real human agent, never a machine —"
                    " an entry without it does not render (sub-doctrine 4.a)"
                )
            try:
                attested = datetime.date.fromisoformat(e.attested_on)
            except ValueError:
                raise ValueError(
                    f"{where}: attested_on must be the ISO date the human last verified"
                    " this signal — a claim without a date cannot age, and every"
                    " authenticity claim must age (4.a amendment)"
                ) from None
            age = (datetime.datetime.now(datetime.UTC).date() - attested).days
            if age > self.max_attestation_age_days:
                raise ValueError(
                    f"{where}: attestation is {age} days old, past"
                    f" max_attestation_age_days={self.max_attestation_age_days} —"
                    " a past-authentic signal is never assumed presently authentic;"
                    " re-verify and re-date attested_on (4.a amendment)"
                )
        if self.entries == ():
            raise ValueError("social_signals.enabled with no entries renders nothing honest")


@dataclass(frozen=True)
class PrAutomationObservabilityConfig:
    sanitized_progress: bool = True
    archive_execution_file: bool = True
    allow_private_full_output: bool = False


@dataclass(frozen=True)
class PrAutomationFallbackConfig:
    """A local model that reviews when the paid path returns no verdict at all.

    An exhausted API key fails the review job before the model ever runs, and because the
    gate is a required check that turns a billing problem into a hard stop on every pull
    request. This runs a local model on a self-hosted runner in that case only — never in
    place of a review that actually ran and returned findings.

    ON by default, per sub-doctrine 8.a: the sovereign path is the PREFERENCE, so it may not
    be the one that has to be opted into while the paid lane runs automatically. That is safe
    without a self-hosted runner because the HEARTBEAT gates scheduling, not this flag — a
    repository with no fresh `heartbeat_ref` simply never offers the lane, so a default of
    true costs an adopter nothing until they stand a runner up deliberately.

    The runner still deserves care once it exists: GitHub says self-hosted runners should
    "almost never be used for public repositories" because any user can open a pull request
    against them. `trusted_only` keeps fork pull requests away from it entirely, and leaving
    that true is what makes the configuration defensible on a public repository.
    """

    enabled: bool = True
    runner_label: str = "vibey-local"
    model: str = "qwen2.5-coder:14b"
    base_url: str = "http://127.0.0.1:11434"
    trusted_only: bool = True
    max_diff_chars: int = 60000
    timeout_seconds: int = 600
    heartbeat_ref: str = "refs/vibey-gh/sovereign-heartbeat"
    heartbeat_max_age_minutes: int = 15

    def __post_init__(self) -> None:
        if not self.enabled:
            return
        for name, value in (
            ("runner_label", self.runner_label),
            ("model", self.model),
            ("base_url", self.base_url),
        ):
            if not value.strip():
                raise ValueError(f"pr_automation.fallback.{name} must not be empty")
        if self.max_diff_chars < 1000:
            raise ValueError("pr_automation.fallback.max_diff_chars must be at least 1000")
        if not 30 <= self.timeout_seconds <= 3600:
            raise ValueError("pr_automation.fallback.timeout_seconds must be between 30 and 3600")
        if not self.heartbeat_ref.startswith("refs/"):
            raise ValueError("pr_automation.fallback.heartbeat_ref must be a full refs/ path")
        if self.heartbeat_ref.startswith("refs/heads/"):
            raise ValueError(
                "pr_automation.fallback.heartbeat_ref must not be a branch — a heartbeat"
                " under refs/heads/ becomes a branch every tidy pass has to reason about"
            )
        if not 1 <= self.heartbeat_max_age_minutes <= 1440:
            raise ValueError(
                "pr_automation.fallback.heartbeat_max_age_minutes must be between 1 and 1440"
            )


@dataclass(frozen=True)
class PrAutomationConfig:
    enabled: bool = True
    scan_workflows: tuple[str, ...] = DEFAULT_SCAN_WORKFLOWS
    ignored_checks: tuple[str, ...] = DEFAULT_IGNORED_CHECKS
    max_repair_attempts: int = 3
    model: str = "claude-sonnet-5"
    review_untrusted_authors: bool = True
    repair_untrusted_authors: bool = True
    replace_fork_prs: bool = True
    retain_schedule_backstop: bool = True
    # Claude Code plugin marketplaces and plugins the review, repair, and conflict jobs
    # load. Empty by default: the marketplace these templates once hard-coded
    # (github.com/the-vibey-project/vibey-skills) no longer exists, and a marketplace
    # that cannot be cloned fails the review outright rather than reviewing without it.
    # An entry is an https Git URL, or a path relative to the repository root, which is
    # read from the trusted checkout of the default branch -- never from the pull
    # request's own tree, so a contributor cannot choose the plugins that review them.
    plugin_marketplaces: tuple[str, ...] = ()
    plugins: tuple[str, ...] = ()
    # Whether `conventional-commits.yml` REWRITES a nonconforming subject, or only
    # reports it. True by default because that is what the workflow has always done and
    # ADR-0018 forbids quietly taking a working capability away from an adopter.
    #
    # The trade a repository is choosing here is real: normalisation produces
    # `chore: <the original subject>`, which conforms without choosing a meaningful type,
    # so a bug fix normalised this way is filed as a chore -- and in a repository whose
    # changelog sections are derived from the type, that is a wrong label rather than a
    # missing one. Set it false where the author should pick the type themselves; the
    # check still runs and still fails, just without rewriting anybody's history.
    normalise_commit_subjects: bool = True
    observability: PrAutomationObservabilityConfig = PrAutomationObservabilityConfig()
    fallback: PrAutomationFallbackConfig = PrAutomationFallbackConfig()

    def __post_init__(self) -> None:
        _unique_nonempty("pr_automation.scan_workflows", self.scan_workflows)
        _unique_nonempty("pr_automation.ignored_checks", self.ignored_checks)
        _unique_nonempty("pr_automation.plugin_marketplaces", self.plugin_marketplaces)
        _unique_nonempty("pr_automation.plugins", self.plugins)
        for entry in self.plugin_marketplaces:
            if entry.startswith("https://"):
                if any(char.isspace() for char in entry):
                    raise ValueError(
                        f"pr_automation.plugin_marketplaces URL contains whitespace: {entry!r}"
                    )
            elif (
                entry.startswith(("/", "~"))
                or "://" in entry
                or ".." in Path(entry).parts
                or any(char.isspace() for char in entry)
            ):
                raise ValueError(
                    "pr_automation.plugin_marketplaces entries must be an https Git URL or a"
                    f" repository-relative path without '..': {entry!r}"
                )
        for plugin in self.plugins:
            name, at, marketplace = plugin.partition("@")
            if not (name and at and marketplace) or any(char.isspace() for char in plugin):
                raise ValueError(
                    f"pr_automation.plugins entries must be '<plugin>@<marketplace>': {plugin!r}"
                )
        if self.plugins and not self.plugin_marketplaces:
            raise ValueError("pr_automation.plugins needs at least one plugin_marketplaces entry")
        if self.enabled and not self.scan_workflows:
            raise ValueError("pr_automation.scan_workflows must not be empty when enabled")
        if not 1 <= self.max_repair_attempts <= 10:
            raise ValueError("pr_automation.max_repair_attempts must be between 1 and 10")
        if not self.model.strip():
            raise ValueError("pr_automation.model must not be empty")


def _unique_nonempty(name: str, values: tuple[str, ...]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{name} entries must be non-empty")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} entries must be unique")


def _merge_queue(section: dict, default_merge_method: str) -> MergeQueueConfig:
    """The declared queue for one branch, defaulting to that branch's own merge style.

    The default is passed in rather than fixed here because the two permanent branches do
    not merge the same way: feature pull requests squash into the integration branch and
    the release branch takes a rebase, so one constant would be wrong for one of them.
    """
    defaults = MergeQueueConfig(merge_method=default_merge_method)
    return MergeQueueConfig(
        enabled=section.get("enabled", defaults.enabled),
        merge_method=section.get("merge_method", defaults.merge_method),
        grouping_strategy=section.get("grouping_strategy", defaults.grouping_strategy),
        check_response_timeout_minutes=section.get(
            "check_response_timeout_minutes", defaults.check_response_timeout_minutes
        ),
        max_entries_to_build=section.get("max_entries_to_build", defaults.max_entries_to_build),
        max_entries_to_merge=section.get("max_entries_to_merge", defaults.max_entries_to_merge),
        min_entries_to_merge=section.get("min_entries_to_merge", defaults.min_entries_to_merge),
        min_entries_to_merge_wait_minutes=section.get(
            "min_entries_to_merge_wait_minutes", defaults.min_entries_to_merge_wait_minutes
        ),
    )


def _ruleset(
    section: dict,
    default_checks: tuple[str, ...],
    default_approvals: int,
    default_merge_method: str = "SQUASH",
) -> RulesetConfig:
    return RulesetConfig(
        merge_queue=_merge_queue(section.get("merge_queue", {}), default_merge_method),
        required_checks=tuple(section.get("required_checks", default_checks)),
        strict_required_checks=section.get("strict_required_checks", True),
        required_approvals=section.get("required_approvals", default_approvals),
        dismiss_stale_reviews=section.get("dismiss_stale_reviews", True),
        require_code_owner_review=section.get("require_code_owner_review", False),
        require_conversation_resolution=section.get("require_conversation_resolution", True),
        require_linear_history=section.get("require_linear_history", True),
        require_signed_commits=section.get("require_signed_commits", False),
        allow_force_pushes=section.get("allow_force_pushes", False),
        allow_deletions=section.get("allow_deletions", False),
        bypass_actors=tuple(section.get("bypass_actors", DEFAULT_RULESET_BYPASS_ACTORS)),
    )


@dataclass(frozen=True)
class IssueAutomationConfig:
    """Policy for autonomously proposing a solution to a published issue.

    Issue text is contributor-controlled, so the defaults are deliberately closed for
    anyone outside the trusted set: an outside issue is solved only after a maintainer
    applies `required_label`. Everything a consuming repository could reasonably want to
    change — the model, the budget, the branch namespace, the base branch, which labels
    opt in or out, and whether a pull request is opened at all — is configuration rather
    than a code change, because this ships to repositories the author never sees.
    """

    enabled: bool = True
    model: str = "claude-sonnet-5"
    max_attempts: int = 2
    max_turns: int = 200
    branch_prefix: str = "vibey-gh/issue"
    base_branch: str = ""
    solve_untrusted_authors: bool = False
    required_label: str = SOLVE_LABEL
    trigger_labels: tuple[str, ...] = ()
    ignored_labels: tuple[str, ...] = DEFAULT_IGNORED_ISSUE_LABELS
    open_pull_request: bool = True
    draft_pull_request: bool = True
    retain_schedule_backstop: bool = True
    # Post a bounded local-model triage comment when the paid solve produced nothing —
    # the issue path's counterpart to [pr_automation.fallback], sharing its runner, model
    # and limits. On by default per sub-doctrine 8.a (#277): the sovereign path is the
    # preference, not the opt-in. A repository with no runner loses nothing, because the
    # job is scheduled only while the sovereign heartbeat is fresh, not on this flag alone.
    fallback_enabled: bool = True

    def __post_init__(self) -> None:
        _unique_nonempty("issue_automation.trigger_labels", self.trigger_labels)
        _unique_nonempty("issue_automation.ignored_labels", self.ignored_labels)
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("issue_automation.max_attempts must be between 1 and 10")
        if not 1 <= self.max_turns <= 1000:
            raise ValueError("issue_automation.max_turns must be between 1 and 1000")
        if not self.model.strip():
            raise ValueError("issue_automation.model must not be empty")
        prefix = self.branch_prefix
        if not prefix.strip() or any(char.isspace() for char in prefix):
            raise ValueError("issue_automation.branch_prefix must be non-empty and unspaced")
        if prefix.startswith(("-", "/")) or prefix.endswith("/") or ":" in prefix or ".." in prefix:
            raise ValueError(f"issue_automation.branch_prefix is unsafe: {prefix!r}")
        if any(char.isspace() for char in self.required_label):
            raise ValueError("issue_automation.required_label must contain no whitespace")


@dataclass(frozen=True)
class AiConfig:
    """Where the AI steps send their requests, and which secret authorises them.

    Every AI step runs Claude Code, which honours `ANTHROPIC_BASE_URL`. Pointing that at a
    gateway serving the Anthropic Messages API — LiteLLM and friends translate it to
    Gemini, Qwen, a local model, anything — is the whole of what it takes to run this
    automation somewhere other than Anthropic. The alternative, teaching five workflows
    about a second vendor's request shape, buys nothing the gateway does not.

    Nothing here changes behaviour until `base_url` is set: empty means the default
    endpoint, exactly as before this existed.

    `auth_secret` names a repository secret rather than carrying a token, because a
    configuration file is committed and a token must never be. Both header conventions are
    populated from it when a gateway is in use — Claude Code sends `x-api-key`, while some
    gateways read `Authorization` — so one secret works either way.
    """

    base_url: str = ""
    auth_secret: str = "ANTHROPIC_API_KEY"

    def __post_init__(self) -> None:
        if not SECRET_NAME_PATTERN.match(self.auth_secret):
            raise ValueError(f"ai.auth_secret is not a valid secret name: {self.auth_secret!r}")
        if self.base_url:
            if not self.base_url.startswith(("http://", "https://")):
                raise ValueError(f"ai.base_url must be an http(s) URL: {self.base_url!r}")
            # It renders into a workflow as a YAML scalar; whitespace would either break
            # the document or smuggle a second key in beside it.
            if any(character.isspace() for character in self.base_url):
                raise ValueError("ai.base_url must contain no whitespace")


@dataclass(frozen=True)
class ConversationConfig:
    """Answering a mention in a comment, and how far that answer may reach.

    Comments are the least guarded input a repository has, so the defaults are closed:
    outside commenters get no response at all, because answering everyone is a spending
    decision rather than something to inherit. `ignore_actors` is the loop guard — the
    automation must never answer its own reply, which would run and bill forever.
    """

    enabled: bool = True
    trigger: str = "@vibey-gh"
    model: str = "claude-sonnet-5"
    max_interactions: int = 10
    respond_to_untrusted: bool = False
    allow_changes: bool = True
    ignore_actors: tuple[str, ...] = ("vibey[bot]", "github-actions[bot]", "claude[bot]")

    def __post_init__(self) -> None:
        _unique_nonempty("conversation.ignore_actors", self.ignore_actors)
        if not self.trigger.strip() or any(char.isspace() for char in self.trigger):
            raise ValueError("conversation.trigger must be non-empty and contain no whitespace")
        if not 1 <= self.max_interactions <= 100:
            raise ValueError("conversation.max_interactions must be between 1 and 100")
        if not self.model.strip():
            raise ValueError("conversation.model must not be empty")
        if self.enabled and not self.ignore_actors:
            raise ValueError(
                "conversation.ignore_actors must name the automation's own identities, "
                "or it will answer its own replies forever"
            )


@dataclass(frozen=True)
class BranchSyncConfig:
    """Keeping open topic branches current with the integration branch.

    A branch that sits behind eventually conflicts, and the longer it waits the worse the
    conflict — so syncing on every merge stops that accumulating. A contributor's branch
    is updated the way GitHub's own "Update branch" button does it, as a merge and never a
    rewrite, so nobody's history is rearranged underneath them.
    """

    enabled: bool = True
    update_contributor_branches: bool = True
    max_self_heals: int = 2

    def __post_init__(self) -> None:
        if not 0 <= self.max_self_heals <= 10:
            raise ValueError("branch_sync.max_self_heals must be between 0 and 10")


@dataclass(frozen=True)
class RealignConfig:
    """What happens to open topic branches when realign rewrites the integration branch.

    Realign replaces commits with rewritten copies, which strands any branch cut from one
    of them. These keys decide how much the automation may do about that on its own —
    rewriting and deleting branches is exactly the kind of thing an adopting repository
    should be able to switch off without editing code.
    """

    reconcile_branches: bool = True
    automation_prefixes: tuple[str, ...] = ("vibey-gh/",)
    close_duplicates: bool = True
    delete_duplicate_branches: bool = True
    notify_contributor_branches: bool = True

    def __post_init__(self) -> None:
        _unique_nonempty("realign.automation_prefixes", self.automation_prefixes)
        if self.reconcile_branches and not self.automation_prefixes:
            raise ValueError("realign.automation_prefixes must not be empty when reconciling")
        if any(
            prefix.startswith(("-", "/")) or ":" in prefix or ".." in prefix
            for prefix in self.automation_prefixes
        ):
            raise ValueError("realign.automation_prefixes entries must be safe ref prefixes")


@dataclass(frozen=True)
class GithubReleaseConfig:
    """How a release-branch commit becomes an immutable tag and GitHub Release.

    Not every push to the release branch carries a new version — a docs-only or
    tooling-only promotion is expected and, per `version.content_paths`/`code_paths`,
    deliberately publishes nothing new. `require_new_version` decides what that means: by
    default such a push is a no-op, because a version already tagged elsewhere is the
    normal, frequent case, not an error. Set it when the adopting repository's release
    branch should carry a new version on every push, so a tag that would otherwise move
    silently reports as the mistake it actually is.
    """

    enabled: bool = True
    tag_prefix: str = "v"
    generate_notes: bool = True
    require_new_version: bool = False

    def __post_init__(self) -> None:
        if not self.tag_prefix or any(char.isspace() for char in self.tag_prefix):
            raise ValueError(
                "github_release.tag_prefix must be non-empty and contain no whitespace"
            )


@dataclass(frozen=True)
class YankConfig:
    """Report which releases an index holds below the one just published.

    Named `yank` because that is what a human does with the list. **Nothing here yanks
    anything: PyPI provides no way to.** The legacy upload endpoint answers `405 Method Not
    Allowed` for `:action=yank`, the `/manage/...` route the web UI uses is CSRF-protected
    against non-browser callers, and programmatic access is an open upstream request
    (pypa/packaging-problems#633, pypi/warehouse#12708). No token changes that. See
    vibey_gh/yank.py.

    That is arguably correct. PEP 592 defines a yanked release as one with "a serious
    problem which should prevent it from being installed" — a distress signal, not a
    tidiness marker. Installers still resolve a yanked version when a pin demands one, so
    nothing is reclaimed; what changes is that everyone pinned to it starts seeing a warning
    about a release that may be fine. The manual click keeps that deliberate.

    Off by default on both indexes and separately switchable, because even the report is
    noise for a repository that does not want it. The version just published is never
    listed, whatever these are set to.
    """

    pypi: bool = False
    testpypi: bool = False
    # How many releases below the newest to leave alone, so a rollback target survives.
    # 0 reports everything superseded.
    keep: int = 0
    # Article V.4 of the Constitution: a RATIFIED change to any of these files supersedes
    # every previous release, zero exceptions — `keep` and the per-index switches above are
    # overridden for that release. fnmatch globs, repository-relative.
    governance_paths: tuple[str, ...] = (
        "docs/constitution.md",
        "docs/commandments.md",
        "docs/bill-of-rights.md",
        "docs/sd-*.md",
    )

    def __post_init__(self) -> None:
        if self.keep < 0:
            raise ValueError("yank.keep must not be negative")


# The two enumerated `merge_queue` parameters, as GitHub defines them. Named here rather
# than inlined in a check so an error can print the whole set and a reader can see the
# choices without opening the API reference.
MERGE_QUEUE_MERGE_METHODS = ("MERGE", "SQUASH", "REBASE")
MERGE_QUEUE_GROUPING_STRATEGIES = ("ALLGREEN", "HEADGREEN")


@dataclass(frozen=True)
class MergeQueueConfig:
    """The merge queue declared for one permanent branch (ADR-0036).

    All seven of GitHub's `merge_queue` parameters are fields, because the API requires
    all seven and a value hard-coded here would be a decision taken away from the next
    adopter, silently (ADR-0018). The defaults are the shape this repository runs, not a
    claim about anyone else's branch flow.

    `enabled` defaults to false. A merge queue changes when and how every merge happens
    for everyone who uses the repository, and switching that on by upgrading a tool would
    be a behaviour change nobody asked for.
    """

    enabled: bool = False
    merge_method: str = "SQUASH"
    grouping_strategy: str = "ALLGREEN"
    check_response_timeout_minutes: int = 60
    max_entries_to_build: int = 5
    max_entries_to_merge: int = 5
    min_entries_to_merge: int = 1
    min_entries_to_merge_wait_minutes: int = 5

    def __post_init__(self) -> None:
        if self.merge_method not in MERGE_QUEUE_MERGE_METHODS:
            raise ValueError(
                "rulesets.merge_queue.merge_method must be one of "
                f"{', '.join(MERGE_QUEUE_MERGE_METHODS)}, got {self.merge_method!r}"
            )
        if self.grouping_strategy not in MERGE_QUEUE_GROUPING_STRATEGIES:
            raise ValueError(
                "rulesets.merge_queue.grouping_strategy must be one of "
                f"{', '.join(MERGE_QUEUE_GROUPING_STRATEGIES)}, got {self.grouping_strategy!r}"
            )
        for name, value, low, high in (
            ("check_response_timeout_minutes", self.check_response_timeout_minutes, 1, 360),
            ("max_entries_to_build", self.max_entries_to_build, 1, 100),
            ("max_entries_to_merge", self.max_entries_to_merge, 1, 100),
            ("min_entries_to_merge", self.min_entries_to_merge, 1, 100),
            ("min_entries_to_merge_wait_minutes", self.min_entries_to_merge_wait_minutes, 0, 360),
        ):
            if not low <= value <= high:
                raise ValueError(
                    f"rulesets.merge_queue.{name} must be between {low} and {high}, got {value}"
                )
        if self.min_entries_to_merge > self.max_entries_to_merge:
            # A floor above the ceiling is a queue that can never merge a group: it would
            # wait for more entries than it is ever allowed to take.
            raise ValueError(
                "rulesets.merge_queue.min_entries_to_merge must not exceed max_entries_to_merge"
            )


@dataclass(frozen=True)
class RulesetConfig:
    """Declared branch-protection policy for one permanent branch.

    `allow_force_pushes` and `allow_deletions` are rejected outright rather than merely
    defaulted, because this config shape only ever targets a permanent branch: the
    non-deletion, non-rewrite guarantee this project claims cannot become one keystroke
    away from silently disabled.
    """

    required_checks: tuple[str, ...] = ()
    strict_required_checks: bool = True
    required_approvals: int = 0
    dismiss_stale_reviews: bool = True
    # A review from the owner CODEOWNERS names, on a pull request touching an owned path.
    # False by default because it is inert without a CODEOWNERS file and, with one, blocks
    # every pull request touching an owned path until that owner approves -- a decision
    # about who may merge what, which an upgrade must never make for an adopter.
    require_code_owner_review: bool = False
    require_conversation_resolution: bool = True
    require_linear_history: bool = True
    require_signed_commits: bool = False
    allow_force_pushes: bool = False
    allow_deletions: bool = False
    bypass_actors: tuple[str, ...] = DEFAULT_RULESET_BYPASS_ACTORS
    merge_queue: MergeQueueConfig = MergeQueueConfig()

    def __post_init__(self) -> None:
        if (
            self.merge_queue.enabled
            and self.require_linear_history
            and self.merge_queue.merge_method == "MERGE"
        ):
            # A ruleset that demands linear history and a queue that creates merge commits
            # is a configuration that cannot succeed. Refusing at load costs one error
            # once; allowing it costs a failed merge for every pull request queued.
            raise ValueError(
                "rulesets.merge_queue.merge_method MERGE conflicts with "
                "require_linear_history; use SQUASH or REBASE"
            )
        if self.allow_force_pushes:
            raise ValueError("rulesets: allow_force_pushes must not be true for a permanent branch")
        if self.allow_deletions:
            raise ValueError("rulesets: allow_deletions must not be true for a permanent branch")
        _unique_nonempty("rulesets.required_checks", self.required_checks)
        _unique_nonempty("rulesets.bypass_actors", self.bypass_actors)
        if not 0 <= self.required_approvals <= 6:
            raise ValueError("rulesets.required_approvals must be between 0 and 6")
        for actor in self.bypass_actors:
            actor_type, sep, actor_id = actor.partition(":")
            actor_type = actor_type.strip()
            if actor_type in IDLESS_BYPASS_ACTOR_TYPES:
                if sep:
                    raise ValueError(
                        f"rulesets.bypass_actors: {actor_type} takes no id, got {actor!r}"
                    )
                continue
            if not sep or not actor_type or not actor_id.strip().isdigit():
                raise ValueError(f"rulesets.bypass_actors entry is malformed: {actor!r}")


@dataclass(frozen=True)
class RulesetsConfig:
    """Whether and how declared repository rulesets are reconciled.

    Branch names are not configured here — `[rulesets.integration]` always targets
    `branches.integration` and `[rulesets.release]` always targets `branches.release`, so a
    repository that renamed either branch does not have to repeat the name.
    """

    enabled: bool = True
    integration: RulesetConfig = RulesetConfig(
        required_checks=DEFAULT_INTEGRATION_RULESET_CHECKS, required_approvals=0
    )
    release: RulesetConfig = RulesetConfig(
        required_checks=DEFAULT_RELEASE_RULESET_CHECKS,
        required_approvals=1,
        # The release branch is promoted by a rebase, not a squash, so its queue must be
        # told so here too -- inert while the queue is off, wrong the moment it is on.
        merge_queue=MergeQueueConfig(merge_method="REBASE"),
    )


@dataclass(frozen=True)
class RepositoryProfileConfig:
    enabled: bool = True
    description: str = ""
    topics: tuple[str, ...] = (
        "automation",
        "continuous-delivery",
        "documentation",
        "github-actions",
        "release-automation",
    )
    has_issues: bool = True
    has_projects: bool = True
    has_wiki: bool = False
    has_discussions: bool = True
    allow_squash_merge: bool = True
    allow_merge_commit: bool = False
    allow_rebase_merge: bool = True
    allow_auto_merge: bool = True
    delete_branch_on_merge: bool = False
    web_commit_signoff_required: bool = True
    vulnerability_alerts: bool = True
    automated_security_fixes: bool = True

    def __post_init__(self) -> None:
        if len(self.description) > 350:
            raise ValueError("repository_profile.description must be at most 350 characters")
        _unique_nonempty("repository_profile.topics", self.topics)
        if len(self.topics) > 20:
            raise ValueError("repository_profile.topics must contain at most 20 entries")
        if any(topic != topic.lower() or " " in topic for topic in self.topics):
            raise ValueError("repository_profile.topics must be lowercase and contain no spaces")


@dataclass(frozen=True)
class DocumentationConfig:
    enabled: bool = True
    ai_maintenance: bool = True
    model: str = "claude-sonnet-5"
    required_files: tuple[str, ...] = DEFAULT_DOCUMENTATION_FILES
    # The living roadmap (doctrine, vibey-gh#211): every project keeps an active roadmap
    # until its goal is reached AND its humans declare it done. The contract accepts
    # either docs/roadmap.md or ROADMAP.md. Opting out here silences only the
    # deterministic check — the exact-head review still judges roadmap liveness.
    require_roadmap: bool = True
    production_label: str = "Production"
    preview_label: str = "Preview"
    production_indexing: bool = True
    preview_indexing: bool = False
    generate_robots: bool = True
    generate_sitemap_index: bool = True
    generate_llms_txt: bool = True
    generate_llms_full_txt: bool = True
    generate_json_ld: bool = True
    generate_book: bool = False
    generate_paper: bool = False
    # Render LaTeX on the published site: `$...$`/`$$...$$` math (protected from Markdown by
    # pymdownx.arithmatex) and ```latex theorem-like environments, typeset by a pinned,
    # checksummed MathJax served from the site itself rather than a CDN. Off by default,
    # because it turns every `$...$` pair in prose into math.
    math: bool = False
    bottom_nav: bool = True
    author_name: str = "Adam Matthew Steinberger"
    author_url: str = "https://vibewithadam.matthewsteinberger.com"
    # Everything below describes what a repository requires of ITS OWN documentation.
    # A project that installs vibey-gh documents its product, not this tool, so each of
    # these is empty until the repository declares it.
    readme_sections: tuple[str, ...] = ()
    automation_doc: str = DEFAULT_AUTOMATION_DOC
    automation_doc_sections: tuple[str, ...] = ()
    automation_doc_min_words: int = 0
    mermaid_terms: tuple[str, ...] = ()
    mermaid_min_edges: int = 0
    require_provenance: bool = False
    provenance_files: tuple[str, ...] = ("README.md", "docs/index.md")
    google_analytics_id: str = ""
    # --- Search & LLM optimisation for the published site. Every field is optional and
    # generic; the defaults derive from the repository so an unconfigured site still ships
    # complete metadata. ---
    # One or two emoji become a zero-asset SVG favicon (plus apple-touch-icon); an http(s)
    # URL or site-relative path is used verbatim.
    favicon: str = "📘"
    # Social preview image. Empty means GitHub's generated OpenGraph card for the
    # repository, which always exists and stays current.
    og_image: str = ""
    twitter_site: str = ""
    twitter_creator: str = ""
    keywords: tuple[str, ...] = ()
    author: str = ""
    theme_color: str = "#080b14"
    locale: str = "en_US"
    # Google Search Console "HTML tag" verification token — the content value of the
    # meta tag, not the whole tag. Rendered into every published page and the channel
    # index, which is what makes it survive redeploys; an uploaded verification FILE is
    # wiped every time release-surfaces rebuilds the Pages root.
    google_site_verification: str = ""
    # What the published-site build installs. ProperDocs renders whatever the repository's
    # `properdocs.yml` declares, and a site that declares plugins or markdown extensions
    # cannot build without them — `properdocs` and its theme pull in none of that, so a
    # `--strict` build of a real documentation site fails on the first `mkdocs-gen-files`
    # or `pymdownx.*` it meets. Neither of these can be a default: the packages a site
    # needs follow from its own configuration, which is the adopter's.
    site_requirements: tuple[str, ...] = ()
    site_requirements_file: str = "docs/requirements.txt"
    # The directory holding the governance corpus -- the Constitution, the doctrines, the
    # commandments, the bill of rights and every standing subdoctrine -- relative to the
    # repository root. When set, every channel site publishes it as a Governance section,
    # which makes it chapters of the book, and every page, the channel chooser and llms.txt
    # link it (sub-doctrine 7.b, governance in plain sight). Copied from this single source
    # at build time, never committed twice. Empty publishes nothing.
    governance_source: str = ""
    # Where `vibey-gh corpus-index` writes the index, relative to the repository root; it is
    # shipped beside the site so the published law is integrity-checkable offline.
    corpus_index: str = "corpus-index.json"
    properdocs_version: str = "1.6.7"
    # Funding signage (#198): opt-in per currency, empty defaults — no default address
    # ever ships, because a payment default is one typo away from someone else's wallet.
    funding_bitcoin: str = ""
    funding_monero: str = ""
    funding_ethereum: str = ""
    funding_label: str = "Support this work"

    def __post_init__(self) -> None:
        for key in ("governance_source", "corpus_index"):
            value = getattr(self, key)
            if value and (
                value.startswith(("/", "~"))
                or ".." in PurePosixPath(value).parts
                or any(char.isspace() or char in "'\"$`\\" for char in value)
            ):
                raise ValueError(
                    f"documentation.{key} must be a repository-relative path without '..',"
                    f" whitespace or shell metacharacters: {value!r}"
                )
        if not self.corpus_index:
            raise ValueError("documentation.corpus_index must not be empty")
        _unique_nonempty("documentation.required_files", self.required_files)
        for name, values in (
            ("readme_sections", self.readme_sections),
            ("automation_doc_sections", self.automation_doc_sections),
            ("mermaid_terms", self.mermaid_terms),
            ("provenance_files", self.provenance_files),
        ):
            _unique_nonempty(f"documentation.{name}", values)
        for name, threshold in (
            ("automation_doc_min_words", self.automation_doc_min_words),
            ("mermaid_min_edges", self.mermaid_min_edges),
        ):
            if threshold < 0:
                raise ValueError(f"documentation.{name} must not be negative")
        # Payments are irreversible: a malformed address is a configuration ERROR,
        # never rendered. Shape only — it catches truncation, whitespace, and a
        # wrong-field paste; it cannot catch a valid-but-wrong address, which is why
        # the render is verbatim-from-config and every change is a reviewed,
        # fingerprinted commit.
        for name, value, pattern, shape in (
            (
                "funding_bitcoin",
                self.funding_bitcoin,
                r"bc1[ac-hj-np-z02-9]{11,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}",
                "bech32 'bc1...' or legacy Base58",
            ),
            (
                "funding_monero",
                self.funding_monero,
                r"[48][1-9A-HJ-NP-Za-km-z]{94}(?:[1-9A-HJ-NP-Za-km-z]{11})?",
                "a 95- or 106-character address starting with 4 or 8",
            ),
            (
                "funding_ethereum",
                self.funding_ethereum,
                r"0x[0-9a-fA-F]{40}",
                "'0x' followed by 40 hex characters",
            ),
        ):
            if value and not re.fullmatch(pattern, value):
                raise ValueError(
                    f"documentation.{name} does not look like a valid address ({shape}): {value}"
                )
        if any(
            Path(value).is_absolute() or ".." in Path(value).parts for value in self.required_files
        ):
            raise ValueError("documentation.required_files must be repository-relative paths")
        _unique_nonempty("documentation.site_requirements", self.site_requirements)
        # Each requirement is shell-quoted where it is rendered, so ordinary specifier
        # punctuation is safe. A newline is not: it would end the `pip install` line and
        # begin an arbitrary command inside the workflow, so it is refused here rather
        # than quoted away, where the error can still name the field.
        for requirement in self.site_requirements:
            if any(character in requirement for character in "\r\n\x00"):
                raise ValueError(
                    f"documentation.site_requirements entry spans lines: {requirement!r}"
                )
        if self.site_requirements_file:
            path = Path(self.site_requirements_file)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(
                    "documentation.site_requirements_file must be a repository-relative path"
                )
        if not self.properdocs_version.strip():
            raise ValueError("documentation.properdocs_version must not be empty")
        for name, value in (
            ("model", self.model),
            ("production_label", self.production_label),
            ("preview_label", self.preview_label),
            ("author_name", self.author_name),
            ("author_url", self.author_url),
        ):
            if not value.strip():
                raise ValueError(f"documentation.{name} must not be empty")
        # SEO fields land verbatim in rendered HTML and workflow YAML, so the cheap
        # injections are refused at load time rather than discovered on a published page.
        for name, value in (
            ("favicon", self.favicon),
            ("og_image", self.og_image),
            ("twitter_site", self.twitter_site),
            ("twitter_creator", self.twitter_creator),
            ("author", self.author),
            ("theme_color", self.theme_color),
            ("locale", self.locale),
        ):
            if any(ch in value for ch in '<>"\n'):
                raise ValueError(f"documentation.{name} must not contain HTML or quotes")
        for word in self.keywords:
            if any(ch in word for ch in '<>"\n,'):
                raise ValueError("documentation.keywords entries must be plain words")
        if self.theme_color and not re.match(r"^#[0-9a-fA-F]{3,8}$", self.theme_color):
            raise ValueError("documentation.theme_color must be a hex colour like #080b14")
        if self.google_site_verification and not re.match(
            r"^[A-Za-z0-9_-]{1,128}$", self.google_site_verification
        ):
            raise ValueError(
                "documentation.google_site_verification must be the bare token from the "
                "HTML-tag method (the content= value), not the whole tag"
            )
        if self.google_analytics_id and not GOOGLE_ANALYTICS_ID_PATTERN.match(
            self.google_analytics_id
        ):
            raise ValueError(
                "documentation.google_analytics_id must be empty (disabled) or a GA4 "
                f"measurement ID matching 'G-<alphanumeric>': {self.google_analytics_id!r}"
            )


@dataclass(frozen=True)
class MarketplaceConfig:
    """`[marketplace]`: the one Claude Code marketplace at the repository root.

    `/plugin marketplace add owner/repo` reads only `<repo>/.claude-plugin/marketplace.json`.
    A monorepo whose plugin marketplaces are workspace members declares them here, and
    `vibey-gh marketplace` renders the root manifest from theirs — every plugin, its source
    re-rooted to the repository — while `check` reports drift. `name` is the root's own:
    Claude Code registers one marketplace per name per user, and each member's package
    still ships its manifest under its own name. Empty `members` is every standalone
    adopter: nothing rendered, nothing checked.
    """

    name: str = ""
    members: tuple[str, ...] = ()
    # The manifest's human description. Empty derives one from the members.
    description: str = ""

    def __post_init__(self) -> None:
        _unique_nonempty("marketplace.members", self.members)
        for member in self.members:
            if (
                member.startswith(("/", "~"))
                or ".." in PurePosixPath(member).parts
                or any(char.isspace() or char in "'\"$`\\" for char in member)
            ):
                raise ValueError(
                    "marketplace.members entries must be repository-relative paths without"
                    f" '..', whitespace or shell metacharacters: {member!r}"
                )
        if self.members and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.name):
            raise ValueError(
                "marketplace.name must be kebab-case (it is what users type after '@')"
                f" when members are declared: {self.name!r}"
            )
        if self.name and not self.members:
            raise ValueError("marketplace.name is set but marketplace.members is empty")


@dataclass(frozen=True)
class EstimateConfig:
    """`[estimate]`: what `vibey-gh estimate` reads, and what each stage requires (#134).

    Every key has a default that reproduces the shipped behaviour, so an adopter writes
    only what differs (ADR-0018):

    - `offline` (true): the command never leaves this machine. It reads the machine's own
      memory, and the model runner only when the runner is on this machine; everything
      else stays `unknown` rather than being probed over the network.
    - `model` (empty): the local model the fit coordinates are measured against. Empty
      means `[pr_automation.fallback] model`, the model the local lane actually runs.
    - `stages` (empty): the pipeline, in order. Empty means the nine stages
      `vibey_gh.feasibility` declares, install through main-validation.
    - `requirements`: per stage, `"material.property" = minimum` on the 0..1 scale where
      1 is peak. A stage named here REPLACES that stage's default vector outright, so the
      file says exactly what the stage needs rather than a delta to be merged in one's
      head. Held as `(stage, ((coordinate, minimum), ...))` so the config stays frozen.
    - `report_first` (["agency"]): materials whose shortfalls lead the report. Agency is
      the common killer -- a run that cannot merge is infeasible however healthy the
      hardware -- so it is first by default.

    Only the SHAPE is checked here. Whether `agency` is a material and `develop` a stage
    is `vibey_gh.feasibility`'s vocabulary, and it is checked there, where the words are
    defined, rather than copied into a second list that could drift from them.
    """

    offline: bool = True
    model: str = ""
    stages: tuple[str, ...] = ()
    requirements: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] = ()
    report_first: tuple[str, ...] = ("agency",)
    # Continuous delivery forecast outputs.  They are repository-relative by default so
    # the append-only history and the human page can travel with the code that produced
    # them.  A repository may point them at an archival mount or disable the writer at the
    # CLI without changing the calculus.
    forecast_ledger: str = ".vibey/delivery-estimates.jsonl"
    forecast_report: str = "docs/estimate.md"
    forecast_billing_ledger: str = ".vibey/billing-ledger.jsonl"
    forecast_phi_floor: float = 0.1
    forecast_phi_epsilon: float = 0.01
    forecast_phi_exponent: float = 1.0
    forecast_phi_unknown_factor: float = 1.0
    forecast_size_weights: tuple[tuple[str, float], ...] = (
        ("xs", 0.5),
        ("s", 1.0),
        ("m", 3.0),
        ("l", 6.0),
        ("xl", 12.0),
    )

    def __post_init__(self) -> None:
        _unique_nonempty("estimate.stages", self.stages)
        _unique_nonempty("estimate.report_first", self.report_first)
        _unique_nonempty("estimate.requirements", tuple(stage for stage, _ in self.requirements))
        for stage, needs in self.requirements:
            for coordinate, minimum in needs:
                material, dot, prop = coordinate.partition(".")
                if not material or not dot or not prop or "." in prop:
                    raise ValueError(
                        f"estimate.requirements.{stage}: {coordinate!r} is not 'material.property'"
                    )
                if isinstance(minimum, bool) or not isinstance(minimum, int | float):
                    invalid_minimum = True
                else:
                    invalid_minimum = not math.isfinite(minimum) or not 0.0 <= minimum <= 1.0
                if invalid_minimum:
                    raise ValueError(
                        f"estimate.requirements.{stage}.{coordinate} must be a number from"
                        f" 0 to 1, where 1 is peak: {minimum!r}"
                    )
        if not self.forecast_ledger.strip() or not self.forecast_report.strip():
            raise ValueError("estimate.forecast ledger and report paths must be non-empty")
        if not self.forecast_billing_ledger.strip():
            raise ValueError("estimate.forecast billing ledger path must be non-empty")
        floor = _finite_forecast_number("estimate.forecast_phi_floor", self.forecast_phi_floor)
        epsilon = _finite_forecast_number(
            "estimate.forecast_phi_epsilon", self.forecast_phi_epsilon
        )
        exponent = _finite_forecast_number(
            "estimate.forecast_phi_exponent", self.forecast_phi_exponent
        )
        unknown_factor = _finite_forecast_number(
            "estimate.forecast_phi_unknown_factor", self.forecast_phi_unknown_factor
        )
        if not 0.0 <= floor < 1.0:
            raise ValueError("estimate.forecast_phi_floor must be at least 0 and below 1")
        if epsilon <= 0:
            raise ValueError("estimate.forecast_phi_epsilon must be positive")
        if exponent <= 0:
            raise ValueError("estimate.forecast_phi_exponent must be positive")
        if unknown_factor < 1.0:
            raise ValueError("estimate.forecast_phi_unknown_factor must be at least 1")
        labels = tuple(label for label, _ in self.forecast_size_weights)
        _unique_nonempty("estimate.forecast_size_weights", labels)
        if any(
            _finite_forecast_number("estimate.forecast_size_weights", value) <= 0
            for _, value in self.forecast_size_weights
        ):
            raise ValueError("estimate.forecast_size_weights values must be positive")

    @classmethod
    def from_table(cls, section: dict) -> EstimateConfig:
        """`[estimate]` as TOML hands it over, with each stage's table frozen."""
        raw = section.get("requirements", {})
        if not isinstance(raw, dict) or not all(isinstance(v, dict) for v in raw.values()):
            raise ValueError(
                "estimate.requirements must be a table of stage tables, e.g."
                ' [estimate.requirements.main] "agency.availability" = 1.0'
            )
        forecast = section.get("forecast", {})
        if not isinstance(forecast, dict):
            raise TypeError("estimate.forecast must be a table")
        weights = forecast.get(
            "size_weights",
            {"xs": 0.5, "s": 1.0, "m": 3.0, "l": 6.0, "xl": 12.0},
        )
        if not isinstance(weights, dict):
            raise TypeError("estimate.forecast.size_weights must be a table of label = weight")
        return cls(
            offline=bool(section.get("offline", True)),
            model=str(section.get("model", "")),
            stages=tuple(section.get("stages", ())),
            requirements=tuple((stage, tuple(needs.items())) for stage, needs in raw.items()),
            report_first=tuple(section.get("report_first", cls.report_first)),
            forecast_ledger=str(forecast.get("ledger", ".vibey/delivery-estimates.jsonl")),
            forecast_report=str(forecast.get("report", "docs/estimate.md")),
            forecast_billing_ledger=str(
                forecast.get("billing_ledger", ".vibey/billing-ledger.jsonl")
            ),
            forecast_phi_floor=_finite_forecast_number(
                "estimate.forecast.phi_floor", forecast.get("phi_floor", 0.1)
            ),
            forecast_phi_epsilon=_finite_forecast_number(
                "estimate.forecast.phi_epsilon", forecast.get("phi_epsilon", 0.01)
            ),
            forecast_phi_exponent=_finite_forecast_number(
                "estimate.forecast.phi_exponent", forecast.get("phi_exponent", 1.0)
            ),
            forecast_phi_unknown_factor=_finite_forecast_number(
                "estimate.forecast.unknown_factor", forecast.get("unknown_factor", 1.0)
            ),
            forecast_size_weights=tuple(
                (
                    str(label),
                    _finite_forecast_number(f"estimate.forecast.size_weights.{label}", value),
                )
                for label, value in weights.items()
            ),
        )


@dataclass(frozen=True)
class GhConfig:
    root: Path
    text: str = DEFAULT_TEXT
    superseded_texts: tuple[str, ...] = DEFAULT_SUPERSEDED_TEXTS
    trailer: str = DEFAULT_TRAILER
    sources: tuple[str, ...] = DEFAULT_SOURCES
    version_files: tuple[str, ...] = ()
    content_paths: tuple[str, ...] = ()
    code_paths: tuple[str, ...] = ("src/",)
    integration_branch: str = "develop"
    release_branch: str = "main"
    owner: str = ""
    trusted_authors: tuple[str, ...] = ()
    # Whether the merge train may bring a conflicting or behind branch forward itself,
    # by merging the integration branch into it locally, before reporting it as stuck.
    # A key rather than a constant (ADR-0018): the merge is an ordinary commit pushed to
    # somebody's topic branch, and a repository is entitled to say that no automation
    # writes to a branch it does not own. Off, the train reports the conflict exactly as
    # it did before and a person clears it.
    restack_conflicts: bool = True
    # Globs the merge train refuses to merge unattended: a pull request touching one is
    # reported as needing a human merge, and never reaches the `--admin` fallback that
    # would bypass a code-owner review (vibey_gh.protected_paths). Empty protects nothing,
    # which is how the train behaved before the key existed.
    protected_paths: tuple[str, ...] = ()
    ai: AiConfig = AiConfig()
    pr_automation: PrAutomationConfig = PrAutomationConfig()
    issue_automation: IssueAutomationConfig = IssueAutomationConfig()
    realign: RealignConfig = RealignConfig()
    branch_sync: BranchSyncConfig = BranchSyncConfig()
    conversation: ConversationConfig = ConversationConfig()
    github_release: GithubReleaseConfig = GithubReleaseConfig()
    yank: YankConfig = YankConfig()
    social_signals: SocialSignalsConfig = SocialSignalsConfig()
    tidy: TidyConfig = TidyConfig()
    platform: PlatformConfig = PlatformConfig()
    workflow_names: WorkflowNamesConfig = WorkflowNamesConfig()
    rulesets: RulesetsConfig = RulesetsConfig()
    repository_profile: RepositoryProfileConfig = RepositoryProfileConfig()
    documentation: DocumentationConfig = DocumentationConfig()
    marketplace: MarketplaceConfig = MarketplaceConfig()
    estimate: EstimateConfig = EstimateConfig()
    # Which bundled workflow templates this repository wants installed and kept current.
    # None means all of them, which is the right default for a repository adopting the
    # whole thing. A repository with its own richer workflows sets `workflows = []` and
    # keeps only the hooks and the CLI — otherwise `check` reports a permanent failure
    # for workflows it deliberately does not want.
    managed_workflows: tuple[str, ...] | None = None
    # Paths marked `merge=union` in `.gitattributes`. Appended to whatever the
    # repository already has there; an existing `.gitattributes` is never rewritten.
    union_merge_paths: tuple[str, ...] = DEFAULT_UNION_MERGE_PATHS
    # The distribution a rendered workflow or git hook installs this tooling from when
    # the repository has no copy of its own. `vibey_gh` is a PACKAGE inside the `vibey`
    # distribution and not a project of its own (ADR-0037), so the default names the
    # distribution that carries it. A key rather than a constant (sub-doctrine 12.c): a
    # fork, a mirror, or an internal index publishing this tooling under another name has
    # nowhere else to say so, and the alternative is an adopter editing rendered output
    # that `installed()` then reports as drift. One key, because the workflow fallback and
    # the pre-push hook's recovery advice must never name different packages -- they did,
    # and the hook kept telling people to install a distribution that no longer existed.
    fallback_package: str = "vibey"
    # Pin every rendered `pip install <fallback_package>` to the exact version that
    # rendered it. False keeps the historical floating install, so upgrading this
    # package changes nothing in an adopting repository until this is turned on.
    pin_version: bool = False
    # Where THIS repository keeps its own copy of vibey-gh, repository-root-relative.
    # "." is the standalone layout and the default, so nothing changes for an adopter.
    # A monorepo that vendors the tooling points this at the subtree.
    #
    # This is a declared path and deliberately NOT a search. Discovering "the first tracked
    # pyproject.toml declaring name = vibey-gh" reads a pull request's own files: a branch
    # that adds one anywhere in the tree would have the workflow `pip install -e` it, run
    # its build backend with the job's permissions, and hand the provenance gate a tool of
    # the contributor's choosing. A path from configuration cannot be moved by a PR.
    self_source: str = "."

    def __post_init__(self) -> None:
        """Cross-field rules neither dataclass can check on its own.

        A branch namespace only reads as safe next to the branches it must never
        collide with, and those live here rather than in `IssueAutomationConfig`.
        """
        _unique_nonempty("install.union_merge_paths", self.union_merge_paths)
        if any(
            Path(value).is_absolute() or ".." in Path(value).parts
            for value in self.union_merge_paths
        ):
            raise ValueError("install.union_merge_paths must be repository-relative paths")
        prefix = self.issue_automation.branch_prefix
        permanent = {self.integration_branch, self.release_branch, "develop", "main"}
        if prefix in permanent or any(prefix.startswith(f"{name}/") for name in permanent):
            raise ValueError(
                f"issue_automation.branch_prefix must not shadow a permanent branch: {prefix!r}"
            )
        patterns = self.protected_paths
        if not isinstance(patterns, tuple) or not all(isinstance(p, str) for p in patterns):
            # A bare TOML string would otherwise be split into one-character globs.
            raise ValueError("merge_train.protected_paths must be a list of strings")
        _unique_nonempty("merge_train.protected_paths", patterns)
        for pattern in patterns:
            if pattern.startswith("/"):
                # CODEOWNERS anchors a pattern with `/`; a pull request's listed paths never
                # start with one, so this glob would match nothing and protect nothing.
                raise ValueError(
                    "merge_train.protected_paths entries are repository-root relative,"
                    f" without a leading '/': {pattern!r}"
                )

    @property
    def header(self) -> str:
        """The fingerprint as it appears at the top of a source file."""
        return f"# {self.text}"

    @property
    def trailer_key(self) -> str:
        return self.trailer.split(":", 1)[0].strip() or DEFAULT_TRAILER_KEY


# PEP 508 names a distribution: letters, digits, and `-`/`_`/`.` between them.
_DISTRIBUTION_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")


def _fallback_package(raw: object) -> str:
    """A distribution name, validated because it is rendered into a shell command.

    This string lands inside `python -m pip install --quiet <value>` in a generated
    workflow and inside the pre-push hook's recovery advice. A PEP 508 name cannot carry
    a space, a quote, a semicolon or a slash, so requiring one keeps the rendered line a
    single argument by construction rather than by escaping it afterwards. An extras
    suffix is refused for the same reason `pin_version` appends its own `==`: this is the
    distribution, and the renderers decorate it.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("install.fallback_package must be a non-empty string")
    value = raw.strip()
    if not _DISTRIBUTION_RE.match(value):
        raise ValueError(f"install.fallback_package must be a PEP 508 distribution name: {value!r}")
    return value


def _self_source(raw: object) -> str:
    """A repository-relative directory, and nothing that can escape the tree.

    Absolute paths and `..` are rejected rather than normalised: this value decides what
    a workflow installs and a hook executes, so "probably fine after cleanup" is not a
    standard it gets held to.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("install.self_source must be a non-empty string")
    value = raw.strip()
    if value == ".":
        return value
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or value.startswith("~"):
        raise ValueError(
            f"install.self_source must be a relative path inside the repository: {value!r}"
        )
    return pure.as_posix()


def find_root(start: Path | None = None) -> Path:
    """The project root: the nearest directory that declares one, else where `.git` lives.

    A repository used to be a project, so `.git` was the only marker needed. A monorepo
    breaks that: `src/vibey_tools/gh` is a project -- its own distribution, its own version
    line, its own fingerprint globs -- inside a repository whose root belongs to something
    else. Walking straight past it to `.git` loaded the WRONG configuration, silently, and
    every path in it then resolved against the wrong tree.

    So a directory that carries its own `.vibey-gh.toml` stops the walk. That is already
    the thing which says "a vibey-gh project lives here", it needs no new marker file, and
    it leaves the standalone case exactly as it was -- there, the config sits at the git
    root and both rules give the same answer.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def _social_signals(raw: dict) -> SocialSignalsConfig:
    cfg = SocialSignalsConfig(
        enabled=bool(raw.get("enabled", False)),
        heading=str(raw.get("heading", "Real people, real words")),
        max_attestation_age_days=int(raw.get("max_attestation_age_days", 365)),
        entries=tuple(
            SocialSignalEntry(
                kind=str(e.get("kind", "")),
                agent=str(e.get("agent", "")),
                source=str(e.get("source", "")),
                human_attested=bool(e.get("human_attested", False)),
                attested_on=str(e.get("attested_on", "")),
                revoked=bool(e.get("revoked", False)),
                quote=str(e.get("quote", "")),
                role=str(e.get("role", "")),
                org=str(e.get("org", "")),
                date=str(e.get("date", "")),
                value=str(e.get("value", "")),
            )
            for e in raw.get("entries", [])
        ),
    )
    cfg.validate()
    return cfg


def _workflow_names(raw: dict) -> WorkflowNamesConfig:
    defaults = WorkflowNamesConfig()
    return WorkflowNamesConfig(
        **{
            f.name: str(raw.get(f.name, getattr(defaults, f.name)))
            for f in dataclasses.fields(WorkflowNamesConfig)
        }
    )


def load_config(root: Path | None = None, config: Path | None = None) -> GhConfig:
    """This repository's configuration, or an alternate one describing a second
    distribution that the same repository publishes.

    `config` changes the CONFIGURATION, never the root. A monorepo publishes several
    distributions from one tree, and one `.vibey-gh.toml` cannot express several version
    lines — but every path a config names (`[version] files`, `content_paths`,
    `code_paths`) is resolved against the repository root, and the version deriver asks
    git about them with `git show <rev>:<path>`, which only ever resolves from the top of
    the tree. So the alternate file lives beside the primary one and keeps writing
    repository-root-relative paths; pointing the root at a subdirectory instead would
    silently read the wrong pyproject.
    """
    root = find_root(root)
    path = config if config is not None else root / CONFIG_NAME
    if not path.is_absolute():
        path = root / path
    data: dict = {}
    if path.is_file():
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    elif config is not None:
        raise FileNotFoundError(f"no such configuration: {path}")

    fp = data.get("fingerprint", {})
    ver = data.get("version", {})
    br = data.get("branches", {})
    tr = data.get("merge_train", {})
    protected = tr.get("protected_paths", ())
    inst = data.get("install", {})
    auto = data.get("pr_automation", {})
    observability = auto.get("observability", {})
    fallback = auto.get("fallback", {})
    issues = data.get("issue_automation", {})
    realigning = data.get("realign", {})
    syncing = data.get("branch_sync", {})
    talking = data.get("conversation", {})
    release = data.get("github_release", {})
    yanking = data.get("yank", {})
    rulesets_data = data.get("rulesets", {})
    profile = data.get("repository_profile", {})
    documentation = data.get("documentation", {})
    marketplace = data.get("marketplace", {})
    platform = data.get("platform", {})
    automation = PrAutomationConfig(
        enabled=auto.get("enabled", True),
        scan_workflows=tuple(auto.get("scan_workflows", DEFAULT_SCAN_WORKFLOWS)),
        ignored_checks=tuple(auto.get("ignored_checks", DEFAULT_IGNORED_CHECKS)),
        max_repair_attempts=auto.get("max_repair_attempts", 3),
        model=auto.get("model", "claude-sonnet-5"),
        review_untrusted_authors=auto.get("review_untrusted_authors", True),
        repair_untrusted_authors=auto.get("repair_untrusted_authors", True),
        replace_fork_prs=auto.get("replace_fork_prs", True),
        retain_schedule_backstop=auto.get("retain_schedule_backstop", True),
        normalise_commit_subjects=auto.get("normalise_commit_subjects", True),
        plugin_marketplaces=tuple(auto.get("plugin_marketplaces", ())),
        plugins=tuple(auto.get("plugins", ())),
        observability=PrAutomationObservabilityConfig(
            sanitized_progress=observability.get("sanitized_progress", True),
            archive_execution_file=observability.get("archive_execution_file", True),
            allow_private_full_output=observability.get("allow_private_full_output", False),
        ),
        fallback=PrAutomationFallbackConfig(
            enabled=fallback.get("enabled", True),
            runner_label=fallback.get("runner_label", "vibey-local"),
            model=fallback.get("model", "qwen2.5-coder:14b"),
            base_url=fallback.get("base_url", "http://127.0.0.1:11434"),
            trusted_only=fallback.get("trusted_only", True),
            max_diff_chars=fallback.get("max_diff_chars", 60000),
            timeout_seconds=fallback.get("timeout_seconds", 600),
            heartbeat_ref=fallback.get("heartbeat_ref", "refs/vibey-gh/sovereign-heartbeat"),
            heartbeat_max_age_minutes=fallback.get("heartbeat_max_age_minutes", 15),
        ),
    )
    return GhConfig(
        root=root,
        text=fp.get("text", DEFAULT_TEXT),
        superseded_texts=tuple(fp.get("superseded_texts", DEFAULT_SUPERSEDED_TEXTS)),
        trailer=fp.get("trailer", DEFAULT_TRAILER),
        sources=tuple(fp.get("sources", DEFAULT_SOURCES)),
        version_files=tuple(ver.get("files", ())),
        content_paths=tuple(ver.get("content_paths", ())),
        code_paths=tuple(ver.get("code_paths", ("src/",))),
        managed_workflows=(tuple(inst["workflows"]) if "workflows" in inst else None),
        union_merge_paths=tuple(inst.get("union_merge_paths", DEFAULT_UNION_MERGE_PATHS)),
        fallback_package=_fallback_package(inst.get("fallback_package", "vibey")),
        pin_version=inst.get("pin_version", False),
        self_source=_self_source(inst.get("self_source", ".")),
        integration_branch=br.get("integration", "develop"),
        release_branch=br.get("release", "main"),
        owner=tr.get("owner", ""),
        trusted_authors=tuple(tr.get("trusted_authors", ())),
        restack_conflicts=bool(tr.get("restack_conflicts", True)),
        # A list becomes the tuple the field holds; anything else -- a bare string above
        # all, which `tuple()` would split into one-character globs -- reaches
        # `GhConfig.__post_init__` as it is, and is refused there.
        protected_paths=tuple(protected) if isinstance(protected, list) else protected,
        ai=AiConfig(
            base_url=data.get("ai", {}).get("base_url", ""),
            auth_secret=data.get("ai", {}).get("auth_secret", AiConfig.auth_secret),
        ),
        pr_automation=automation,
        issue_automation=IssueAutomationConfig(
            enabled=issues.get("enabled", True),
            model=issues.get("model", "claude-sonnet-5"),
            max_attempts=issues.get("max_attempts", 2),
            max_turns=issues.get("max_turns", 200),
            branch_prefix=issues.get("branch_prefix", "vibey-gh/issue"),
            base_branch=issues.get("base_branch", ""),
            solve_untrusted_authors=issues.get("solve_untrusted_authors", False),
            required_label=issues.get("required_label", SOLVE_LABEL),
            trigger_labels=tuple(issues.get("trigger_labels", ())),
            ignored_labels=tuple(issues.get("ignored_labels", DEFAULT_IGNORED_ISSUE_LABELS)),
            open_pull_request=issues.get("open_pull_request", True),
            draft_pull_request=issues.get("draft_pull_request", True),
            retain_schedule_backstop=issues.get("retain_schedule_backstop", True),
            fallback_enabled=issues.get("fallback_enabled", True),
        ),
        conversation=ConversationConfig(
            enabled=talking.get("enabled", True),
            trigger=talking.get("trigger", "@vibey-gh"),
            model=talking.get("model", "claude-sonnet-5"),
            max_interactions=talking.get("max_interactions", 10),
            respond_to_untrusted=talking.get("respond_to_untrusted", False),
            allow_changes=talking.get("allow_changes", True),
            ignore_actors=tuple(talking.get("ignore_actors", ConversationConfig().ignore_actors)),
        ),
        branch_sync=BranchSyncConfig(
            enabled=syncing.get("enabled", True),
            update_contributor_branches=syncing.get("update_contributor_branches", True),
            max_self_heals=syncing.get("max_self_heals", 2),
        ),
        realign=RealignConfig(
            reconcile_branches=realigning.get("reconcile_branches", True),
            automation_prefixes=tuple(
                realigning.get("automation_prefixes", RealignConfig().automation_prefixes)
            ),
            close_duplicates=realigning.get("close_duplicates", True),
            delete_duplicate_branches=realigning.get("delete_duplicate_branches", True),
            notify_contributor_branches=realigning.get("notify_contributor_branches", True),
        ),
        social_signals=_social_signals(data.get("social_signals", {})),
        estimate=EstimateConfig.from_table(data.get("estimate", {})),
        workflow_names=_workflow_names(data.get("workflow_names", {})),
        tidy=TidyConfig(
            enabled=data.get("tidy", {}).get("enabled", True),
            keep_branches=tuple(data.get("tidy", {}).get("keep_branches", ())),
            trust_forge_deletions=data.get("tidy", {}).get("trust_forge_deletions", True),
            fail_check=data.get("tidy", {}).get("fail_check", False),
        ),
        platform=PlatformConfig(
            kind=platform.get("kind", PlatformConfig.kind),
            host=platform.get("host", PlatformConfig.host),
            repository=platform.get("repository", PlatformConfig.repository),
            token_env=platform.get("token_env", PlatformConfig.token_env),
        ),
        yank=YankConfig(
            pypi=yanking.get("pypi", False),
            testpypi=yanking.get("testpypi", False),
            keep=yanking.get("keep", 0),
            governance_paths=tuple(
                yanking.get(
                    "governance_paths",
                    YankConfig.governance_paths,
                )
            ),
        ),
        github_release=GithubReleaseConfig(
            enabled=release.get("enabled", True),
            tag_prefix=release.get("tag_prefix", "v"),
            generate_notes=release.get("generate_notes", True),
            require_new_version=release.get("require_new_version", False),
        ),
        rulesets=RulesetsConfig(
            enabled=rulesets_data.get("enabled", True),
            integration=_ruleset(
                rulesets_data.get("integration", {}), DEFAULT_INTEGRATION_RULESET_CHECKS, 0
            ),
            release=_ruleset(
                rulesets_data.get("release", {}), DEFAULT_RELEASE_RULESET_CHECKS, 1, "REBASE"
            ),
        ),
        repository_profile=RepositoryProfileConfig(
            enabled=profile.get("enabled", True),
            description=profile.get("description", ""),
            topics=tuple(profile.get("topics", RepositoryProfileConfig().topics)),
            has_issues=profile.get("has_issues", True),
            has_projects=profile.get("has_projects", True),
            has_wiki=profile.get("has_wiki", False),
            has_discussions=profile.get("has_discussions", True),
            allow_squash_merge=profile.get("allow_squash_merge", True),
            allow_merge_commit=profile.get("allow_merge_commit", False),
            allow_rebase_merge=profile.get("allow_rebase_merge", True),
            allow_auto_merge=profile.get("allow_auto_merge", True),
            delete_branch_on_merge=profile.get("delete_branch_on_merge", False),
            web_commit_signoff_required=profile.get("web_commit_signoff_required", True),
            vulnerability_alerts=profile.get("vulnerability_alerts", True),
            automated_security_fixes=profile.get("automated_security_fixes", True),
        ),
        documentation=DocumentationConfig(
            enabled=documentation.get("enabled", True),
            ai_maintenance=documentation.get("ai_maintenance", True),
            model=documentation.get("model", "claude-sonnet-5"),
            required_files=tuple(documentation.get("required_files", DEFAULT_DOCUMENTATION_FILES)),
            require_roadmap=documentation.get("require_roadmap", True),
            production_label=documentation.get("production_label", "Production"),
            preview_label=documentation.get("preview_label", "Preview"),
            production_indexing=documentation.get("production_indexing", True),
            preview_indexing=documentation.get("preview_indexing", False),
            generate_robots=documentation.get("generate_robots", True),
            generate_sitemap_index=documentation.get("generate_sitemap_index", True),
            generate_llms_txt=documentation.get("generate_llms_txt", True),
            generate_llms_full_txt=documentation.get("generate_llms_full_txt", True),
            generate_json_ld=documentation.get("generate_json_ld", True),
            generate_book=documentation.get("generate_book", False),
            generate_paper=documentation.get("generate_paper", False),
            math=documentation.get("math", False),
            bottom_nav=documentation.get("bottom_nav", True),
            author_name=documentation.get("author_name", "Adam Matthew Steinberger"),
            author_url=documentation.get(
                "author_url", "https://vibewithadam.matthewsteinberger.com"
            ),
            readme_sections=tuple(documentation.get("readme_sections", ())),
            automation_doc=documentation.get("automation_doc", DEFAULT_AUTOMATION_DOC),
            # The former names are still read. They described a file this no longer points
            # at, but an adopter's config predates the rename and should not break on it.
            automation_doc_sections=tuple(
                documentation.get(
                    "automation_doc_sections", documentation.get("github_readme_sections", ())
                )
            ),
            automation_doc_min_words=documentation.get(
                "automation_doc_min_words", documentation.get("github_readme_min_words", 0)
            ),
            mermaid_terms=tuple(documentation.get("mermaid_terms", ())),
            mermaid_min_edges=documentation.get("mermaid_min_edges", 0),
            require_provenance=documentation.get("require_provenance", False),
            provenance_files=tuple(
                documentation.get("provenance_files", ("README.md", "docs/index.md"))
            ),
            google_analytics_id=documentation.get("google_analytics_id", ""),
            favicon=documentation.get("favicon", "📘"),
            og_image=documentation.get("og_image", ""),
            twitter_site=documentation.get("twitter_site", ""),
            twitter_creator=documentation.get("twitter_creator", ""),
            keywords=tuple(documentation.get("keywords", ())),
            author=documentation.get("author", ""),
            theme_color=documentation.get("theme_color", "#080b14"),
            locale=documentation.get("locale", "en_US"),
            google_site_verification=documentation.get("google_site_verification", ""),
            site_requirements=tuple(documentation.get("site_requirements", ())),
            governance_source=documentation.get("governance_source", ""),
            corpus_index=documentation.get("corpus_index", "corpus-index.json"),
            site_requirements_file=documentation.get(
                "site_requirements_file", DocumentationConfig.site_requirements_file
            ),
            properdocs_version=documentation.get(
                "properdocs_version", DocumentationConfig.properdocs_version
            ),
            funding_bitcoin=documentation.get("funding_bitcoin", ""),
            funding_monero=documentation.get("funding_monero", ""),
            funding_ethereum=documentation.get("funding_ethereum", ""),
            funding_label=documentation.get("funding_label", "Support this work"),
        ),
        marketplace=MarketplaceConfig(
            name=marketplace.get("name", ""),
            members=tuple(marketplace.get("members", ())),
            description=marketplace.get("description", ""),
        ),
    )


def normalise_actor(login: str) -> str:
    """`app/claude` and `claude[bot]` are the same account spelled two ways.

    `gh` reports a bot author with the `app/` prefix; the rest of GitHub writes `[bot]`.
    A literal allow-list matches whichever spelling it happens to contain and silently
    distrusts the other — which once caused an automation to quarantine its own pull
    request as an outside contribution.
    """
    login = login.removeprefix("app/")
    return login.removesuffix("[bot]")
