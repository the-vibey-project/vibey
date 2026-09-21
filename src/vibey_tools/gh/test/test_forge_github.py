# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The GitHub forge adapter, and the proof that moving the clean-repo survey onto it changed
nothing GitHub or an adopter can see.

The proof is before/after, the technique the `gh` transport's own tests use. `Before` holds
the survey as it stood before this change, verbatim, with the private `gh` runners it
carried. Each comparison runs the old survey and the new one against the same clone and the
same `FakeGh` on PATH, and requires the same report, the same argv lists, the same working
directory and the same bytes in `calls.txt`. A scenario that never reached `gh` would compare
equal and prove nothing, so each one also pins what it expected `gh` to have seen.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import tidy
from vibey_gh.config import GhConfig, PlatformConfig, TidyConfig
from vibey_gh.forge import ForgeRelease
from vibey_gh.forge_github import GH_DEFAULT_HOST, GitHubForge
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface

PR_HEADS = ["pr", "list", "--json", "headRefName", "--limit", "200"]
RELEASES = ["release", "list", "--json", "tagName,name,isDraft", "--limit", "100"]


def key(argv: list[str]) -> str:
    """The spelling of one scripted answer. Module-level (vibey ADR-0016) because it is the
    one-word form every scenario table below repeats, and a method would only lengthen it."""
    return " ".join(argv)


class Before:
    """The clean-repo survey as it stood before the forge adapter, gathered into one class
    and otherwise verbatim: its git helpers, its two private `gh` runners, and the survey
    that called them. Kept as a copy rather than imported, so this proof still says what it
    says after `tidy` moves on."""

    @staticmethod
    def _git(root: Path, *args: str) -> str:
        run = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return run.stdout if run.returncode == 0 else ""

    @staticmethod
    def _gh_json(root: Path, *args: str) -> tuple[list | dict, str]:
        label = " ".join(("gh", *args[:2]))
        try:
            run = subprocess.run(
                ["gh", *args], cwd=root, capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            return [], "the GitHub CLI (`gh`) is not installed"
        if run.returncode != 0:
            detail = (run.stderr or run.stdout).strip().splitlines()
            return [], f"`{label}` failed: {detail[-1] if detail else 'no output'}"
        try:
            value = json.loads(run.stdout)
        except json.JSONDecodeError:
            return [], f"`{label}` returned output that is not JSON"
        if isinstance(value, (list, dict)):
            return value, ""
        return [], f"`{label}` returned JSON that is neither a list nor an object"

    @classmethod
    def _gh_list(cls, root: Path, *args: str) -> tuple[list, str]:
        value, problem = cls._gh_json(root, *args)
        if problem:
            return [], problem
        if not isinstance(value, list):
            label = " ".join(("gh", *args[:2]))
            return [], f"`{label}` returned a JSON object where a listing was expected"
        return value, ""

    @staticmethod
    def _kept(cfg: GhConfig) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys((cfg.integration_branch, cfg.release_branch, *cfg.tidy.keep_branches))
        )

    @classmethod
    def _open_pr_heads(cls, root: Path) -> tuple[set[str], str]:
        prs, problem = cls._gh_list(root, "pr", "list", "--json", "headRefName", "--limit", "200")
        return {p.get("headRefName", "") for p in prs if isinstance(p, dict)}, problem

    @staticmethod
    def _contained(root: Path, tip: str, kept_remote: list[str]) -> bool:
        for keeper in kept_remote:
            run = subprocess.run(
                ["git", "merge-base", "--is-ancestor", tip, keeper],
                cwd=root,
                capture_output=True,
                check=False,
            )
            if run.returncode == 0:
                return True
        return False

    @classmethod
    def survey(cls, cfg: GhConfig, local: bool = True, refresh: bool = True) -> tidy.TidyReport:
        _git, _contained = cls._git, cls._contained
        root = cfg.root
        kept = cls._kept(cfg)
        problems: list[str] = []
        if refresh:
            _git(root, "fetch", "--prune", "--quiet", "origin")
        kept_remote = [f"origin/{b}" for b in kept if _git(root, "rev-parse", f"origin/{b}")]
        if not kept_remote:
            return tidy.TidyReport(
                problems=("no kept branch resolves on origin; refusing to judge",)
            )
        pr_heads, forge_problem = cls._open_pr_heads(root)
        judged = not forge_problem
        if forge_problem:
            problems.append(f"{forge_problem}; merged branches were not judged")

        remote_merged: list[str] = []
        if judged:
            for line in _git(root, "branch", "-r", "--format=%(refname:short)").splitlines():
                name = line.strip()
                short = name.removeprefix("origin/")
                if not name.startswith("origin/") or "HEAD" in short:
                    continue
                if short in kept or short in pr_heads:
                    continue
                tip = _git(root, "rev-parse", name).strip()
                if tip and _contained(root, tip, kept_remote):
                    remote_merged.append(short)

        releases, release_problem = cls._gh_list(
            root, "release", "list", "--json", "tagName,name,isDraft", "--limit", "100"
        )
        if release_problem:
            problems.append(f"{release_problem}; draft releases were not judged")
        drafts = [
            str(r.get("tagName") or r.get("name") or "")
            for r in releases
            if isinstance(r, dict) and r.get("isDraft")
        ]

        orphan_tags: list[str] = []
        for tag in _git(root, "tag", "--list").splitlines():
            tag = tag.strip()
            if not tag:
                continue
            tip = _git(root, "rev-parse", f"{tag}^{{commit}}").strip()
            if tip and not _contained(root, tip, kept_remote):
                orphan_tags.append(tag)

        local_merged: list[str] = []
        local_gone: list[str] = []
        prunable: list[str] = []
        stashes = 0
        untracked = 0
        if local:
            current = _git(root, "branch", "--show-current").strip()
            fmt = "%(refname:short)\t%(upstream:track)"
            for line in _git(root, "branch", "--format=" + fmt).splitlines():
                name, _, track = line.partition("\t")
                name = name.strip()
                if not name or name == current or name in kept:
                    continue
                if "[gone]" in track:
                    local_gone.append(name)
                    continue
                if not judged or name in pr_heads:
                    continue
                tip = _git(root, "rev-parse", name).strip()
                if tip and _contained(root, tip, kept_remote):
                    local_merged.append(name)
            main = str(Path(root).resolve())
            for block in _git(root, "worktree", "list", "--porcelain").strip().split("\n\n"):
                lines = block.splitlines()
                path = next(
                    (
                        ln.removeprefix("worktree ").strip()
                        for ln in lines
                        if ln.startswith("worktree ")
                    ),
                    "",
                )
                if not path or path == main:
                    continue
                if any(ln.startswith("prunable") for ln in lines):
                    prunable.append(path)
            stashes = len(_git(root, "stash", "list").splitlines())
            untracked = len(
                _git(root, "status", "--porcelain", "--untracked-files=normal").splitlines()
            )

        return tidy.TidyReport(
            remote_merged=tuple(remote_merged),
            local_merged=tuple(local_merged),
            local_gone=tuple(local_gone),
            prunable_worktrees=tuple(prunable),
            draft_releases=tuple(drafts),
            orphan_tags=tuple(orphan_tags),
            stashes=stashes,
            untracked=untracked,
            problems=tuple(problems),
        )


class Witness:
    """Runs one action against the fake and keeps everything an observer could see of it."""

    def __init__(self, fake: Any) -> None:
        self.fake = fake

    def observe(self, action: Callable[[], Any]) -> dict[str, Any]:
        seen = {
            "outcome": action(),
            "invocations": self.fake.invocations(),
            "calls": self.fake.calls(),
        }
        self.fake.forget()
        return seen

    def compare(self, before: Callable[[], Any], after: Callable[[], Any]) -> dict[str, Any]:
        """Both sides' observations, required equal; returns the shared one to pin."""
        old, new = self.observe(before), self.observe(after)
        assert new == old
        return new


# Module-level for the reason every fixture is (vibey ADR-0016): pytest resolves fixtures by
# name at module scope.
def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _github_config(root: Path, **kwargs) -> GhConfig:
    """A config bound to GitHub, the declared-only kind these tests drive."""
    return GhConfig(root=root, platform=PlatformConfig(kind="github"), **kwargs)


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A clone whose survey the forge's answers visibly change: two branches whose work has
    landed, one of them an open pull request's head (so it is clutter only if the forge does
    not say it is live), a gone-upstream local, and an orphan tag."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    (work / "a.txt").write_text("a\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "base")
    _git(work, "branch", "-M", "develop")
    _git(work, "push", "-qu", "origin", "develop")
    _git(work, "push", "-q", "origin", "develop:main")
    for landed in ("merged-work", "open-head"):
        _git(work, "branch", landed, "develop")
        _git(work, "push", "-qu", "origin", landed)
    _git(work, "checkout", "-qb", "gone-work")
    (work / "b.txt").write_text("b\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "squashed elsewhere")
    _git(work, "push", "-qu", "origin", "gone-work")
    _git(work, "push", "-q", "origin", "--delete", "gone-work")
    _git(work, "tag", "orphaned-tag")
    _git(work, "checkout", "-q", "develop")
    return work.resolve()


@pytest.fixture
def witness(fake_gh) -> Witness:
    return Witness(fake_gh)


LISTED = json.dumps(
    [
        {"tagName": "v9.9.9-draft", "name": "Next", "isDraft": True},
        {"tagName": "v1.0.0", "name": "One", "isDraft": False},
        {"tagName": None, "name": "Untitled draft", "isDraft": True},
        {"tagName": "", "name": None, "isDraft": 1},
        {"tagName": 7, "isDraft": True},
        {"name": "no draft flag"},
        "not a release",
    ]
)
HEADS = json.dumps(
    [
        {"headRefName": "open-head"},
        {"number": 3},
        {"headRefName": None},
        "not a pull request",
    ]
)

# What the survey appends to a problem, per class it could not judge.
BRANCHES = "; merged branches were not judged"
DRAFTS = "; draft releases were not judged"
REFUSED = "gh: To use GitHub CLI in a GitHub Actions workflow, set GH_TOKEN"
ENVELOPE = "returned a JSON object where a listing was expected"

# Each scenario: the two scripted answers, then what the survey must make of them.
SCENARIOS = {
    "both answer": (
        {"out": HEADS},
        {"out": LISTED},
        {
            "remote_merged": ("merged-work",),
            "draft_releases": ("v9.9.9-draft", "Untitled draft", "", "7"),
            "problems": (),
        },
    ),
    "nothing open, nothing released": (
        {"out": "[]"},
        {"out": "[]\n"},
        {"remote_merged": ("merged-work", "open-head"), "draft_releases": (), "problems": ()},
    ),
    "gh refused": (
        {"err": f"{REFUSED}\n", "code": 4},
        {"out": "partial\n", "code": 1},
        {
            "remote_merged": (),
            "draft_releases": (),
            "problems": (
                f"`gh pr list` failed: {REFUSED}{BRANCHES}",
                f"`gh release list` failed: partial{DRAFTS}",
            ),
        },
    ),
    "an error envelope where a listing belongs": (
        {"out": '{"message": "Bad credentials", "status": "401"}'},
        {"out": '{"message": "Bad credentials"}'},
        {
            "remote_merged": (),
            "draft_releases": (),
            "problems": (
                f"`gh pr list` {ENVELOPE}{BRANCHES}",
                f"`gh release list` {ENVELOPE}{DRAFTS}",
            ),
        },
    ),
    "output that is not a listing at all": (
        {"out": "<html>"},
        {"out": "3"},
        {
            "remote_merged": (),
            "draft_releases": (),
            "problems": (
                f"`gh pr list` returned output that is not JSON{BRANCHES}",
                f"`gh release list` returned JSON that is neither a list nor an object{DRAFTS}",
            ),
        },
    ),
    "silence": (
        {"code": 2},
        {"out": ""},
        {
            "remote_merged": (),
            "draft_releases": (),
            "problems": (
                f"`gh pr list` failed: no output{BRANCHES}",
                f"`gh release list` returned output that is not JSON{DRAFTS}",
            ),
        },
    ),
}


# ------------------------------------------------ before/after: the survey onto the adapter


@pytest.mark.parametrize(("local", "refresh"), [(True, False), (False, False), (True, True)])
@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_the_survey_asks_gh_the_same_questions_and_reports_the_same(
    witness, clone, scenario, local, refresh
):
    heads, listed, expected = SCENARIOS[scenario]
    witness.fake.script({key(PR_HEADS): heads, key(RELEASES): listed})
    cfg = _github_config(clone)
    seen = witness.compare(
        lambda: Before.survey(cfg, local=local, refresh=refresh),
        lambda: tidy.survey(cfg, local=local, refresh=refresh),
    )
    assert seen["invocations"] == [
        {"argv": PR_HEADS, "cwd": str(clone), "stdin": None},
        {"argv": RELEASES, "cwd": str(clone), "stdin": None},
    ]
    assert seen["calls"] == [key(PR_HEADS), key(RELEASES)]
    report = seen["outcome"]
    assert report.remote_merged == expected["remote_merged"]
    assert report.draft_releases == expected["draft_releases"]
    assert report.problems == expected["problems"]
    assert report.orphan_tags == ("orphaned-tag",)
    assert report.local_gone == (("gone-work",) if local else ())


def test_the_survey_says_the_same_thing_when_there_is_no_gh_at_all(witness, clone, monkeypatch):
    """`gh` absent entirely: both sides must say so, and must not have reached the fake."""
    outer = subprocess.run

    def without_gh(cmd, **kw):
        if cmd and cmd[0] == "gh":
            raise FileNotFoundError(2, "No such file or directory: 'gh'")
        return outer(cmd, **kw)

    monkeypatch.setattr(subprocess, "run", without_gh)
    cfg = _github_config(clone)
    seen = witness.compare(lambda: Before.survey(cfg), lambda: tidy.survey(cfg))
    assert seen["invocations"] == [] and seen["calls"] == []
    assert seen["outcome"].problems == (
        "the GitHub CLI (`gh`) is not installed; merged branches were not judged",
        "the GitHub CLI (`gh`) is not installed; draft releases were not judged",
    )


def test_the_survey_refuses_to_judge_before_it_asks_the_forge_anything(witness, tmp_path):
    """No kept branch on origin: the early refusal comes before either forge call, before
    and after, so the adapter is not even chosen."""
    solo = tmp_path / "solo"
    subprocess.run(["git", "init", "-q", str(solo)], check=True)
    cfg = _github_config(solo)
    seen = witness.compare(lambda: Before.survey(cfg), lambda: tidy.survey(cfg))
    assert seen["invocations"] == []
    assert seen["outcome"].problems == ("no kept branch resolves on origin; refusing to judge",)


def test_the_survey_keeps_an_extra_kept_branch_the_same_way(witness, clone):
    witness.fake.script({key(PR_HEADS): {"out": "[]"}, key(RELEASES): {"out": "[]"}})
    cfg = _github_config(clone, tidy=TidyConfig(keep_branches=("merged-work",)))
    seen = witness.compare(lambda: Before.survey(cfg), lambda: tidy.survey(cfg))
    assert seen["outcome"].remote_merged == ("open-head",)


# ------------------------------------------------------------------------ the adapter


def test_the_adapter_is_the_declared_seam():
    forge = GitHubForge(root=".")
    assert isinstance(forge, ForgeAdapterInterface)
    assert isinstance(forge.transport, GhTransport)
    assert forge.transport.host is None
    assert GH_DEFAULT_HOST == "github.com"


def test_heads_keep_only_named_heads(fake_gh, clone):
    fake_gh.script({key(PR_HEADS): {"out": HEADS}})
    assert GitHubForge(root=clone).open_change_request_heads(limit=200) == (
        frozenset({"open-head", ""}),
        "",
    )


def test_a_head_that_is_not_text_is_left_out_rather_than_crashing_the_survey(fake_gh, clone):
    """The one deliberate difference from the code this replaced, which built a set of
    whatever `headRefName` held and so raised `TypeError` on a list. `gh` never sends one;
    if a forge ever did, the survey now leaves it out instead of dying mid-report."""
    fake_gh.script({key(PR_HEADS): {"out": '[{"headRefName": ["x"]}, {"headRefName": "a"}]'}})
    assert GitHubForge(root=clone).open_change_request_heads(limit=200) == (
        frozenset({"a"}),
        "",
    )
    with pytest.raises(TypeError):
        Before._open_pr_heads(clone)


def test_releases_become_forge_releases(fake_gh, clone):
    fake_gh.script({key(RELEASES): {"out": LISTED}})
    releases, problem = GitHubForge(root=clone).releases(limit=100)
    assert problem == ""
    assert releases == (
        ForgeRelease(tag="v9.9.9-draft", name="Next", draft=True),
        ForgeRelease(tag="v1.0.0", name="One", draft=False),
        ForgeRelease(tag="", name="Untitled draft", draft=True),
        ForgeRelease(tag="", name="", draft=True),
        ForgeRelease(tag="7", name="", draft=True),
        ForgeRelease(tag="", name="no draft flag", draft=False),
    )


def test_the_limit_is_the_callers(fake_gh, clone):
    fake_gh.script(
        {
            key(["pr", "list", "--json", "headRefName", "--limit", "5"]): {"out": "[]"},
            key(["release", "list", "--json", "tagName,name,isDraft", "--limit", "9"]): {
                "out": "[]"
            },
        }
    )
    forge = GitHubForge(root=clone)
    assert forge.open_change_request_heads(limit=5) == (frozenset(), "")
    assert forge.releases(limit=9) == ((), "")


class ScriptedTransport:
    """A transport double whose `survey` gives one scripted answer, for the parts of the
    adapter that do not depend on a process at all. The other three shapes fail loudly:
    the adapter reads through `survey` and nothing else."""

    def __init__(self, value: Any, problem: str = "", executable: str = "gh") -> None:
        self.value, self.problem, self.executable = value, problem, executable
        self.asked: list[tuple[tuple[str, ...], Any]] = []

    def run(self, args, *, cwd=None, stdin=None):
        raise AssertionError("the adapter reads through survey")

    def json(self, args, *, cwd=None, stdin=None):
        raise AssertionError("the adapter reads through survey")

    def probe(self, args, *, cwd=None, stdin=None, strip=True, with_stderr=False):
        raise AssertionError("the adapter reads through survey")

    def survey(self, args, *, cwd=None, stdin=None):
        self.asked.append((tuple(args), cwd))
        return self.value, self.problem


def test_a_listing_names_the_client_the_transport_runs():
    transport = ScriptedTransport({"message": "nope"}, executable="gh-enterprise")
    forge = GitHubForge(root="/r", transport=transport)
    assert forge.releases(limit=1) == (
        (),
        "`gh-enterprise release list` returned a JSON object where a listing was expected",
    )
    asked = ("release", "list", "--json", "tagName,name,isDraft", "--limit", "1")
    assert transport.asked == [(asked, "/r")]


def test_a_problem_from_the_transport_is_passed_on_with_nothing_read():
    transport = ScriptedTransport([{"headRefName": "x"}], problem="could not ask")
    assert GitHubForge(root="/r", transport=transport).open_change_request_heads(limit=1) == (
        frozenset(),
        "could not ask",
    )
