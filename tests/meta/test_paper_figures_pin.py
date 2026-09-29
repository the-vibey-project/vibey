# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The history figures' pin must be a commit every clone of the integration branch can walk.

PR #1235 pinned the figures to 3680d700, a commit on its own branch. The squash merge
replaced that branch with one new commit, so 3680d700 existed only in the clone that made
it, and develop's CI failed in `git log` (exit 128) on every run after. The script now
refuses such a pin with a reason, before it reads any history; these tests hold it to that.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "paper_figures.py"
# Run in its own interpreter, as the forecast-caption test does: paper_figures imports its
# siblings as top-level packages whose names collide with other test-imported packages.
PROBE = (
    "import json, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import paper_figures\n"
    "guard = paper_figures.RevisionPinGuard(Path(sys.argv[2]))\n"
    "tree = sys.argv[3] or None\n"
    "print(json.dumps({rev: [guard.problems(rev, tree), guard.resolve(rev, tree)]\n"
    "                  for rev in sys.argv[4:]}))\n"
)
# A throwaway repository must not pick up the developer's identity, signing or hooks.
GIT = [
    "git",
    "-c",
    "user.name=pin-test",
    "-c",
    "user.email=pin-test@example.invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run([*GIT, *args], cwd=repo, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    # Each commit changes the tree: a pin is also found by its tree, so commits that share
    # one (as empty commits all do) would stand in for each other.
    (repo / "log.txt").write_text(
        ((repo / "log.txt").read_text("utf-8") if (repo / "log.txt").exists() else "")
        + message
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "log.txt")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _history(repo: Path) -> dict[str, str]:
    """base -> squash on develop (also origin/develop), a local commit on top, and a
    feature-branch commit that the squash discarded."""
    _git(repo, "init", "-q", "-b", "develop")
    base = _commit(repo, "chore: base")
    _git(repo, "checkout", "-q", "-b", "feature")
    feature = _commit(repo, "docs: pre-squash commit a pin once named")
    _git(repo, "checkout", "-q", "develop")
    squash = _commit(repo, "docs: the squash merge (#1)")
    _git(repo, "update-ref", "refs/remotes/origin/develop", squash)
    local = _commit(repo, "fix: unpushed work on top")
    return {"base": base, "feature": feature, "squash": squash, "local": local}


def _probe(repo: Path, tree: str | None, *revisions: str) -> dict[str, list]:
    done = subprocess.run(
        [sys.executable, "-c", PROBE, str(SCRIPT.parent), str(repo), tree or "", *revisions],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(done.stdout)


def _problems(repo: Path, *revisions: str, tree: str | None = None) -> dict[str, list[str]]:
    return {rev: found[0] for rev, found in _probe(repo, tree, *revisions).items()}


def test_a_pin_on_the_integration_branch_is_accepted(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    found = _problems(tmp_path, commits["base"], commits["squash"])
    assert found == {commits["base"]: [], commits["squash"]: []}


def test_a_commit_a_squash_merge_discarded_is_refused(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    reasons = _problems(tmp_path, commits["feature"])[commits["feature"]]
    assert any("not an ancestor of the checked-out HEAD" in r for r in reasons), reasons
    assert any("not on origin/develop's history" in r for r in reasons), reasons


def test_a_pin_the_remote_integration_branch_lacks_is_refused(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    reasons = _problems(tmp_path, commits["local"])[commits["local"]]
    assert len(reasons) == 1 and "not on origin/develop's history" in reasons[0], reasons


def test_a_revision_absent_from_the_clone_is_refused(tmp_path: Path) -> None:
    _history(tmp_path)
    missing = "0" * 40
    reasons = _problems(tmp_path, missing)[missing]
    assert len(reasons) == 1 and "is not a commit in this clone" in reasons[0], reasons


def test_the_integration_branch_is_read_from_the_repository_config(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text('[branches]\nintegration = "trunk"\n', "utf-8")
    _git(tmp_path, "update-ref", "refs/remotes/origin/trunk", commits["base"])
    reasons = _problems(tmp_path, commits["squash"])[commits["squash"]]
    assert len(reasons) == 1 and "not on origin/trunk's history" in reasons[0], reasons


def test_the_check_refuses_an_orphaned_pin_before_reading_history(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "paper.md").write_text(
        f"<!-- BEGIN GENERATED figure:commits-daily rev:{commits['feature']} — regenerated by "
        "scripts/paper_figures.py -->\n```latex\n```\n<!-- END GENERATED figure:commits-daily -->\n",
        encoding="utf-8",
    )
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(tmp_path), "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert "not an ancestor of the checked-out HEAD" in done.stderr


def _promoted(repo: Path) -> dict[str, str]:
    """develop (also origin/develop) carries a pin; a promotion branch holds its rebased
    copy -- same tree, new SHA -- on top of a commit develop never had."""
    commits = _history(repo)
    pin = commits["squash"]
    _git(repo, "checkout", "-q", "-b", "release", commits["base"])
    _commit(repo, "fix: a hotfix that landed on main alone")
    # The copy a clean rebase leaves: the pin's exact tree on a new parent, a new SHA.
    tree = _git(repo, "rev-parse", f"{pin}^{{tree}}")
    parent = _git(repo, "rev-parse", "HEAD")
    copied = _git(repo, "commit-tree", tree, "-p", parent, "-m", "docs: the squash merge (#1)")
    _git(repo, "reset", "-q", "--hard", copied)
    copy = _git(repo, "rev-parse", "HEAD")
    return {**commits, "pin": pin, "copy": copy, "tree": _git(repo, "rev-parse", f"{pin}^{{tree}}")}


def test_a_rebased_copy_of_the_pin_is_found_by_its_tree(tmp_path: Path) -> None:
    c = _promoted(tmp_path)
    problems, resolved = _probe(tmp_path, c["tree"], c["pin"])[c["pin"]]
    assert problems == [] and resolved == c["copy"], (problems, resolved)


def test_without_its_tree_a_rebased_pin_is_still_refused(tmp_path: Path) -> None:
    c = _promoted(tmp_path)
    problems, resolved = _probe(tmp_path, None, c["pin"])[c["pin"]]
    assert resolved is None
    assert any("not an ancestor of the checked-out HEAD" in r for r in problems), problems


def test_a_pin_absent_from_the_clone_is_found_by_its_tree(tmp_path: Path) -> None:
    c = _promoted(tmp_path)
    missing = "f" * 40
    problems, resolved = _probe(tmp_path, c["tree"], missing)[missing]
    assert problems == [] and resolved == c["copy"], (problems, resolved)


def test_a_pre_squash_tree_still_does_not_reach_the_integration_branch(tmp_path: Path) -> None:
    commits = _history(tmp_path)
    tree = _git(tmp_path, "rev-parse", f"{commits['feature']}^{{tree}}")
    problems = _problems(tmp_path, commits["feature"], tree=tree)[commits["feature"]]
    assert any("not on origin/develop's history" in r for r in problems), problems
