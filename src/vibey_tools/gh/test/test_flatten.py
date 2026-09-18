# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Flattening a branch, against real git history.

The command's whole claim is that content survives a rewrite, and a claim about git is
worth exactly what git says about it. So every test here builds an actual repository in a
temporary directory -- with an actual bare remote, actual merge commits, actual authorship
-- and reads the result back out of git. Nothing stubs `subprocess`: a stub would agree
with whatever this file believes about git's behaviour, which is the thing under test.

Four test doubles do exist, at the bottom, and each subclasses `Flattener` to break
something the real one otherwise makes impossible -- a tree that is not the branch's, a
ref that moves mid-flight, a tree the repository does not have, a push whose lease was
dropped by a race nobody can schedule. They are how the guards get to prove they are
guards. Everything else drives the public API.

The forge is the one thing that IS stubbed, and by an autouse fixture so it cannot be
forgotten: these repositories live in a temporary directory and GitHub has never heard of
them, so a review-thread check allowed to reach out would be asking a real server about a
branch that does not exist there. `Forge` is what `gh` would have said, and its default is
what an unauthenticated machine says -- no `gh` at all -- because that is also the degraded
path every other test then proves is reported as degraded rather than as clean.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import flatten, github_state
from vibey_gh.cli import main as cli_main
from vibey_gh.config import GhConfig
from vibey_gh.interfaces.flatten_interface import FlattenerInterface

MAINTAINER = "Maintainer <maintainer@example.com>"
ALICE = "Alice <alice@example.com>"
BOT = "Review Bot <bot@example.com>"
# Credited by trailer and never by authorship, which is this repository's own convention:
# its commits name the collaborator in `Co-Authored-By:` while the git author is the
# operator. A flatten that read credit off authorship alone would lose exactly this one.
OLD_ONE = "Old One <old@example.com>"

# --------------------------------------------------------------------------- helpers


def git(cwd: Path, *args: str) -> str:
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    assert run.returncode == 0, f"git {' '.join(args)}: {run.stderr}"
    return run.stdout


def sha(work: Path, rev: str = "HEAD") -> str:
    return git(work, "rev-parse", rev).strip()


def commit(work: Path, message: str, *, author: str = MAINTAINER, file: str | None = None) -> str:
    """One commit by whoever, with an optional file change, returning its sha."""
    if file is not None:
        (work / file).write_text(f"{file}: {message.splitlines()[0]}\n", encoding="utf-8")
        git(work, "add", "-A")
    git(work, "commit", "-q", "--allow-empty", f"--author={author}", "-m", message)
    return sha(work)


def topic(work: Path, name: str = "feat/thing", *, base: str = "origin/develop") -> str:
    git(work, "checkout", "-q", "-b", name, base)
    return name


def cfg(work: Path, **kw) -> GhConfig:
    return GhConfig(root=work, **kw)


# What the forge says about a branch with no open pull request. A named constant because
# `pages` hands it back as one page of a walk too: a pull request can close between two
# calls, and that tail must not read as the whole answer.
CLOSED: dict[str, Any] = {"data": {"repository": {"pullRequests": {"nodes": []}}}}


class Forge:
    """What `gh` would have said -- or how it would have failed, which is also an answer."""

    def __init__(self) -> None:
        # The default is a machine with no GitHub CLI on it, which is the honest starting
        # point for a repository the forge has never heard of.
        self.reply: object = FileNotFoundError(2, "No such file or directory", "gh")
        # One reply per call, for the tests that walk a paginated connection. Empty means
        # every call gets `reply`, which is what a single-page answer needs.
        self.replies: list[object] = []
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> Any:
        self.calls.append(args)
        reply = self.replies.pop(0) if self.replies else self.reply
        if isinstance(reply, BaseException):
            raise reply
        return reply

    @staticmethod
    def page(
        threads: Any,
        *,
        number: int = 12,
        after: str = "",
        more: bool | None = None,
        pulls: int = 1,
    ) -> dict[str, Any]:
        """One page of the thread connection, naming the next cursor when there is one.

        `more` is separate from `after` on purpose. `endCursor` is nullable in the schema,
        so a forge is allowed to answer "there is another page" and name nowhere to go --
        and a helper that derived `hasNextPage` from the cursor could not express that page
        at all, which is precisely why nothing caught the walk reporting it as clean. The
        default keeps every ordinary page one argument: a cursor means another page.

        `pulls` is the same story one level up. A branch may head more than one open pull
        request, the query asks for two, and two nodes is the only way to say so.
        """
        walked = {
            "number": number,
            "reviewThreads": {
                "pageInfo": {
                    "hasNextPage": bool(after) if more is None else more,
                    "endCursor": after or None,
                },
                "nodes": list(threads),
            },
        }
        siblings = [
            {"number": number + extra, "reviewThreads": {"pageInfo": {}, "nodes": []}}
            for extra in range(1, pulls)
        ]
        return {"data": {"repository": {"pullRequests": {"nodes": [walked, *siblings]}}}}

    def pull_request(self, *threads: dict[str, Any], number: int = 12) -> None:
        """One open pull request carrying these review threads, all on one page."""
        self.reply = self.page(threads, number=number)

    def pages(self, *pages: Any, number: int = 12) -> None:
        """One reply per page, each naming the next.

        A page given as a list is a list of threads; given as an exception or a ready-made
        reply it stands for a page that fails or answers with something else, which is how
        a walk that stops partway gets tested at all.
        """
        self.replies = []
        for n, page in enumerate(pages, 1):
            if isinstance(page, (BaseException, dict)):
                self.replies.append(page)
                continue
            after = f"cursor-{n}" if n < len(pages) else ""
            self.replies.append(self.page(page, number=number, after=after))

    def no_pull_request(self) -> None:
        self.reply = CLOSED


def thread(
    *, resolved: bool = False, author: str | None = "alice", **fields: Any
) -> dict[str, Any]:
    """One review thread as the GraphQL API shapes it, with every field overridable."""
    comment = {"path": "a.py", "line": 12, "body": "this drops the empty case\nand more", **fields}
    comment["author"] = {"login": author} if author is not None else None
    return {"isResolved": resolved, "comments": {"nodes": [comment]}}


@pytest.fixture(autouse=True)
def forge(monkeypatch) -> Forge:
    """No forge unless a test asks for one, and never the real one.

    `GH_REPO` is set so the repository is not itself a question put to `gh`: what these
    tests are about is the review-thread query, and a second call that has to be stubbed
    into agreeing is a second thing to get wrong.
    """
    monkeypatch.setenv("GH_REPO", "the-vibey-project/vibey")
    fake = Forge()
    monkeypatch.setattr(github_state, "gh_json", fake)
    return fake


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    """The bare repository the work tree pushes to. A path, so nothing leaves the machine."""
    git(tmp_path, "init", "-q", "--bare", "-b", "develop", "origin.git")
    return tmp_path / "origin.git"


@pytest.fixture
def work(tmp_path: Path, origin: Path) -> Path:
    """A repository on `develop`, one commit deep, with `origin/develop` in step."""
    path = tmp_path / "work"
    path.mkdir()
    git(path, "init", "-q", "-b", "develop", ".")
    git(path, "config", "user.email", "maintainer@example.com")
    git(path, "config", "user.name", "Maintainer")
    (path / "README.md").write_text("base\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "chore: base")
    git(path, "remote", "add", "origin", str(origin))
    git(path, "push", "-q", "origin", "develop")
    git(path, "fetch", "-q", "origin")
    return path


def a_merged_branch(work: Path) -> str:
    """The shape that sends a branch here: a web commit, a bot commit, and a merge.

    `feat: add the thing` carries no provenance trailer, the way a commit authored in the
    GitHub UI does not; the merge is integration coming back into the topic branch, which
    is what the Conventional Commits normaliser refuses outright.
    """
    name = topic(work)
    commit(work, "feat: add the thing", author=ALICE, file="a.txt")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: integration moved on", file="c.txt")
    git(work, "push", "-q", "origin", "develop")
    git(work, "checkout", "-q", name)
    commit(work, f"fix: the bot fixed it\n\n{cfg(work).trailer}", author=BOT, file="b.txt")
    git(work, "merge", "--no-ff", "-q", "develop", "-m", "Merge branch 'develop' into feat/thing")
    return name


# ------------------------------------------------------------------- the invariant


def test_a_merge_and_a_trailerless_commit_become_one_commit_with_the_same_tree(work):
    a_merged_branch(work)
    config = cfg(work)
    before, base = sha(work, "HEAD^{tree}"), sha(work, "origin/develop")

    plan, notes = flatten.Flattener().flatten(config)

    # The invariant, read back out of git rather than out of the plan.
    assert sha(work, "HEAD^{tree}") == before == plan.tree
    assert git(work, "rev-list", "--parents", "-n", "1", "HEAD").split() == [sha(work), base]
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"
    # Three commits went in -- two of them non-merge -- and the content of all three is
    # still on disk, which is the only claim that matters.
    assert plan.range_size == 3 and len(plan.commits) == 2
    assert (work / "a.txt").exists() and (work / "b.txt").exists() and (work / "c.txt").exists()
    assert git(work, "status", "--porcelain") == ""

    message = git(work, "log", "-1", "--format=%B")
    assert message.splitlines()[0] == "feat: add the thing"
    assert f"Co-Authored-By: {ALICE}" in message
    assert f"Co-Authored-By: {BOT}" in message
    assert message.count(config.trailer) == 1
    assert any("one commit on" in note for note in notes)


def test_untracked_files_neither_block_the_flatten_nor_enter_it(work):
    """Build output is not uncommitted work, and a commit built from a tree cannot take it."""
    name = topic(work)
    commit(work, "feat: real work", file="real.txt")
    (work / "junk.log").write_text("build output\n", encoding="utf-8")

    flatten.Flattener().flatten(cfg(work))

    assert (work / "junk.log").exists()
    assert git(work, "status", "--porcelain") == "?? junk.log\n"
    assert git(work, "ls-tree", "--name-only", "HEAD").split() == ["README.md", "real.txt"]
    assert name == git(work, "symbolic-ref", "--short", "HEAD").strip()


def test_the_default_base_is_fetched_before_it_is_read(work):
    """Proof the fetch is real: without it there is no `origin/develop` left to resolve."""
    topic(work)
    commit(work, "feat: work", file="w.txt")
    git(work, "update-ref", "-d", "refs/remotes/origin/develop")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.base == "origin/develop"
    assert plan.base_sha == sha(work, "origin/develop")


def diverged(work: Path) -> str:
    """A topic branch and its base with a commit each that the other has never seen.

    The shape that loses work: `landed.txt` is on the base and absent from the branch, so
    the branch's tree is the base's content MINUS a merged pull request.
    """
    name = topic(work)
    commit(work, "feat: the topic's own work", author=ALICE, file="topic.txt")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: a pull request that landed after the branch was cut", file="landed.txt")
    git(work, "push", "-q", "origin", "develop")
    git(work, "checkout", "-q", name)
    return name


def test_a_base_the_branch_has_not_merged_is_refused_rather_than_reverted(work):
    """The work-loss bug, and the one tree equality cannot see.

    `commit-tree <HEAD's tree> -p <base>` presents the branch's tree as the whole of the
    base plus the branch, so a base carrying a commit the branch never merged is DELETED
    by the flatten -- and the invariant agrees, because the tree is correctly HEAD's.
    Only ancestry catches it, so the assertion here is the refusal, not the revert.
    """
    name = diverged(work)
    before = sha(work)
    assert not (work / "landed.txt").exists()  # the content a flatten would take out

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work))

    assert "origin/develop is not an ancestor of feat/thing" in str(raised.value)
    assert "REVERTING" in str(raised.value)
    # The remedy, spelled as the commands to run -- a refusal with no way forward is a
    # reason to reach for the hand procedure that caused this in the first place.
    assert "  git merge origin/develop" in str(raised.value)
    assert "  vibey-gh flatten --onto origin/develop" in str(raised.value)
    assert sha(work, f"refs/heads/{name}") == before
    assert git(work, "ls-tree", "--name-only", "origin/develop").split() == [
        "README.md",
        "landed.txt",
    ]


def test_merging_the_base_in_first_is_what_makes_the_flatten_legal(work):
    """The remedy the refusal names, carried out: the merge is what makes it an ancestor."""
    diverged(work)
    git(work, "merge", "--no-ff", "-q", "develop", "-m", "Merge branch 'develop' into feat/thing")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.base_sha == sha(work, "origin/develop") == sha(work, "HEAD^")
    # Both sides survive: the branch's own work and the pull request it had to merge.
    assert (work / "topic.txt").exists() and (work / "landed.txt").exists()
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_a_branch_left_behind_by_its_base_is_told_it_has_nothing_to_flatten(work):
    """Strictly behind is not divergence, and the useful thing to say is the simpler one."""
    topic(work, "feat/behind")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: the base moved on alone", file="landed.txt")
    git(work, "push", "-q", "origin", "develop")
    git(work, "checkout", "-q", "feat/behind")

    with pytest.raises(flatten.FlattenError, match="no commits origin/develop does not"):
        flatten.Flattener().plan(cfg(work))


# ----------------------------------------------------------------------- the message


def test_the_message_is_the_first_non_merge_commits_without_its_trailers(work):
    name = topic(work)
    commit(
        work,
        "feat: carry the body\n\nSome body text.\n\n"
        f"Refs: #12\nCo-Authored-By: {OLD_ONE}\nMade-With: something stale",
        author=ALICE,
        file="first.txt",
    )
    commit(work, "fix: a later commit nobody reads the message of", author=BOT, file="later.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat: carry the body"
    assert "Some body text." in plan.message
    # Re-derivable means re-derived: a trailer carried over from ONE commit of the range
    # would be an assertion nobody made about the others.
    assert "Refs: #12" not in plan.message
    assert "something stale" not in plan.message
    assert plan.message.count("Made-With:") == 1
    # Credit is the exception, for the same reason the breaking footers are: nothing
    # re-derives a co-author who is not an author. Stripping the block is how the other
    # trailers get recomputed, not how this one gets dropped.
    assert f"Co-Authored-By: {OLD_ONE}" in plan.message
    assert plan.coauthors == (ALICE, OLD_ONE, BOT)
    assert sha(work, f"refs/heads/{name}") == sha(work)


def test_a_merge_commits_own_footers_and_trailers_are_not_dropped(work):
    """A merge commit has a MESSAGE, and everything in it was being thrown away.

    The range was read with `--no-merges`, and `records` is the only input to `_coauthors`,
    `_closing_footers`, `_breaking_footers` and `_references` -- so a co-author credited on
    the merge, an issue it promised to close, a break it declared and an issue it referenced
    all left the history at once, silently, with the whole-range docstrings still promising
    otherwise. Resolving a conflict in a merge is exactly when a collaborator gets named.

    Authorship is the one thing a merge still does not carry: MAINTAINER merged and authored
    nothing, and the plan says so in its two counts.
    """
    name = topic(work)
    commit(work, "feat: the topic's work", author=ALICE, file="a.txt")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: integration moved on", file="c.txt")
    git(work, "push", "-q", "origin", "develop")
    git(work, "checkout", "-q", name)
    git(
        work,
        "merge",
        "--no-ff",
        "-q",
        "develop",
        "-m",
        "Merge branch 'develop' into feat/thing\n\nWe untangled the conflict together.\n\n"
        f"Closes #41\n\nBREAKING-CHANGE: the old flag is gone\nCo-Authored-By: {OLD_ONE}",
    )

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.range_size == 2 and len(plan.commits) == 1
    # The subject still comes from the non-merge commit: a merge has none worth reusing,
    # which is the one thing the narrower list is still read for.
    assert plan.subject == "feat: the topic's work"
    assert OLD_ONE in plan.coauthors and f"Co-Authored-By: {OLD_ONE}" in plan.message
    assert "Closes #41" in plan.message
    assert "BREAKING-CHANGE: the old flag is gone" in plan.message
    assert plan.references == ("#41",)
    # Merging is not authoring, so the merger is credited by neither half.
    assert MAINTAINER not in plan.coauthors
    assert ALICE in plan.coauthors


def test_a_breaking_change_footer_survives_the_rewrite(work):
    """Losing it demotes a major release to a patch one, and nothing else records it."""
    topic(work)
    commit(
        work,
        "feat: change the interface\n\nSome body.\n\n"
        "BREAKING-CHANGE: the old flag is gone\nRefs: #12\n"
        f"Co-Authored-By: {OLD_ONE}",
        author=ALICE,
        file="x.txt",
    )
    config = cfg(work)

    plan, _ = flatten.Flattener().flatten(config)

    assert plan.message.count("BREAKING-CHANGE: the old flag is gone") == 1
    # Kept because nothing re-derives it -- not because its paragraph was spared, which
    # `Refs:` leaving from the same paragraph is what proves.
    assert "Refs: #12" not in plan.message
    assert f"Co-Authored-By: {ALICE}" in plan.message
    assert f"Co-Authored-By: {OLD_ONE}" in plan.message
    assert plan.message.count(config.trailer) == 1
    assert "BREAKING-CHANGE: the old flag is gone" in git(work, "log", "-1", "--format=%B")


def test_the_unhyphenated_breaking_change_is_kept_once_and_not_twice(work):
    """`BREAKING CHANGE:` is not trailer-shaped, so it never left; re-adding it would double it."""
    topic(work)
    commit(work, "feat: change it\n\nBREAKING CHANGE: the old flag is gone", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.message.count("BREAKING CHANGE:") == 1


def test_a_breaking_change_in_a_later_commit_survives_too(work):
    """The footer used to be read from the FIRST commit only, so this one was dropped.

    A range breaks something in whichever commit breaks it, and that is rarely the commit
    whose subject gets reused. Dropping it turns a MAJOR release into a minor one, which
    nothing downstream notices until a build breaks against a version that promised it
    would not -- the most expensive direction for a silent loss to run in.
    """
    topic(work)
    commit(work, "feat: add the thing", author=ALICE, file="a.txt")
    commit(
        work,
        "fix: drop the old path\n\nBREAKING-CHANGE: the old flag is gone",
        author=BOT,
        file="b.txt",
    )

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat: add the thing"
    assert plan.message.count("BREAKING-CHANGE: the old flag is gone") == 1
    assert "BREAKING-CHANGE: the old flag is gone" in git(work, "log", "-1", "--format=%B")


def test_one_break_written_two_ways_is_carried_once(work):
    """The two spellings Conventional Commits allows are one assertion, not two."""
    topic(work)
    commit(work, "feat: one\n\nBREAKING-CHANGE: the old flag is gone", file="a.txt")
    commit(work, "fix: two\n\nBREAKING CHANGE: The Old Flag Is Gone", file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.message.lower().count("the old flag is gone") == 1
    # The first spelling seen is the one written, the way the co-authors keep first-seen
    # order -- neither spelling is normalised into the other.
    assert "BREAKING-CHANGE: the old flag is gone" in plan.message


def test_two_different_breaks_are_both_carried_in_first_seen_order(work):
    topic(work)
    commit(work, "feat: one\n\nBREAKING-CHANGE: the old flag is gone", file="a.txt")
    commit(work, "fix: two\n\nBREAKING-CHANGE: the config file moved", file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert "BREAKING-CHANGE: the old flag is gone" in plan.message
    assert "BREAKING-CHANGE: the config file moved" in plan.message
    assert plan.message.index("old flag") < plan.message.index("config file")


def test_a_bang_on_a_later_commit_re_marks_the_composed_subject(work):
    """`!` alone is a breaking change, and exactly one subject survives a flatten.

    The commit that declared the break is not the commit whose subject is reused, so the
    `!` would leave with the discarded subject and the flattened commit would say nothing
    breaks. The remedy is re-marking rather than a synthesised footer: that commit wrote
    no description, and one invented here would put words in its author's mouth.
    """
    topic(work)
    commit(work, "feat: add the thing", author=ALICE, file="a.txt")
    commit(work, "fix!: drop the old flag", author=BOT, file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat!: add the thing"
    assert git(work, "log", "-1", "--format=%s").strip() == "feat!: add the thing"


def test_the_marker_lands_where_the_spec_puts_it_on_a_scoped_subject(work):
    """Immediately before the colon, which is behind the scope and not in front of it."""
    topic(work)
    commit(work, "feat(api): add the thing", file="a.txt")
    commit(work, "fix!: drop the old flag", file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat(api)!: add the thing"


def test_a_subject_that_already_declares_the_break_is_not_marked_twice(work):
    topic(work)
    commit(work, "feat!: add the thing", author=ALICE, file="a.txt")
    commit(work, "fix!: drop the old flag", author=BOT, file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat!: add the thing"


def test_an_explicit_message_does_not_drop_the_ranges_breaking_change(work):
    """`--message` rewrites the subject, not the content -- and the content still breaks."""
    topic(work)
    commit(work, "feat: one\n\nBREAKING-CHANGE: the old flag is gone", file="a.txt")
    commit(work, "fix!: two", file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work), message="chore: say it my way")

    assert plan.subject == "chore!: say it my way"
    assert "BREAKING-CHANGE: the old flag is gone" in plan.message


def test_an_explicit_message_replaces_the_one_that_would_be_reused(work):
    topic(work)
    commit(work, "feat: the reused subject", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work), message="fix: say it my way")

    assert plan.subject == "fix: say it my way"
    assert "the reused subject" not in plan.message


def test_a_subject_that_is_not_conventional_is_normalised(work):
    """The Conventional Commits gate is half of why this command exists."""
    topic(work)
    commit(work, "feat: fine", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work), message="Tidied up the thing")

    assert plan.subject == "chore: Tidied up the thing"


def test_a_message_ending_in_trailers_is_joined_rather_than_reopened(work):
    topic(work)
    commit(work, "feat: work", author=ALICE, file="x.txt")
    config = cfg(work)

    plan, _ = flatten.Flattener().flatten(config, message="feat: joined\n\nbody line\n\nRefs: #9")

    assert f"Refs: #9\nCo-Authored-By: {ALICE}\n{config.trailer}\n" in plan.message


def test_a_message_that_already_credits_everyone_gains_nothing(work):
    topic(work)
    commit(work, "feat: work", file="x.txt")
    config = cfg(work)
    message = f"feat: complete\n\nCo-Authored-By: {MAINTAINER}\n{config.trailer}"

    plan, _ = flatten.Flattener().flatten(config, message=message)

    assert plan.message == message + "\n"
    assert plan.message.count("Co-Authored-By:") == 1
    assert plan.message.count("Made-With:") == 1


def test_an_author_already_credited_is_not_credited_a_second_time(work):
    """However the message spells them: the comparison is case-insensitive."""
    topic(work)
    commit(work, "feat: work", author=ALICE, file="x.txt")

    plan, _ = flatten.Flattener().flatten(
        cfg(work), message="feat: mine\n\nCo-Authored-By: ALICE <Alice@Example.COM>"
    )

    assert plan.message.count("Co-Authored-By:") == 1
    assert "Co-Authored-By: ALICE <Alice@Example.COM>" in plan.message
    assert plan.message.count("Made-With:") == 1


def test_every_distinct_author_is_credited_once_in_first_seen_order(work):
    """Absorbing a review bot's commit without crediting it is how a flatten loses work."""
    topic(work)
    commit(work, "feat: first", author=ALICE, file="one.txt")
    commit(work, "fix: second", author=BOT, file="two.txt")
    commit(work, "fix: third", author="ALICE <Alice@Example.COM>", file="three.txt")

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.coauthors == (ALICE, BOT)
    assert [note for note in notes if note.startswith("co-author: ")] == [
        f"co-author: {ALICE}",
        f"co-author: {BOT}",
    ]


def test_a_co_author_declared_by_trailer_is_credited_and_not_discarded(work):
    """Authorship is only half of how credit is written, and here it is the quieter half.

    This repository names its collaborators in a `Co-Authored-By:` trailer while the git
    author stays the operator, so credit re-derived from authorship alone would drop every
    one of them -- defeating the command's own headline promise on the commits it exists
    for. The trailer block is still stripped; this one is read back off the range.
    """
    topic(work)
    commit(work, f"feat: work\n\nCo-Authored-By: {ALICE}", file="x.txt")

    plan, notes = flatten.Flattener().flatten(cfg(work))

    assert plan.coauthors == (MAINTAINER, ALICE)
    assert f"co-author: {ALICE}" in notes
    # Read back out of git, because the message on the ref is the thing that credits them.
    written = git(work, "log", "-1", "--format=%B")
    assert f"Co-Authored-By: {MAINTAINER}" in written
    assert f"Co-Authored-By: {ALICE}" in written


def test_declared_co_authors_are_collected_from_every_commit_of_the_range(work):
    """From the WHOLE range, the way the breaking footers are, and for the same reason.

    The commit that names a collaborator is rarely the commit whose message is reused, so
    reading credit from the first one is reading it from the wrong one. Duplicates are one
    person however they are cased and whichever spelling of the key names them, and the
    case first written is the case kept.
    """
    topic(work)
    commit(work, f"feat: first\n\nCo-Authored-By: {ALICE}", file="one.txt")
    commit(work, f"fix: second\n\nCo-Authored-By: {BOT}", author=ALICE, file="two.txt")
    commit(
        work,
        "fix: third\n\nCo-authored-by: ALICE <Alice@Example.COM>",
        author=BOT,
        file="three.txt",
    )

    plan, _ = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.coauthors == (MAINTAINER, ALICE, BOT)
    assert plan.message.count("Co-Authored-By:") == 3
    assert "Alice@Example.COM" not in plan.message


def test_a_co_author_above_the_provenance_paragraph_is_still_credited(work):
    """The message shape this repository's own hook writes, which no other credit test had.

    `.githooks/commit-msg` appends the provenance trailer as a paragraph of its OWN, so an
    ordinary commit here ends in TWO trailer paragraphs separated by a blank line. Every
    other test in this file puts `Co-Authored-By:` in the final paragraph, which is a shape
    this repository never produces -- so restricting the reader to git's final paragraph
    passed all of them while dropping every declared collaborator in real use.

    Nothing fails when that happens, which is the dangerous part: a dropped co-author looks
    exactly like a commit that never named one. The first real flatten of this very branch
    dropped its own, with 1258 tests and 100% branch coverage green.
    """
    config = cfg(work)
    topic(work)
    commit(
        work,
        f"feat: work\n\nCo-Authored-By: {ALICE}\n\n{config.trailer}",
        file="x.txt",
    )

    plan, notes = flatten.Flattener().flatten(config, dry_run=True)

    assert ALICE in plan.coauthors
    assert f"co-author: {ALICE}" in notes
    assert f"Co-Authored-By: {ALICE}" in plan.message
    # The provenance trailer was already there, in its own paragraph, and is not doubled.
    assert plan.message.count(f"{config.trailer_key}:") == 1


def test_a_closing_keyword_survives_the_rewrite(work):
    """`Closes: #12` is trailer-shaped, so stripping the block used to take it with it.

    Nothing re-derives an issue-closing keyword -- not authorship, not the tree, not the
    branch name -- so losing it silently breaks issue auto-closing on the merge.
    """
    topic(work)
    commit(work, "feat: work\n\nCloses: #12\nRefs: #9", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert "Closes: #12" in plan.message
    # Kept because nothing re-derives it, not because its paragraph was spared -- which
    # `Refs:` leaving from the same paragraph is what proves.
    assert "Refs: #9" not in plan.message
    assert "Closes: #12" in git(work, "log", "-1", "--format=%B")


def test_a_closing_keyword_in_a_later_commit_survives_too(work):
    """From the WHOLE range, the way the breaking footers are: the promise is rarely first."""
    topic(work)
    commit(work, "feat: the subject that gets reused", file="a.txt")
    commit(work, "fix: the commit that closes it\n\nFixes #34", file="b.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.subject == "feat: the subject that gets reused"
    assert "Fixes #34" in plan.message


def test_one_issue_promised_twice_keeps_the_first_promise_and_only_one(work):
    """The identity is the issue, not the line: `Closes #7` and `Fixes #7` are one issue."""
    topic(work)
    commit(work, "feat: one\n\nCloses #7", file="a.txt")
    commit(work, "fix: two\n\nfixes #7", file="b.txt")
    commit(work, "fix: three\n\nResolves the-vibey-project/vibey#7", file="c.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.message.count("#7") == 2
    assert "Closes #7" in plan.message
    # A different repository's issue #7 is a different issue, so it is not deduplicated away.
    assert "Resolves the-vibey-project/vibey#7" in plan.message
    assert "fixes #7" not in plan.message


def test_a_closing_keyword_goes_above_a_trailer_block_the_message_already_has(work):
    """Body, then the promises, then the trailers -- in that order and in three paragraphs."""
    config = cfg(work)
    topic(work)
    commit(work, "feat: one", file="a.txt")
    commit(work, "fix: two\n\nCloses #12", file="b.txt")

    plan, _ = flatten.Flattener().flatten(config, message="feat: mine\n\nRefs: #9")

    assert plan.message == (
        f"feat: mine\n\nCloses #12\n\nRefs: #9\nCo-Authored-By: {MAINTAINER}\n{config.trailer}\n"
    )


def test_a_closing_keyword_the_message_already_carries_is_not_written_twice(work):
    topic(work)
    commit(work, "feat: work\n\nCloses #12", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work), message="feat: mine\n\nCloses #12")

    assert plan.message.count("Closes #12") == 1


def test_nothing_promises_to_close_an_issue_the_range_never_named(work):
    """Prose about an issue is not a promise to close it, and inventing one closes it anyway."""
    topic(work)
    commit(work, "feat: work\n\nThis fixes #12 in a way that still needs review.", file="x.txt")

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert plan.references == ("#12",)
    assert plan.message.count("#12") == 1
    assert plan.message.splitlines()[-1] == cfg(work).trailer


def test_the_closing_keywords_sit_above_the_trailer_block_and_a_second_flatten_agrees(work):
    """Placement is load-bearing: `Closes #12` is not `token: value`.

    Put one inside the trailer block and the block stops being one -- so the next flatten
    of that message would find no provenance trailer in it and add a second.
    """
    config = cfg(work)
    topic(work)
    commit(work, f"feat: work\n\nCloses #12\n\nCo-Authored-By: {ALICE}", file="x.txt")

    first, _ = flatten.Flattener().flatten(config)
    git(work, "checkout", "-q", "-b", "feat/again", "origin/develop")
    commit(work, first.message, file="y.txt")
    second, _ = flatten.Flattener().flatten(config)

    assert "Closes #12\n\nCo-Authored-By:" in first.message
    assert first.message.count(config.trailer) == 1
    assert second.message.count(config.trailer) == 1
    assert second.message.count("Closes #12") == 1


def test_a_body_sentence_shaped_like_the_provenance_trailer_does_not_suppress_it(work):
    """Trailers live in the final paragraph; a colon in a sentence elsewhere is not one.

    Searching the whole message meant a body line opening `Made-With:` -- exactly how one
    writes ABOUT this tool -- suppressed the trailer the commit needs to pass its own gate.
    The body goes on afterwards, which is what makes that line prose rather than a trailer.
    """
    config = cfg(work)
    topic(work)
    commit(
        work,
        f"feat: work\n\n{config.trailer_key}: is what the hook appends.\n\nThen more body.",
        file="x.txt",
    )

    plan, _ = flatten.Flattener().flatten(config)

    assert plan.message.splitlines()[-1] == config.trailer
    assert plan.message.count(f"{config.trailer_key}:") == 2


def test_a_body_line_quoting_a_co_author_does_not_suppress_the_real_attribution(work):
    """The quoted line named nobody, and taking it as credit dropped whoever it displaced."""
    topic(work)
    commit(
        work,
        "feat: work\n\nCo-Authored-By: is the trailer git reads.\n\nMore body.",
        author=ALICE,
        file="x.txt",
    )

    plan, _ = flatten.Flattener().flatten(cfg(work))

    assert f"Co-Authored-By: {ALICE}" in plan.message
    assert plan.message.count("Co-Authored-By:") == 2


# ------------------------------------------------------- what the rewrite orphans


def test_unresolved_review_threads_refuse_the_rewrite_and_are_listed(work, forge):
    """The operator's ask, and the failure it was written for.

    31 inline review comments were posted across five pull requests and 26 of them merged
    unaddressed, partly because a force-push had already marked them outdated and nothing
    was looking. So the threads are named -- author, file, line, first line of the body --
    because a refusal nobody can act on is a refusal everybody routes around.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    before = sha(work)
    forge.pull_request(
        thread(author="copilot", path="vibey_gh/flatten.py", line=88, body="this leaks a fd"),
        thread(author="alice", path="test/test_flatten.py", line=4, body="assert the note too"),
    )

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work))

    assert f"{name} has 2 unresolved review thread(s) on #12" in str(raised.value)
    assert "  copilot vibey_gh/flatten.py:88 — this leaks a fd" in str(raised.value)
    assert "  alice test/test_flatten.py:4 — assert the note too" in str(raised.value)
    assert "--orphan-comments" in str(raised.value)
    # Refused before anything moved, which is the point of deciding it in `plan`.
    assert sha(work, f"refs/heads/{name}") == before


def test_orphan_comments_says_yes_on_purpose_and_the_notes_still_say_what_it_cost(work, forge):
    """The opt-in is a decision, not a silencer: the threads are listed either way."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.pull_request(thread(author="copilot", path="a.py", line=3, body="wrong order"))

    plan, notes = flatten.Flattener().flatten(cfg(work), orphan_comments=True)

    assert plan.pull_request == 12 and plan.threads_problem == ""
    assert plan.threads == (
        flatten.ReviewThread(author="copilot", path="a.py", line="3", excerpt="wrong order"),
    )
    assert "orphaning 1 unresolved review thread(s) on #12:" in notes
    assert "  copilot a.py:3 — wrong order" in notes
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"
    assert sha(work, f"refs/heads/{name}") == sha(work)


def test_a_resolved_thread_is_not_a_reason_to_refuse(work, forge):
    """Resolved threads are already detached from the conversation; only open ones are lost."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.pull_request(thread(resolved=True), number=77)

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads == () and plan.pull_request == 77 and plan.threads_problem == ""
    assert "review threads on #77: none unresolved" in notes


def test_a_branch_with_no_open_pull_request_has_nothing_anchored_to_it(work, forge):
    """An answer, not an unknown -- and it must not be worded like one."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.no_pull_request()

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.pull_request is None and plan.threads == () and plan.threads_problem == ""
    assert "review threads: none — the branch has no open pull request" in notes


def test_a_missing_gh_is_reported_as_unknown_and_never_as_a_clean_check(work, forge):
    """The dangerous case is silence. An unchecked branch must not read like a checked one.

    `gh` is absent by default in this file, so what is asserted here is the SENTENCE: it
    says the check was not made, and it says what that leaves unprotected.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads_problem == "the GitHub CLI (`gh`) is not installed"
    unknown = [note for note in notes if note.startswith("review threads: NOT CHECKED")]
    assert unknown and "will be orphaned" in unknown[0]
    assert "none unresolved" not in "".join(notes)
    # It did not refuse: an unknown is a lesser thing than a known loss, and blocking every
    # flatten on an unauthenticated machine would be a different bug.
    assert plan.branch == "feat/thing"


def test_a_forge_that_answers_with_an_error_is_reported_as_itself(work, forge):
    """`gh_json` raises on a non-zero exit, and its words are more use than a paraphrase."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = RuntimeError("gh api graphql: HTTP 401: Bad credentials")

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads_problem == (
        "`gh api graphql` failed: gh api graphql: HTTP 401: Bad credentials"
    )
    assert any("Bad credentials" in note for note in notes)


def test_a_forge_answer_with_nothing_in_it_is_a_problem_and_not_a_clean_check(work, forge):
    """A `RuntimeError` with no message still means the question went unanswered."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = RuntimeError("")

    plan, _ = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads_problem == "`gh api graphql` failed: RuntimeError"


def test_a_thread_whose_every_nullable_field_is_null_is_still_named(work, forge):
    """A deleted author, an outdated line, an empty body: none of them may take the list down.

    A thread nobody can name is still a thread somebody is about to orphan, so every field
    falls back rather than failing -- and `originalLine` answers for the `line` that a
    thread GitHub already considers outdated no longer has.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.pull_request(
        thread(author=None, path=None, line=None, originalLine=41, body=None),
        {"isResolved": False},
    )

    plan, _ = flatten.Flattener().flatten(cfg(work), orphan_comments=True)

    assert plan.threads == (
        flatten.ReviewThread(author="someone", path="?", line="41", excerpt=""),
        flatten.ReviewThread(author="someone", path="?", line="?", excerpt=""),
    )


def test_a_thread_past_the_first_page_is_found_rather_than_reported_as_none(work, forge):
    """A connection answers with a WINDOW, and a window is not the set.

    `reviewThreads(first:100)` with no walk behind it reported a CLEAN check on a pull
    request whose 101st thread was the unresolved one: the refusal never fired, the notes
    said "none unresolved" about a branch that had some, and the rewrite orphaned exactly
    the thread the check exists to protect. The failure mode is the dangerous one -- it
    succeeds.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    before = sha(work)
    forge.pages(
        [thread(resolved=True) for _ in range(100)],
        [thread(author="alice", path="late.py", line=101, body="the 101st thread")],
    )

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work))

    assert f"{name} has 1 unresolved review thread(s) on #12" in str(raised.value)
    assert "  alice late.py:101 — the 101st thread" in str(raised.value)
    # Two calls, and the second asks from where the first left off. The first must name no
    # cursor at all: `$after` is nullable, and an empty string is not null.
    assert len(forge.calls) == 2
    assert "after=cursor-1" in forge.calls[1]
    assert not [argument for argument in forge.calls[0] if argument.startswith("after=")]
    assert sha(work, f"refs/heads/{name}") == before


def test_a_walk_that_stops_partway_is_a_problem_and_still_names_what_it_saw(work, forge):
    """Half a list is not a clean list, and it is not nothing either.

    The same rule the missing `gh` gets, applied to a walk that dies on page two: the
    unread remainder is a PROBLEM, so the notes say NOT CHECKED rather than counting the
    threads in hand as all of them. What was seen is still carried and still refuses --
    those threads are a known loss, and a known loss outranks an unknown one.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    seen = flatten.ReviewThread(author="alice", path="a.py", line="3", excerpt="page one")

    def arm() -> None:
        forge.pages(
            [thread(author="alice", path="a.py", line=3, body="page one")],
            RuntimeError("gh api graphql: HTTP 502"),
        )

    arm()
    plan, notes = flatten.Flattener().flatten(cfg(work), orphan_comments=True, dry_run=True)

    assert plan.pull_request == 12 and plan.threads == (seen,)
    assert plan.threads_problem == "`gh api graphql` failed: gh api graphql: HTTP 502"
    assert [note for note in notes if note.startswith("review threads: NOT CHECKED")]
    assert "orphaning 1 unresolved review thread(s) on #12:" in notes
    assert "  alice a.py:3 — page one" in notes

    arm()
    with pytest.raises(flatten.FlattenError, match="1 unresolved review thread"):
        flatten.Flattener().flatten(cfg(work))


def test_a_graphql_errors_payload_is_not_read_as_having_no_pull_request(work, forge):
    """HTTP 200 carrying an `errors` array is a FAILED query, not an empty repository.

    GraphQL reports field-level failure in `errors` and leaves `data` partial or null. Read
    past it and `repository` is `{}`, `pulls` is `[]`, and the walk returns the clean "there
    is no open pull request" answer -- the friendliest possible result, produced by a
    question that was never answered. The flatten then proceeds with no thread check having
    happened and says nothing about it.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = {
        "data": None,
        "errors": [{"message": "Something went wrong while executing your query."}],
    }

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads_problem == (
        "`gh api graphql` returned errors: Something went wrong while executing your query."
    )
    assert [note for note in notes if note.startswith("review threads: NOT CHECKED")]
    assert not [note for note in notes if "none unresolved" in note]


def test_a_page_without_pageinfo_is_not_read_as_a_finished_walk(work, forge):
    """A walk is not finished by a field that never arrived.

    `pageInfo` absent made `hasNextPage` falsy under `or {}`, which fell into the completion
    branch and returned the empty problem string -- the sentence reserved for a walk that
    DID end. The notes then say "none unresolved" about a connection that never claimed to
    have ended, which is the fifth place in this one function where absent evidence was read
    as evidence of absence.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [{"number": 12, "reviewThreads": {"nodes": []}}],
                }
            }
        }
    }

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.threads_problem == "#12 answered without pageInfo"
    assert [note for note in notes if note.startswith("review threads: NOT CHECKED")]
    assert not [note for note in notes if "none unresolved" in note]


def test_a_pull_request_that_stops_answering_midwalk_is_not_read_as_having_none(work, forge):
    """An empty tail is not the end of a clean list.

    The forge handed back page one of #12's threads and then said the branch has no open
    pull request -- merged mid-walk, or a cursor that went bad. Reading that as the
    no-pull-request ANSWER would turn a half-read list into "nothing is anchored here",
    which is the same silence this whole seam exists to refuse.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.pages([thread(author="alice", path="a.py", line=3, body="still open")], CLOSED)

    plan, notes = flatten.Flattener().flatten(cfg(work), orphan_comments=True, dry_run=True)

    assert plan.pull_request == 12
    assert plan.threads_problem == "#12 stopped listing its review threads"
    assert plan.threads == (
        flatten.ReviewThread(author="alice", path="a.py", line="3", excerpt="still open"),
    )
    assert "review threads: none — the branch has no open pull request" not in notes


def test_a_next_page_with_no_cursor_is_a_check_that_did_not_finish(work, forge):
    """Being told there is more and being told where are two facts, not one.

    `endCursor` is nullable in the Cursor Connections spec, so `hasNextPage: true` with a
    null cursor is a shape the API is allowed to hand back: the forge says the list goes on
    and names nowhere to go. Folded into one condition with `hasNextPage` being false, it
    returned the EMPTY problem string -- the codebase's spelling of "checked, fine" -- so a
    pull request whose unresolved thread sat on the page nobody could reach printed "review
    threads on #12: none unresolved" and the rewrite went ahead.

    The page here is deliberately all-resolved, because that is the trap: nothing refuses,
    nothing is listed, and the only thing standing between the operator and a silent orphan
    is whether the sentence says NOT CHECKED.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = Forge.page([thread(resolved=True)], more=True)

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert len(forge.calls) == 1
    assert plan.threads_problem == "#12 stopped listing its review threads"
    assert any(note.startswith("review threads: NOT CHECKED") for note in notes)
    assert "review threads on #12: none unresolved" not in notes


def test_a_branch_with_a_second_open_pull_request_is_a_partial_check(work, forge):
    """One branch, two open pull requests -- which GitHub allows whenever the bases differ.

    `pullRequests(first:1)` took the first node and the whole seam then spoke as though it
    were the branch's: the field is named in the singular, `_collateral` says "the branch has
    no open pull request", and an empty `threads_problem` declares the check complete. The
    second pull request's unresolved threads were never fetched, never refused on and never
    mentioned. Asking for two does not walk the second -- a second connection needs a second
    cursor -- but it makes the partial answer say that it is partial, which is the rule the
    rest of this seam holds to.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.reply = Forge.page([thread(author="alice", path="a.py", line=3, body="open")], pulls=2)

    plan, notes = flatten.Flattener().flatten(cfg(work), orphan_comments=True, dry_run=True)

    assert plan.pull_request == 12
    problem = "feat/thing heads more than one open pull request; only #12's threads were read"
    assert plan.threads_problem == problem
    assert any(note.startswith("review threads: NOT CHECKED") for note in notes)
    # What WAS read is still carried and still listed: a known loss refuses on its own, and
    # the sentence above is what says the rest is unknown.
    assert plan.threads == (
        flatten.ReviewThread(author="alice", path="a.py", line="3", excerpt="open"),
    )


def test_a_connection_that_never_ends_is_reported_rather_than_walked_forever(work, forge):
    """The cursor comes from the other end of a network, so the walk is bounded.

    A connection that keeps saying `hasNextPage` would hang the flatten, and a hang is the
    one failure nobody ever gets a sentence about. The cap stops the walk and says what it
    could not read, which is the same honest degradation every other unread answer gets.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    forge.pages(
        *[
            [thread(author="alice", path="a.py", line=number)]
            for number in range(1, flatten._THREAD_PAGES + 2)
        ]
    )

    plan, _ = flatten.Flattener().flatten(cfg(work), orphan_comments=True, dry_run=True)

    assert len(forge.calls) == flatten._THREAD_PAGES
    assert len(plan.threads) == flatten._THREAD_PAGES
    # The number is what came back, not `pages x per-page`. These pages carry ONE thread
    # each -- `first:100` is an upper bound a server may under-fill -- so a message inferred
    # from the page size would say 2000 about a walk that counted twenty, in the one sentence
    # this seam emits when it admits it could not finish.
    assert plan.threads_problem == (
        f"#12 has more than {flatten._THREAD_PAGES} review threads, which is more of them "
        "than this check reads"
    )


def test_the_issues_and_discussions_the_rewrite_stales_are_reported(work, forge):
    """Reporting, not refusing: nothing can save a timeline entry naming a deleted commit."""
    topic(work)
    commit(
        work,
        "feat: work\n\nSee #12 and the-vibey-project/vibey#7, and\n"
        "https://github.com/the-vibey-project/vibey/discussions/9 — but not abc#3.",
        file="x.txt",
    )
    commit(work, "fix: more\n\nStill about #12.", file="y.txt")

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.references == (
        "#12",
        "the-vibey-project/vibey#7",
        "the-vibey-project/vibey#9",
    )
    staled = [note for note in notes if note.startswith("these timelines")]
    assert staled and "#12, the-vibey-project/vibey#7" in staled[0]


def test_the_merge_subject_github_writes_is_not_read_as_a_reference(work):
    """Reading merges for metadata is right; reading git's own boilerplate as a claim is not.

    GitHub's merge commits are literally `Merge pull request #12 from owner/branch`, so the
    moment merge messages were scanned, every squash-free merge started contributing a `#12`
    that no human referenced -- usually the very pull request being flattened, which the plan
    already names. The note's whole value is that a reader acts on every line of it, so the
    one line git wrote is skipped and the body somebody typed is not.
    """
    name = topic(work)
    commit(work, "feat: the topic's work\n\nCloses #41.", author=ALICE, file="a.txt")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: integration moved on", file="c.txt")
    git(work, "push", "-q", "origin", "develop")
    git(work, "checkout", "-q", name)
    git(
        work,
        "merge",
        "--no-ff",
        "-q",
        "develop",
        "-m",
        "Merge pull request #12 from owner/branch\n\nThis also relates to #77.",
    )

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    # #77 is in the merge body a human wrote, so it survives; #12 is in the subject git
    # wrote, so it was never a reference to begin with.
    assert plan.references == ("#41", "#77")
    staled = [note for note in notes if note.startswith("these timelines")]
    assert staled and "#12" not in staled[0]


def test_a_range_that_references_nothing_reports_nothing(work):
    topic(work)
    commit(work, "feat: work", file="x.txt")

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.references == ()
    assert not [note for note in notes if note.startswith("these timelines")]


# -------------------------------------------------------------------- the refusals


def test_a_detached_head_has_no_branch_to_rewrite(work):
    topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "checkout", "-q", "--detach")

    with pytest.raises(flatten.FlattenError, match="HEAD is detached"):
        flatten.Flattener().plan(cfg(work))


def test_a_dirty_working_tree_is_named_rather_than_absorbed(work):
    """The failure this command replaces staged 12,115 lines of somebody else's revert."""
    topic(work)
    for name in ("one", "two", "three", "four", "five"):
        commit(work, f"feat: {name}", file=f"{name}.txt")
    for name in ("one", "two", "three", "four", "five"):
        (work / f"{name}.txt").write_text("edited\n", encoding="utf-8")

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().plan(cfg(work))

    assert "uncommitted changes" in str(raised.value)
    assert "(+2 more)" in str(raised.value)


def test_a_staged_change_refuses_too(work):
    """Work staged against the old history would silently become a change to the new one."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    (work / "staged.txt").write_text("staged\n", encoding="utf-8")
    git(work, "add", "staged.txt")

    with pytest.raises(flatten.FlattenError, match="staged.txt"):
        flatten.Flattener().plan(cfg(work))


def test_a_working_tree_that_cannot_be_read_is_not_assumed_clean(tmp_path):
    """A bare repository has a branch and no work tree -- `status` fails rather than lies."""
    git(tmp_path, "init", "-q", "--bare", "-b", "feat/bare", "bare.git")

    with pytest.raises(flatten.FlattenError, match="cannot read the working tree"):
        flatten.Flattener().plan(cfg(tmp_path / "bare.git"))


@pytest.mark.parametrize(
    "branch,kind", [("develop", "integration"), ("main", "release")], ids=["integration", "release"]
)
def test_the_permanent_branches_are_never_rewritten(work, branch, kind):
    git(work, "checkout", "-q", "-B", branch)

    with pytest.raises(flatten.FlattenError, match=f"is the {kind} branch"):
        flatten.Flattener().plan(cfg(work))


@pytest.mark.parametrize("branch", ["develop", "main"], ids=["develop", "main"])
def test_a_permanent_branch_this_repository_does_not_configure_is_refused_too(work, branch):
    """The names `reconcile.permanent_branches` denies independently of configuration.

    A second, narrower list here would let flatten rewrite a branch every other mutating
    path in this package refuses to touch, which is the drift the shared list prevents.
    """
    git(work, "checkout", "-q", "-B", branch)
    config = cfg(work, integration_branch="trunk", release_branch="shipped")

    with pytest.raises(flatten.FlattenError, match=f"{branch} is a permanent branch"):
        flatten.Flattener().plan(config)


def test_a_branch_with_nothing_of_its_own_has_nothing_to_flatten(work):
    topic(work, "feat/empty")

    with pytest.raises(flatten.FlattenError, match="no commits origin/develop does not"):
        flatten.Flattener().plan(cfg(work))


def test_a_base_that_cannot_be_resolved_is_refused_not_guessed(work):
    """Through `flatten`, so the fetch gets to find there is no such remote to fetch from."""
    topic(work)
    commit(work, "feat: work", file="x.txt")

    with pytest.raises(flatten.FlattenError, match="cannot resolve upstream/main"):
        flatten.Flattener().flatten(cfg(work), onto="upstream/main")


def test_an_empty_explicit_message_is_refused(work):
    topic(work)
    commit(work, "feat: work", file="x.txt")

    with pytest.raises(flatten.FlattenError, match="--message is empty"):
        flatten.Flattener().plan(cfg(work), message="   \n ")


def test_a_commit_with_no_message_at_all_leaves_nothing_to_compose(work):
    topic(work)
    git(work, "commit", "-q", "--allow-empty", "--allow-empty-message", "-m", "")

    with pytest.raises(flatten.FlattenError, match="the commit message is empty"):
        flatten.Flattener().plan(cfg(work))


def merges_only(work: Path) -> str:
    """A range whose every commit is a merge, which `git merge` itself will not produce.

    Both parents are already in the base, so nothing they carry is in the range -- the
    case where there is no authorship and no message to reuse.
    """
    base = sha(work, "origin/develop")
    parent = sha(work, "origin/develop~1")
    merge = git(
        work, "commit-tree", f"{base}^{{tree}}", "-p", base, "-p", parent, "-m", "Merge"
    ).strip()
    git(work, "update-ref", "refs/heads/feat/merges-only", merge)
    git(work, "checkout", "-q", "feat/merges-only")
    return merge


def test_a_range_of_only_merges_has_no_message_to_reuse(work):
    commit(work, "chore: something to be a second parent", file="p.txt")
    git(work, "push", "-q", "origin", "develop")
    merges_only(work)

    with pytest.raises(flatten.FlattenError, match="only merge commits"):
        flatten.Flattener().plan(cfg(work))


def test_a_range_of_only_merges_flattens_when_a_message_is_given(work):
    commit(work, "chore: something to be a second parent", file="p.txt")
    git(work, "push", "-q", "origin", "develop")
    merges_only(work)
    before = sha(work, "HEAD^{tree}")

    plan, notes = flatten.Flattener().flatten(cfg(work), message="chore: collapse the merge")

    assert plan.coauthors == () and plan.commits == ()
    assert plan.range_size == 1
    assert not [note for note in notes if note.startswith("co-author: ")]
    assert sha(work, "HEAD^{tree}") == before
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_a_range_that_cannot_be_read_is_reported_not_counted_as_empty(work):
    """`plan` resolves the base first, so these two guards have no route through it.

    They are what a repository that breaks BETWEEN the two reads runs into, and a silent
    zero from either would mean flattening a range nobody managed to read.
    """
    topic(work)
    commit(work, "feat: work", file="x.txt")
    flattener, config, missing = flatten.Flattener(), cfg(work), "0" * 40

    with pytest.raises(flatten.FlattenError, match="cannot read"):
        flattener._count(config, missing)
    with pytest.raises(flatten.FlattenError, match="cannot read"):
        flattener._log(config, missing)


# ------------------------------------------------------------ bases, dry runs, pushes


def test_a_local_ref_is_a_base_like_any_other_and_is_not_fetched(work):
    """No remote in the name, so there is nothing to fetch -- and the push still knows where."""
    commit(work, "chore: a local base nobody pushed", file="local.txt")
    git(work, "branch", "-q", "integration-mirror")
    name = topic(work, "feat/onto-local", base="integration-mirror")
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    # Pushed, so the lease is in the command for the reason the lease rule gives and not
    # by accident: what this test is about is that a base with no remote in its name
    # leaves the push with somewhere to go anyway.
    git(work, "push", "-q", "origin", name)

    plan, notes = flatten.Flattener().flatten(cfg(work), onto="integration-mirror")

    assert plan.base == "integration-mirror"
    assert sha(work, "HEAD^") == sha(work, "integration-mirror")
    assert f"  git push --force-with-lease=refs/heads/{name}:{old} origin {name}" in notes


def test_a_dry_run_moves_nothing(work):
    name = a_merged_branch(work)
    before = sha(work)

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert sha(work, f"refs/heads/{name}") == before == plan.old_sha
    assert notes[-1].startswith("dry run: nothing was changed")
    assert notes[0].startswith(f"branch: {name} ({before[:9]})")
    assert f"subject: {plan.subject}" in notes
    assert "flattening 3 commit(s), 2 of them non-merge" in notes


def test_a_dry_run_changes_nothing_including_the_refs_a_fetch_would_move(work, origin):
    """A rehearsal that moves `FETCH_HEAD` is a mutation wearing a rehearsal's label.

    Proved by moving the remote and NOT letting the dry run see it: the plan reads the base
    this clone already has, and the note says that is what it did.
    """
    name = topic(work)
    commit(work, "feat: work", file="w.txt")
    stale = sha(work, "origin/develop")
    git(work, "checkout", "-q", "develop")
    commit(work, "chore: the base moved on", file="landed.txt")
    git(work, "push", "-q", "origin", "develop")
    # The remote moved and this clone has not looked since, which is what a failed or
    # skipped fetch leaves behind.
    git(work, "update-ref", "refs/remotes/origin/develop", stale)
    git(work, "checkout", "-q", name)

    plan, notes = flatten.Flattener().flatten(cfg(work), dry_run=True)

    assert plan.base_sha == stale == sha(work, "origin/develop")
    assert notes[-1] == (
        "dry run: nothing was changed, and origin/develop was not fetched — it is read here "
        "as this clone already has it"
    )


def test_a_fetch_that_fails_refuses_rather_than_planning_on_a_stale_base(work, origin):
    """The ancestry guard is only as good as the ref it is asked about.

    A transient network or auth failure leaves `origin/develop` here at whatever it was
    hours ago. The guard then agrees about a base the remote moved past, the flatten builds
    one commit whose parent omits every integration change since, and the push SUCCEEDS --
    the lease protects the topic branch and has nothing to say about the base. Same
    work-loss class as the ancestry guard, through a door the guard cannot watch.
    """
    topic(work)
    commit(work, "feat: work", file="w.txt")
    before = sha(work)
    shutil.rmtree(origin)

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work))

    assert "could not fetch develop from origin" in str(raised.value)
    assert "stale ref" in str(raised.value) and "--onto" in str(raised.value)
    assert sha(work, "refs/heads/feat/thing") == before
    # Planning alone never fetched, so it is not the thing that refuses here.
    assert flatten.Flattener().plan(cfg(work)).base_sha == sha(work, "origin/develop")


def test_the_lease_pins_what_the_remote_had_and_not_the_local_head(work, origin):
    """The ordinary case, which the pre-rewrite local SHA refused every single time.

    A branch about to be flattened usually carries a commit that was never pushed. The
    remote has therefore never held the local HEAD, so a lease naming it cannot be met and
    `--push` refused every normal flatten -- protection indistinguishable from a blanket no.
    """
    name = topic(work)
    commit(work, "feat: pushed", file="x.txt")
    git(work, "push", "-q", "origin", name)
    pushed = sha(work)
    commit(work, "fix: never pushed", file="y.txt")
    assert sha(work) != pushed

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert notes[-1] == f"pushed {name} to origin with a lease on {pushed[:9]}"


def test_a_remote_branch_this_clone_has_never_fetched_is_leased_on_the_local_sha(work, origin):
    """Nothing here saw it, so nothing here can honestly pin it -- and the push refuses.

    That refusal is the right outcome: it sends the reader to `git fetch`, where the
    alternative is force-pushing over history this clone has never seen.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    # Somebody else's branch of the same name, never fetched here.
    git(origin, "update-ref", f"refs/heads/{name}", git(work, "rev-parse", "develop").strip())
    assert f"refs/remotes/origin/{name}" not in git(work, "for-each-ref", "--format=%(refname)")

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work), push=True)

    assert f"the lease on {old[:9]} was refused" in str(raised.value)
    assert f"  git fetch origin\n  git push --force-with-lease=refs/heads/{name}:" in str(
        raised.value
    )


def test_without_push_the_exact_command_is_printed_rather_than_run(work, origin):
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "origin", name)

    _, notes = flatten.Flattener().flatten(cfg(work))

    assert notes[-2] == "not pushed. Push it with:"
    assert notes[-1] == f"  git push --force-with-lease=refs/heads/{name}:{old} origin {name}"
    # Printed, not run: the remote is still at the pre-rewrite commit.
    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == old


def test_push_sends_the_rewrite_with_a_lease_on_the_pre_rewrite_sha(work, origin):
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "push", "-q", "origin", name)

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert notes[-1].startswith("pushed")


def test_a_refused_lease_leaves_the_local_rewrite_standing_and_names_the_retry(work, origin):
    """A refusal with no way forward is a reason to reach for the hand procedure instead.

    The retry fetches FIRST and leases on what the fetch brought back, so pasting it is a
    decision taken after looking rather than instead of looking -- which is also why the
    printed command is not the one that just refused.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "origin", name)
    # Somebody else's commit reached the remote branch after this clone last saw it.
    git(origin, "update-ref", f"refs/heads/{name}", sha(work, "origin/develop"))

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work), push=True)

    assert "flattened locally but NOT pushed" in str(raised.value)
    assert f"the lease on {old[:9]} was refused" in str(raised.value)
    assert f"`git log origin/{name}`" in str(raised.value)
    assert (
        f"  git fetch origin\n"
        f"  git push --force-with-lease=refs/heads/{name}:$(git rev-parse origin/{name}) "
        f"origin {name}"
    ) in str(raised.value)
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_a_push_that_fails_for_another_reason_is_not_called_a_refused_lease(work, upstream):
    """Verified by deleting the remote: the lease was never reached, let alone refused.

    Reporting this as a refused lease sends the reader looking for somebody else's push
    that never happened -- and past the thing that is actually wrong, which git says. The
    branch's remote is the one deleted and the base's is left alone, because a base that
    cannot be fetched is now its own refusal and would never reach the push at all.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "push", "-q", "-u", "upstream", name)
    shutil.rmtree(upstream)

    with pytest.raises(flatten.FlattenError) as raised:
        flatten.Flattener().flatten(cfg(work), push=True)

    assert "was refused" not in str(raised.value)
    assert "does not appear to be a git repository" in str(raised.value)
    assert f"  git push --force-with-lease=refs/heads/{name}:" in str(raised.value)
    # The local rewrite stands, exactly as the refused-lease case leaves it.
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_a_branch_the_remote_does_not_have_is_pushed_without_a_lease(work, origin):
    """A lease pins a value the remote holds, and a ref that does not exist holds none.

    `--force-with-lease=refs/heads/x:<sha>` against a remote that has never heard of `x`
    cannot be satisfied, so the FIRST push of a branch fails -- and is reported as a
    refused lease, which sends the reader looking for a concurrent push nobody made. The
    ref simply is not there yet, so there is nothing to lease and nothing to protect.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")

    _, notes = flatten.Flattener().flatten(cfg(work))

    assert notes[-1] == f"  git push origin {name}"
    assert f"refs/heads/{name}" not in git(origin, "for-each-ref", "--format=%(refname)")


def test_the_first_push_creates_the_branch_rather_than_failing_a_lease(work, origin):
    """Pasting the printed command and passing `--push` are the same push, so both work."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert notes[-1] == (
        f"pushed {name} to origin; the remote had no such branch, so no lease was needed"
    )


def test_a_branch_the_remote_already_has_keeps_its_lease(work, origin):
    """The protection is the whole point of the push, and a first push is not a reason to drop it."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "origin", name)

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert notes[-1] == f"pushed {name} to origin with a lease on {old[:9]}"
    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)


def test_a_remote_that_cannot_be_asked_keeps_the_lease(work, upstream):
    """The two mistakes are not the same size, so an unanswered question gets the careful answer.

    A lease that was not needed costs a push that refuses and can be retried. A lease
    wrongly dropped costs somebody else's commits.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "-u", "upstream", name)
    shutil.rmtree(upstream)

    _, notes = flatten.Flattener().flatten(cfg(work))

    assert notes[-1] == f"  git push --force-with-lease=refs/heads/{name}:{old} upstream {name}"


@pytest.fixture
def upstream(tmp_path: Path, work: Path) -> Path:
    """A second bare remote, so "the base's remote" and "the branch's remote" can differ.

    It starts where `origin` does, which is what lets it be an `--onto` without also being
    a divergence: these tests are about where the push LANDS, and a base that had to be
    merged first would be about something else.
    """
    git(tmp_path, "init", "-q", "--bare", "-b", "develop", "upstream.git")
    path = tmp_path / "upstream.git"
    git(work, "remote", "add", "upstream", str(path))
    git(work, "push", "-q", "upstream", "develop")
    git(work, "fetch", "-q", "upstream")
    return path


def test_an_onto_on_another_remote_is_fetched_from_there_and_not_pushed_to(work, origin, upstream):
    """The base's remote and the branch's are two questions, and this is both answers.

    Answering the second with the first pushes somebody's topic branch to somebody else's
    fork -- which no note mentioned, because the note did not name a destination either.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "-u", "origin", name)

    _, notes = flatten.Flattener().flatten(cfg(work), onto="upstream/develop", push=True)

    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert f"refs/heads/{name}" not in git(upstream, "for-each-ref", "--format=%(refname)")
    assert notes[-1] == f"pushed {name} to origin with a lease on {old[:9]}"


def test_a_branch_that_tracks_another_remote_is_pushed_to_that_one(work, origin, upstream):
    """The other direction, so the answer is the branch's remote and not the word "origin"."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    old = sha(work)
    git(work, "push", "-q", "-u", "upstream", name)

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert git(upstream, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert f"refs/heads/{name}" not in git(origin, "for-each-ref", "--format=%(refname)")
    assert notes[-1] == f"pushed {name} to upstream with a lease on {old[:9]}"


def test_a_branch_with_no_upstream_at_all_falls_back_to_origin(work, origin, upstream):
    """The common case, not the edge one: a branch is flattened before its first push too.

    `upstream` exists and is even where `--onto` points, so `origin` here is the fallback
    doing its job rather than the only remote in the repository.
    """
    name = topic(work)
    commit(work, "feat: work", file="x.txt")

    _, notes = flatten.Flattener().flatten(cfg(work), onto="upstream/develop", push=True)

    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert f"refs/heads/{name}" not in git(upstream, "for-each-ref", "--format=%(refname)")
    assert notes[-1] == (
        f"pushed {name} to origin; the remote had no such branch, so no lease was needed"
    )


def test_a_branch_tracking_a_local_branch_falls_back_to_origin_too(work, origin):
    """`branch.<name>.remote = .` is how git spells a local upstream, and it is no target."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "branch", "-q", "--set-upstream-to=develop", name)

    _, notes = flatten.Flattener().flatten(cfg(work), push=True)

    assert git(work, "config", "--get", f"branch.{name}.remote").strip() == "."
    assert git(origin, "rev-parse", f"refs/heads/{name}").strip() == sha(work)
    assert notes[-1] == (
        f"pushed {name} to origin; the remote had no such branch, so no lease was needed"
    )


# ----------------------------------------------------------------------- the signature


def signer(tmp_path: Path) -> Path:
    """A stub signing program: the one line git's gpg interface looks for, and armour.

    The crypto is git's business and a real key is not this suite's to have. What is
    under test is that `-S` reaches `commit-tree` at all, which the `gpgsig` header on
    the object proves and nothing short of a real invocation does.
    """
    path = tmp_path / "fake-gpg.sh"
    path.write_text(
        "#!/bin/sh\n"
        'echo "[GNUPG:] SIG_CREATED " >&2\n'
        'echo "-----BEGIN PGP SIGNATURE-----"\n'
        'echo ""\n'
        'echo "ZmFrZQ=="\n'
        'echo "-----END PGP SIGNATURE-----"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def test_a_repository_that_signs_its_commits_gets_a_signed_flattened_commit(work, tmp_path):
    """`git commit` reads `commit.gpgsign`; `commit-tree` is plumbing and does not."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "config", "gpg.program", str(signer(tmp_path)))
    git(work, "config", "user.signingkey", "FAKEKEY")
    git(work, "config", "commit.gpgsign", "true")

    flatten.Flattener().flatten(cfg(work))

    assert "\ngpgsig " in git(work, "cat-file", "commit", "HEAD")


def test_a_repository_that_does_not_sign_gets_an_unsigned_one(work, tmp_path):
    """The flag is the repository's decision, never this command's."""
    topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "config", "gpg.program", str(signer(tmp_path)))
    git(work, "config", "commit.gpgsign", "false")

    flatten.Flattener().flatten(cfg(work))

    assert "gpgsig" not in git(work, "cat-file", "commit", "HEAD")


# ------------------------------------------------------------------------ the guards


class WrongTreeFlattener(flatten.Flattener):
    """A flatten whose builder returns a commit carrying the BASE's tree, not the branch's.

    `commit-tree` makes tree equality true by construction, so breaking the construction
    deliberately is the only way to watch the assertion in `_move` do its job.
    """

    def _build(self, cfg: GhConfig, plan: flatten.FlattenPlan) -> str:
        return git(
            cfg.root,
            "commit-tree",
            f"{plan.base_sha}^{{tree}}",
            "-p",
            plan.base_sha,
            "-m",
            "chore: a commit of the wrong tree",
        ).strip()


class RacingFlattener(flatten.Flattener):
    """A flatten whose branch gains a commit between the build and the update.

    The race the pinned `update-ref` exists for, made deterministic.
    """

    def _build(self, cfg: GhConfig, plan: flatten.FlattenPlan) -> str:
        new = super()._build(cfg, plan)
        commit(cfg.root, "chore: somebody else's commit")
        return new


class BogusTreeFlattener(flatten.Flattener):
    """A flatten that plans a tree the repository does not have, so `commit-tree` fails."""

    def plan(
        self,
        cfg: GhConfig,
        *,
        onto: str | None = None,
        message: str | None = None,
        orphan_comments: bool = False,
    ) -> flatten.FlattenPlan:
        planned = super().plan(cfg, onto=onto, message=message, orphan_comments=orphan_comments)
        return replace(planned, tree="0" * 40)


class LeaselessFlattener(flatten.Flattener):
    """A flatten whose push carries no lease although the remote does have the branch.

    The one window a leaseless first push has, made deterministic. `ls-remote` answers
    about the remote at the moment it is asked and the push is a second moment; somebody
    creating the branch in between leaves an ordinary `[rejected]` with no lease behind
    it, which must not be read back as a lease that was refused.
    """

    @staticmethod
    def _push_command(cfg: GhConfig, plan: flatten.FlattenPlan, remote: str) -> tuple[str, ...]:
        command = flatten.Flattener._push_command(cfg, plan, remote)
        return tuple(arg for arg in command if not arg.startswith("--force-with-lease="))


def test_the_ref_does_not_move_when_the_built_tree_is_not_the_branchs(work):
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    before = sha(work)

    with pytest.raises(flatten.FlattenError, match="refusing to move"):
        WrongTreeFlattener().flatten(cfg(work))

    assert sha(work, f"refs/heads/{name}") == before


def test_a_branch_that_moves_mid_flatten_is_left_alone(work):
    name = topic(work)
    commit(work, "feat: work", file="x.txt")

    with pytest.raises(flatten.FlattenError, match="moved while it was being flattened"):
        RacingFlattener().flatten(cfg(work))

    assert git(work, "log", "-1", "--format=%s", f"refs/heads/{name}").strip() == (
        "chore: somebody else's commit"
    )


def test_a_commit_that_cannot_be_built_moves_nothing(work):
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    before = sha(work)

    with pytest.raises(flatten.FlattenError, match="could not build the flattened commit"):
        BogusTreeFlattener().flatten(cfg(work))

    assert sha(work, f"refs/heads/{name}") == before


def test_a_leaseless_push_that_is_rejected_is_not_called_a_refused_lease(work, origin):
    """There was no lease, so the one sentence that must not be printed is that one."""
    name = topic(work)
    commit(work, "feat: work", file="x.txt")
    git(work, "push", "-q", "origin", name)

    with pytest.raises(flatten.FlattenError) as raised:
        LeaselessFlattener().flatten(cfg(work), push=True)

    # Not the word anywhere -- pytest's own tmpdir is named after this test -- but the
    # sentence, which is the thing that would be false.
    assert "the lease on" not in str(raised.value) and "was refused" not in str(raised.value)
    assert "flattened locally but NOT pushed" in str(raised.value)
    assert "[rejected]" in str(raised.value)
    assert f"  git push origin {name}" in str(raised.value)
    # The local rewrite stands, exactly as every other failed push leaves it.
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


# --------------------------------------------------------------------- the command


def test_the_cli_dry_runs_then_rewrites(work, monkeypatch, capsys):
    name = a_merged_branch(work)
    # Untracked, and deliberately so: it stops `find_root` walking past the fixture, and a
    # flatten that refused over an untracked file would refuse over everyone's build output.
    (work / ".vibey-gh.toml").write_text("# test\n", encoding="utf-8")
    monkeypatch.chdir(work)
    before = sha(work)

    assert cli_main(["flatten", "--dry-run"]) == 0
    assert f"{name} would be flattened onto origin/develop" in capsys.readouterr().out
    assert sha(work) == before

    assert cli_main(["flatten"]) == 0
    out = capsys.readouterr().out
    assert f"{name} flattened onto origin/develop" in out
    assert "not pushed. Push it with:" in out
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_the_cli_reports_a_refusal_on_stderr_and_exits_non_zero(work, monkeypatch, capsys):
    (work / ".vibey-gh.toml").write_text("# test\n", encoding="utf-8")
    monkeypatch.chdir(work)

    assert cli_main(["flatten"]) == 1
    assert "vibey-gh: develop is the integration branch" in capsys.readouterr().err


def test_the_cli_refuses_unresolved_threads_and_orphans_them_only_when_told_to(
    work, forge, monkeypatch, capsys
):
    """The flag is the whole opt-in, so the command is what has to prove it reaches through."""
    (work / ".vibey-gh.toml").write_text("# test\n", encoding="utf-8")
    topic(work)
    commit(work, "feat: work", file="x.txt")
    monkeypatch.chdir(work)
    forge.pull_request(thread(author="copilot", path="a.py", line=3, body="wrong order"))

    assert cli_main(["flatten"]) == 1
    refusal = capsys.readouterr().err
    assert "1 unresolved review thread(s) on #12" in refusal
    assert "copilot a.py:3 — wrong order" in refusal

    assert cli_main(["flatten", "--orphan-comments"]) == 0
    out = capsys.readouterr().out
    assert "orphaning 1 unresolved review thread(s) on #12:" in out
    assert git(work, "rev-list", "--count", "origin/develop..HEAD").strip() == "1"


def test_the_flattener_is_the_seam_it_declares():
    assert isinstance(flatten.Flattener(), FlattenerInterface)
