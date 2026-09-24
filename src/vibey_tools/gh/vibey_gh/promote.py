# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Promote the integration branch to the release branch.

This is the half of the flow that was missing. The merge train fills the integration
branch; something has to move it to the release branch, and doing that by hand is how a
release ends up on the wrong branch — or how an unbumped version publishes nothing.

Four things it gets right that a hand-written workflow usually does not:

**It compares by CONTENT, not by commit count.** The release branch is rebase-merged, so
its commits are rewritten copies with different SHAs; the integration branch will always
look "ahead" by some number of commits even when the two trees are identical. A diff
between them is the only honest test of whether there is anything to release.

**It derives the version before opening anything.** A PyPI upload with `skip-existing`
turns an unbumped promotion into a green run that publishes nothing, silently. `none` is a
legitimate answer — docs and CI changes reach no installed user — and the promotion still
proceeds; it just does not publish.

**It waits for the checks.** A pull request opened seconds ago has no results yet, and
merging blind is how a red build reaches the release branch.

**It keeps the pull request's words current.** A promotion that stays open across runs is
reused, and its title and body are rewritten from the current derivation every time — a
reviewer approving a release reads the version it will publish, not the one it was opened
at (#235). The version it was opened at is kept, and said, when the two differ.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field

from vibey_gh import github_state, versioning
from vibey_gh.config import GhConfig, load_config
from vibey_gh.interfaces.promotion_pull_request_interface import PromotionInterface

DEFAULT_METHOD = "rebase"
CHECK_TIMEOUT_SECONDS = 1800
# The promotion pull request's own record, carried at the top of its body the way the
# `vibey-gh-pr-automation` and `vibey-gh-issue-automation` state markers carry theirs.
PROMOTION_MARKER = "vibey-gh-promotion"
# A promotion opened before the marker existed never had its title changed, so the title
# is an honest record of the version it was opened at — when it has this exact shape.
_TITLE_VERSION = re.compile(r"^chore\(release\): (\S+)$")
_VERSION = re.compile(r"\S+")
# `gh pr edit` reads the pull request over GraphQL first, and a gh old enough to still ask
# for `projectCards` is refused outright now that Projects (classic) is sunset — the edit
# never happens, whatever the token may do. The REST endpoint asks for no such field.
_PROJECTS_CLASSIC = re.compile(r"projects \(classic\)|projectcards", re.IGNORECASE)


@dataclass
class Promotion:
    """What happened, in a shape a caller can print or assert on."""

    changed_files: int = 0
    version: str = ""
    bumped: str | None = None  # the derived version, or None when nothing was due
    reason: str = ""  # what the derivation said, verbatim
    released: str | None = None  # the release branch's version, or None when unreadable
    previous: str | None = None  # the version a reused pull request was opened at, if known
    pull_request: int | None = None
    merged: bool = False
    bypassed: bool = False
    notes: list[str] = field(default_factory=list)

    def say(self, note: str) -> None:
        self.notes.append(note)


def _git(cfg: GhConfig, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cfg.root, capture_output=True, text=True, check=False)


def _gh(cfg: GhConfig, *args: str) -> tuple[bool, str]:
    r = subprocess.run(["gh", *args], cwd=cfg.root, capture_output=True, text=True, check=False)
    return r.returncode == 0, (r.stdout or "").strip()


def open_pull_request(cfg: GhConfig) -> int | None:
    """The open promotion pull request, if there already is one."""
    ok, out = _gh(
        cfg,
        "pr",
        "list",
        "--base",
        cfg.release_branch,
        "--head",
        cfg.integration_branch,
        "--state",
        "open",
        "--json",
        "number",
        "--jq",
        '.[0].number // ""',
    )
    return int(out) if ok and out.isdigit() else None


def create_pull_request(cfg: GhConfig, body: str) -> int | None:
    """Open the promotion pull request, titled by the one spelling an edit also uses.

    Module-level beside `open_pull_request`, `checks_pass` and `merge` (ADR-0016's method
    of last resort, and the reason): the four are the `gh` verbs `promote` sequences, and
    moving one of them alone into `PromotionPullRequest` would split a set that converges
    together. The title is not spelled here; it is asked of the class that also edits it.
    """
    ok, out = _gh(
        cfg,
        "pr",
        "create",
        "--base",
        cfg.release_branch,
        "--head",
        cfg.integration_branch,
        "--title",
        PromotionPullRequest(cfg).title(versioning.read_version(cfg)),
        "--body",
        body,
    )
    if not ok:
        return None
    digits = "".join(c for c in out.rsplit("/", 1)[-1] if c.isdigit())
    return int(digits) if digits else None


def checks_pass(cfg: GhConfig, number: int) -> bool:
    """Block until the checks settle. `--watch` exits non-zero if any of them fail."""
    ok, _ = _gh(cfg, "pr", "checks", str(number), "--watch", "--interval", "30")
    return ok


def merge(
    cfg: GhConfig, number: int, method: str = DEFAULT_METHOD, admin_fallback: bool = False
) -> tuple[bool, bool, str]:
    """(merged, bypassed, error). A plain merge, and by default nothing else: a ruleset's
    approving-review requirement refuses it, and that refusal is the gate working. Only
    with `admin_fallback` -- `vibey-gh promote --wait --admin-fallback`, a person's choice
    for one run and never a configuration default (vibey ADR-0053, sub-doctrine 12.d) --
    is it retried with `--admin`. `error` is GitHub's own reason, "" on success.

    Module-level beside `promote`, its one caller: callers and tests substitute it by name.
    """
    base = ["gh", "pr", "merge", str(number), f"--{method}"]
    attempts = [base, base + ["--admin"]] if admin_fallback else [base]
    detail = ""
    for bypassed, argv in enumerate(attempts):
        run = subprocess.run(argv, cwd=cfg.root, capture_output=True, text=True, check=False)
        if run.returncode == 0:
            return True, bool(bypassed), ""
        detail = (run.stderr or run.stdout or "").strip() or detail
    return False, admin_fallback, " ".join((detail or "GitHub refused the merge").split())[:300]


def promote(
    cfg: GhConfig | None = None,
    *,
    dry_run: bool = False,
    method: str = DEFAULT_METHOD,
    wait: bool = False,
    admin_fallback: bool = False,
) -> Promotion:
    """Promote the integration branch, opening a pull request or refreshing the open one.

    Module-level under ADR-0016 because it is this module's published entry point: `cli`
    dispatches to it by name and callers substitute it by name.
    """
    cfg = cfg or load_config()
    result = Promotion()
    integration, release = cfg.integration_branch, cfg.release_branch

    _git(cfg, "fetch", "--quiet", "origin", integration, release)
    if _git(cfg, "diff", "--quiet", f"origin/{release}", f"origin/{integration}").returncode == 0:
        result.say(f"{integration} and {release} have identical trees; nothing to promote")
        return result

    changed = _git(cfg, "diff", "--name-only", f"origin/{release}", f"origin/{integration}")
    result.changed_files = len([line for line in changed.stdout.splitlines() if line])
    # What the release branch already carries — the version an upload would find on the
    # index. The pull request's body says whether merging publishes from THIS comparison,
    # not from a caveat printed on every promotion whatever it proposes.
    result.released = versioning.read_version_at(cfg, f"origin/{release}")

    # Derive the version on the integration branch, where the release will be cut from.
    _git(cfg, "checkout", "--quiet", "-B", integration, f"origin/{integration}")
    new, why = versioning.decide(cfg, f"origin/{release}")
    result.bumped, result.reason = new, why
    result.say(f"version: {why}")

    if new and not dry_run:
        written = versioning.apply_version(cfg, new)
        _git(cfg, "add", *written)
        _git(
            cfg,
            "commit",
            "--quiet",
            "-m",
            # A Conventional Commit, because this subject does not stay on the release
            # branch: any topic branch that later merges the integration branch in pulls it
            # into its own commit range, where the provenance gate reads it like any other
            # commit and rejects it. `Release 1.23.0` blocked a pull request that way, and
            # the repair could not fix it by editing files because the problem was history.
            f"chore(release): {new}",
            "-m",
            "Version derived from what changed since the last release, so the "
            "promotion actually publishes.",
            "-m",
            cfg.trailer,
        )
        push = _git(cfg, "push", "--quiet", "origin", integration)
        if push.returncode != 0:
            # Not a warning. An unpushed bump means the promotion publishes nothing. The
            # stderr goes into the message because git names the actual refusal — hiding
            # it once turned a token-scope problem into an afternoon of guessing.
            detail = " ".join(((push.stderr or push.stdout) or "").split())[:300]
            raise RuntimeError(
                f"could not push the version bump to {integration}; promoting it would "
                "publish nothing" + (f" — {detail}" if detail else "")
            )
        result.say(f"bumped to {new} and pushed to {integration}")
        _git(cfg, "fetch", "--quiet", "origin", integration)
    elif new:
        result.say(f"dry run — would bump to {new}")
        _git(cfg, "checkout", "--quiet", "--", *cfg.version_files)

    result.version = versioning.read_version(cfg)

    if dry_run:
        result.say("dry run — stopping before opening the pull request")
        return result

    pull_request = PromotionPullRequest(cfg)
    number = open_pull_request(cfg)
    if number is None:
        number = create_pull_request(cfg, pull_request.body(result))
        if number is None:
            raise RuntimeError("could not open the promotion pull request")
        result.say(f"opened #{number}")
    else:
        # Reused, so its words were written by an earlier run about an earlier state.
        pull_request.refresh(number, result)
    result.pull_request = number

    if not wait:
        result.say(f"#{number} will be merged by the event-driven PR automation gate")
        return result

    if not checks_pass(cfg, number):
        result.say(f"checks did not pass on #{number}; leaving it open")
        return result

    merged, bypassed, error = merge(cfg, number, method, admin_fallback)
    result.merged, result.bypassed = merged, bypassed
    if merged:
        result.say(
            f"#{number} {method}-merged into {release}"
            + (" (review requirement bypassed)" if bypassed else "")
        )
    else:
        # Open and green, waiting on a person: the refusal is the gate, not a fault.
        result.say(f"#{number} needs a human merge: {error}")
    return result


class PromotionPullRequest:
    """Implements `PromotionPullRequestInterface` with `gh`, against the repository at
    `cfg.root` — the same directory every other `gh` call in this module resolves from."""

    def __init__(self, cfg: GhConfig) -> None:
        self._cfg = cfg

    def title(self, version: str) -> str:
        return f"chore(release): {version}"

    def body(self, result: PromotionInterface) -> str:
        release = self._cfg.release_branch
        # The version the pull request was first opened at is carried forward, not
        # overwritten: it is how long the promotion has been open, and a record holding
        # only the current version would forget it the run after it was first said.
        opened = result.previous or result.version
        # "Written", not "opened": a promotion a human opened is rewritten all the same.
        intro = (
            "Written by `vibey-gh promote`, and rewritten from the current derivation every "
            "time it runs while this pull request is open."
        )
        differ = f"{result.changed_files} file(s) differ from `{release}`."
        paragraphs = [intro, f"{differ} {self._publishes(result)}"]
        if opened != result.version:
            derivation = f" (version derivation: {result.reason})" if result.reason else ""
            paragraphs.append(f"Opened as `{opened}`; now `{result.version}`{derivation}.")
        paragraphs.append(
            f"Merged with `--{DEFAULT_METHOD}`, which is the only method consistent with a "
            "linear-history rule."
        )
        return github_state.render_body(
            PROMOTION_MARKER,
            {"opened": opened, "version": result.version},
            f"Promote `{self._cfg.integration_branch}` to `{release}`",
            "\n\n".join(paragraphs),
        )

    def _publishes(self, result: PromotionInterface) -> str:
        release = self._cfg.release_branch
        if result.released is None:
            # Unreadable is not the same as unbumped: say what is known, and no more.
            return (
                f"The package version is `{result.version}`; the version on `{release}` "
                "could not be read, so whether merging publishes it depends on whether "
                "the index already holds it."
            )
        if result.version == result.released:
            return (
                f"The package version is `{result.version}`, the same as `{release}`'s, "
                "and an upload skips a version the index already holds — so merging this "
                "promotion publishes nothing."
            )
        return f"Merging publishes `{result.version}` (`{release}` is at `{result.released}`)."

    def recorded_version(self, title: str, body: str) -> str | None:
        pattern = github_state.marker_pattern(PROMOTION_MARKER)
        payload = github_state.parse_payload([body], pattern) or {}
        for key in ("opened", "version"):
            value = payload.get(key)
            if isinstance(value, str) and _VERSION.fullmatch(value):
                return value
        match = _TITLE_VERSION.match(title.strip())
        return match.group(1) if match else None

    def read(self, number: int) -> tuple[str, str]:
        # Its own call, never a wider `pr list`: the list answers "is there one", and
        # folding the words into it would make every caller of that question pay for them.
        run = self._gh("pr", "view", str(number), "--json", "title,body")
        if run.returncode:
            raise RuntimeError(self._detail(run, "gh pr view"))
        try:
            data = json.loads(run.stdout or "null")
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            return str(data.get("title") or ""), str(data.get("body") or "")
        raise RuntimeError(f"gh pr view {number} did not return a title and body")

    def write(self, number: int, title: str, body: str) -> None:
        edit = self._gh("pr", "edit", str(number), "--title", title, "--body", body)
        if edit.returncode == 0:
            return
        detail = self._detail(edit, "gh pr edit")
        if not _PROJECTS_CLASSIC.search(detail):
            raise RuntimeError(detail)
        # `{owner}` and `{repo}` are gh's own placeholders, filled from the repository at
        # `cfg.root` exactly as `gh pr edit` would have resolved it. `-f` sends the text
        # as a raw string, so a body that happens to start with `@` is not read as a file.
        patch = self._gh(
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{number}",
            "--method",
            "PATCH",
            "-f",
            f"title={title}",
            "-f",
            f"body={body}",
        )
        if patch.returncode:
            raise RuntimeError(
                f"{detail}; the REST fallback failed too — {self._detail(patch, 'gh api')}"
            )

    def refresh(self, number: int, result: PromotionInterface) -> None:
        current: tuple[str, str] | None
        try:
            current = self.read(number)
        except RuntimeError as exc:
            # Refreshed anyway: a stale title is the defect, and not knowing what the pull
            # request says now is no reason to leave it saying it.
            current = None
            result.say(
                f"could not read #{number}'s title and body, so the version it was opened "
                f"at is unknown — {exc}"
            )
        if current is not None:
            result.previous = self.recorded_version(*current)
        title, body = self.title(result.version), self.body(result)
        if current is not None and self._same(current, (title, body)):
            result.say(f"reusing #{number}; its title and body are already current")
            return
        try:
            self.write(number, title, body)
        except RuntimeError as exc:
            # A note, not a crash: the pull request is still the promotion, and the merge
            # gate still judges its exact head. Its words are what could not be fixed.
            result.say(f"reusing #{number}; could not refresh its title/body — {exc}")
            return
        moved = ""
        if result.previous is not None and result.previous != result.version:
            moved = f" (opened as {result.previous}, now {result.version})"
        result.say(f"reusing #{number}; refreshed its title and body{moved}")

    def _gh(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["gh", *args], cwd=self._cfg.root, capture_output=True, text=True, check=False
        )

    @staticmethod
    def _detail(run: subprocess.CompletedProcess, what: str) -> str:
        # gh names the actual refusal on stderr; hiding it turns a token-scope problem
        # into guessing, which is the lesson the version-bump push above already records.
        text = " ".join(((run.stderr or run.stdout) or "").split())[:300]
        return text or f"{what} exited {run.returncode}"

    @staticmethod
    def _same(current: tuple[str, str], wanted: tuple[str, str]) -> bool:
        # The forge may hand a body back with CRLF line ends or without its final newline;
        # neither is a difference worth an edit.
        def norm(text: str) -> str:
            return text.replace("\r\n", "\n").strip()

        return all(norm(a) == norm(b) for a, b in zip(current, wanted, strict=True))
