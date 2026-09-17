# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rebuild a branch as one commit on its base, with the message and trailers re-derived.

Two gates send a branch here, and neither has another remedy. A commit authored through
the GitHub web UI or API never meets `.githooks/commit-msg`, so it carries no provenance
trailer and the Provenance gate refuses it — `check --apply` cannot repair that, because
it writes file headers, not commit trailers. And the Conventional Commits normaliser
refuses outright any range containing a merge commit, which is every range that took the
integration branch into a topic branch. Both answers are the same one: rewrite the
history.

The guard is TREE EQUALITY BY CONSTRUCTION. The new commit is built with `git commit-tree`
from the branch's EXISTING tree object, so nothing is staged, nothing is reset, and the
working tree is never read — there is no step at which content can enter or leave. That
matters because the hand procedure this replaces has a live failure mode: `reset --mixed`
followed by `add -A`, in a worktree created before a merge that deleted files, stages
those files back and silently reverts a merged pull request inside an unrelated commit.
It was caught by reading a `--stat` and noticing the line count was too large, which is
not a control. The invariant is asserted as well as constructed — the new commit's tree
must equal the old HEAD's, or the ref does not move — because an invariant nobody checks
is a comment.

Tree equality is necessary and NOT sufficient, which is the second guard. `commit-tree
<HEAD's tree> -p <base>` asserts that HEAD's tree is the whole of the base plus this
branch, and when the base carries a commit the branch never merged that assertion is a
lie the tree check cannot see — the tree is correctly HEAD's, and HEAD's tree is exactly
what is wrong, because it never had those changes to lose. The one commit would delete
them. So the base must be an ancestor of HEAD, and a base that is not one is refused
naming the remedy that keeps both sides: merge the base in first, then flatten.

A rewrite does not only move content. THREE things outside this repository are anchored to
the commits it replaces, and all three were destroyed in silence until they were not.
Inline review comments are anchored to commit SHAs, so a force-push marks every unresolved
thread "outdated" and detaches it from the code it was about — that one is REFUSED by
default and takes `orphan_comments` to say yes to on purpose, because 31 review comments
were posted across five pull requests and 26 of them merged unaddressed. Issue-closing
keywords live in commit messages and the trailer stripper ate them, so they are collected
from the whole range and put back, the same treatment the breaking footers get and for the
same reason: nothing else re-derives them. And every `#N` the range mentions leaves a
"referenced this in commit <sha>" entry on that issue's or discussion's timeline for a sha
that is about to stop existing — nothing can save those, so they are REPORTED rather than
refused on.

The thread check talks to the forge, and a check that could not be made must never read as
a check that passed. `gh` missing, unauthenticated or failing is reported as exactly that,
and the flatten proceeds. Knowing threads exist and orphaning them silently is the
dangerous case; not knowing is a smaller and different one, and the two get different
sentences rather than one comfortable one.

Planning changes nothing and fetching does, so the fetch belongs to the rewrite and not to
the plan: a dry run that moved `FETCH_HEAD` and the remote-tracking refs would be a
mutation wearing a rehearsal's label. It reads the base as this clone already has it, and
says so. The rewrite itself fetches first and REFUSES when that fetch fails, because the
ancestry guard above is only as good as the ref it is asked about — a stale `origin/<base>`
makes it agree about a base the remote has long since moved past, and the lease on the push
protects the topic branch only, so the wrong parent goes up without a murmur.

Both refs are pinned: `update-ref` takes the old LOCAL value, and the push takes a lease on
the value this clone last saw the REMOTE holding — its remote-tracking ref, which is the
thing somebody else's push makes stale — so anything that landed in between refuses rather
than being clobbered. Pinning the pre-rewrite local SHA instead reads like the same
protection and is not: a branch about to be flattened usually carries a commit that was
never pushed, the remote has therefore never held that value, and the lease refuses the
ORDINARY case every time. A branch the remote has never heard of is the one exception, and
not a loosening: there is no remote value to pin, nothing a lease could protect, and a
lease named anyway cannot be satisfied — so the FIRST push of a branch would fail, and fail
wearing the one label it has not earned. WHICH remote is asked of the branch and not of the
base: the base's remote is the one fetched from, and `--onto upstream/main` must not
thereby send a topic branch to somebody else's fork.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any

from vibey_gh import fingerprints, github_state, reconcile
from vibey_gh.config import GhConfig

__all__ = ["COAUTHOR_KEY", "FlattenError", "FlattenPlan", "Flattener", "ReviewThread"]

# Git's own spelling is case-insensitive and GitHub's attribution is too; this is the
# spelling the forge renders, so it is the one written.
COAUTHOR_KEY = "Co-Authored-By"
# `token: value` on one line, which is all git recognises as a trailer. Used to find the
# block at the end of a message — never to judge the subject, which matches this shape
# too and is decided by position instead.
_TRAILER_LINE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:(?:\s|$)")
# A footer nothing re-derives, so it is collected from the whole range and put back rather
# than stripped with the rest — the same treatment a declared `Co-Authored-By:` gets, for
# the same reason. Both spellings Conventional Commits allows, because a range writes both
# and they assert the same thing.
_BREAKING_LINE = re.compile(r"^BREAKING[ -]CHANGE:")
# GitHub's issue-closing keywords, every one it honours, in each tense it accepts. A footer
# is the whole line — keyword, an optional colon, one reference — because a closing keyword
# IS a footer and a footer states one thing; `This fixes #12 badly` is prose about an issue,
# not a promise to close it, and the `^` anchor is what tells them apart.
_CLOSING_LINE = re.compile(
    r"^[ \t]*(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)[ \t]*:?[ \t]+"
    r"(?P<reference>(?:[\w.-]+/[\w.-]+)?#\d+)[ \t]*$",
    re.IGNORECASE,
)
# A cross-reference to an issue or a discussion, in the three spellings GitHub links: a URL,
# `owner/repo#12`, and a bare `#12`. Each one puts a "referenced this in commit <sha>" entry
# on that timeline, which is what the rewrite makes point at nothing. The lookbehind is what
# keeps `abc#12` out: a reference is a word of its own, not the tail of one.
_REFERENCE = re.compile(
    r"https://github\.com/(?P<owner>[\w.-]+/[\w.-]+)/(?:issues|discussions)/(?P<id>\d+)"
    r"|(?<![\w/])(?P<repository>[\w.-]+/[\w.-]+)?#(?P<number>\d+)\b"
)
# The unresolved review threads on the branch's open pull request, with just enough of the
# first comment to make a refusal actionable: who wrote it, where, and what it said. `line`
# is null on a thread GitHub already considers outdated, so `originalLine` answers for it.
_THREADS_QUERY = """
query($owner:String!,$name:String!,$branch:String!){
  repository(owner:$owner,name:$name){
    pullRequests(headRefName:$branch,states:OPEN,first:1){
      nodes{
        number
        reviewThreads(first:100){
          nodes{
            isResolved
            comments(first:1){nodes{path line originalLine body author{login}}}
          }
        }
      }
    }
  }
}
"""
# How git spells a lease it would not take. Anything else that fails a push — an
# unreachable remote, a declined hook, no credentials — is a different fact about the
# world and gets reported as itself. `[remote rejected]` is deliberately not matched:
# that is the server refusing, not the lease going stale.
_LEASE_REFUSED = re.compile(r"stale info|\[rejected\]")


class FlattenError(RuntimeError):
    """A flatten that will not proceed. Every refusal reaches the caller as one of these."""


@dataclass(frozen=True)
class ReviewThread:
    """One unresolved inline review thread, reduced to what a refusal has to name.

    A thread is unactionable as a number. Somebody deciding whether to orphan four of them
    needs to know whose they are and what they said, and the four fields here are the ones
    that fit on a line each.
    """

    author: str
    path: str
    # A string, not an int: an already-outdated thread has no current line and answers with
    # the line it was written against, and a thread on a deleted file has neither.
    line: str
    excerpt: str


@dataclass(frozen=True)
class FlattenPlan:
    """The rewrite as data, decided before anything moves and printable on its own."""

    branch: str
    base: str
    base_sha: str
    old_sha: str
    tree: str
    # Every commit in the range, then the non-merge ones the message and authors come
    # from. Reported as two numbers because a merge carries no authorship of its own and
    # a range can be all merges, which is a thing a reader should see rather than infer.
    range_size: int
    commits: tuple[str, ...]
    coauthors: tuple[str, ...]
    message: str
    # The issues and discussions the range's commits reference, which keep timeline entries
    # naming commits the rewrite deletes. Reported, never refused on: nothing can save them.
    references: tuple[str, ...] = ()
    # The branch's open pull request, its unresolved threads, and — when the forge could not
    # be asked at all — why. `threads_problem` empty is the ONLY thing that means the check
    # was made; `pull_request is None` with no problem means there is no open pull request.
    pull_request: int | None = None
    threads: tuple[ReviewThread, ...] = ()
    threads_problem: str = ""

    @property
    def subject(self) -> str:
        return self.message.splitlines()[0]


class Flattener:
    """Implements `FlattenerInterface` against the repository at `cfg.root`."""

    def plan(
        self,
        cfg: GhConfig,
        *,
        onto: str | None = None,
        message: str | None = None,
        orphan_comments: bool = False,
    ) -> FlattenPlan:
        branch = self._branch(cfg)
        self._refuse_protected(cfg, branch)
        self._refuse_dirty(cfg)
        base = self._base(cfg, onto)
        base_sha = self._resolve(cfg, base)
        old_sha = self._resolve(cfg, "HEAD")
        tree = self._resolve(cfg, "HEAD", kind="tree")
        range_size = self._count(cfg, base_sha)
        if range_size == 0:
            raise FlattenError(
                f"{branch} has no commits {base} does not; there is nothing to flatten"
            )
        self._refuse_unmerged_base(cfg, branch, base, base_sha)
        records = self._log(cfg, base_sha)
        # Asked last of the local refusals and before the message is composed: there is no
        # point asking the forge about a branch that has nothing to flatten, and no point
        # composing a message for a rewrite that is about to be refused.
        number, threads, problem = self._review_threads(branch)
        if threads and not orphan_comments:
            self._refuse_orphaning(branch, number, threads)
        coauthors = self._coauthors(records)
        return FlattenPlan(
            branch=branch,
            base=base,
            base_sha=base_sha,
            old_sha=old_sha,
            tree=tree,
            range_size=range_size,
            commits=tuple(sha for sha, _name, _email, _body in records),
            coauthors=coauthors,
            message=self._compose(
                cfg,
                self._body(branch, message, records),
                coauthors,
                footers=self._breaking_footers(records),
                closings=self._closing_footers(records),
                marked=self._breaking_subject(records),
            ),
            references=self._references(records),
            pull_request=number,
            threads=threads,
            threads_problem=problem,
        )

    def flatten(
        self,
        cfg: GhConfig,
        *,
        onto: str | None = None,
        message: str | None = None,
        push: bool = False,
        dry_run: bool = False,
        orphan_comments: bool = False,
    ) -> tuple[FlattenPlan, tuple[str, ...]]:
        # Before the plan, because the plan reads the base and a stale base is what the
        # ancestry guard cannot see through — and not at all on a dry run, which promises
        # to change nothing and would otherwise move `FETCH_HEAD` to keep that promise.
        if not dry_run:
            self._fetch(cfg, self._base(cfg, onto))
        plan = self.plan(cfg, onto=onto, message=message, orphan_comments=orphan_comments)
        notes = [
            f"branch: {plan.branch} ({plan.old_sha[:9]})",
            f"base: {plan.base} ({plan.base_sha[:9]})",
            f"flattening {plan.range_size} commit(s), {len(plan.commits)} of them non-merge",
            f"subject: {plan.subject}",
        ]
        notes += [f"co-author: {author}" for author in plan.coauthors]
        notes += self._collateral(plan)
        if dry_run:
            notes.append(
                f"dry run: nothing was changed, and {plan.base} was not fetched — it is read "
                "here as this clone already has it"
            )
            return plan, tuple(notes)

        new = self._build(cfg, plan)
        self._move(cfg, plan, new)
        notes.append(f"{plan.branch} is now {new[:9]}, one commit on {plan.base_sha[:9]}")
        # Decided once, so the command printed here is the command `--push` runs, lease
        # and all. A printed command that behaves differently when pasted is worse than
        # no printed command, because the reader has no reason to doubt it.
        remote = self._push_remote(cfg, plan.branch)
        command = self._push_command(cfg, plan, remote)
        if push:
            self._push(cfg, plan, remote, command)
            notes.append(self._pushed(plan, remote, command))
        else:
            notes.append("not pushed. Push it with:")
            notes.append(f"  {' '.join(command)}")
        return plan, tuple(notes)

    # -- the refusals -------------------------------------------------------------

    def _branch(self, cfg: GhConfig) -> str:
        """The branch being flattened. A detached HEAD has none, so there is nothing to move."""
        run = self._git(cfg, "symbolic-ref", "--quiet", "--short", "HEAD")
        branch = run.stdout.strip()
        if run.returncode != 0 or not branch:
            raise FlattenError(
                "HEAD is detached, so there is no branch to rewrite. Check out the branch first."
            )
        return branch

    @staticmethod
    def _refuse_protected(cfg: GhConfig, branch: str) -> None:
        """Refuse every branch this package already calls permanent.

        `reconcile.permanent_branches` is where the repository decides which refs may
        never be force-updated: the configured integration and release branches, plus the
        literal `develop` and `main` denied independently as defence. Asking it is the
        point. A second, narrower definition of "branch you must not rewrite" would drift
        from that one, and the drift would be a branch flatten rewrites that every other
        mutating path in this package refuses to touch.
        """
        if branch not in reconcile.permanent_branches(cfg):
            return
        if branch == cfg.integration_branch:
            role = "the integration branch"
        elif branch == cfg.release_branch:
            role = "the release branch"
        else:
            # Named by the shared list rather than by this repository's configuration —
            # it is nobody's configured role here, and saying otherwise would be a guess.
            role = "a permanent branch"
        raise FlattenError(f"{branch} is {role}; flatten rewrites history and will not touch it")

    def _refuse_unmerged_base(self, cfg: GhConfig, branch: str, base: str, base_sha: str) -> None:
        """Refuse a base the branch has never merged, because flattening would revert it.

        This is the work-loss bug, and it is not hypothetical. The new commit is
        `commit-tree <HEAD's tree> -p <base>`: HEAD's tree becomes the whole content of
        the base plus the branch. Everything the base gained since the branch was cut is
        absent from that tree, so the one commit DELETES it — a merged pull request
        reverted inside an unrelated commit. The tree-equality invariant agrees happily,
        because the tree is correctly HEAD's; HEAD's tree is the thing that is wrong.

        The hand procedure this command replaces did exactly that on 2026-09-17: a
        `reset --mixed` and an `add -A` in a worktree that predated a merge staged 12,115
        lines of five deleted lockfiles back, caught only by eyeballing a `--stat`. There
        is no `--stat` to eyeball here, so the ancestry is checked in the code instead.

        The refusal names a remedy because there is a good one, and it loses nothing:
        merging the base into the branch makes it an ancestor and keeps both sides.
        """
        if self._git(cfg, "merge-base", "--is-ancestor", base_sha, "HEAD").returncode == 0:
            return
        raise FlattenError(
            f"{base} is not an ancestor of {branch}: it carries commits this branch has "
            f"never merged. Flattening would build one commit from {branch}'s tree onto "
            f"{base_sha[:9]}, presenting that tree as the whole of both — silently "
            f"REVERTING everything {base} gained. Merge it in first, then flatten; that "
            "makes it an ancestor and keeps both sides:\n"
            f"  git merge {base}\n"
            f"  vibey-gh flatten --onto {base}"
        )

    @staticmethod
    def _refuse_orphaning(
        branch: str, number: int | None, threads: tuple[ReviewThread, ...]
    ) -> None:
        """Refuse a rewrite that would detach unresolved review threads from their code.

        An inline review comment is anchored to a commit SHA. Replace that commit and
        GitHub marks the thread "outdated": it collapses, it stops appearing against the
        code it was about, and nobody is prompted to answer it again. That is how 26 of 31
        review comments across five pull requests came to be merged unaddressed.

        The threads are LISTED rather than counted, because a refusal a reader cannot act
        on is a refusal they will route around. Author, file, line and the comment's first
        line is enough to decide each one without leaving the terminal.
        """
        listed = "\n".join(
            f"  {thread.author} {thread.path}:{thread.line} — {thread.excerpt}"
            for thread in threads
        )
        raise FlattenError(
            f"{branch} has {len(threads)} unresolved review thread(s) on #{number}. They are "
            f"anchored to the commits this rewrite replaces, so the force-push marks every "
            f"one of them outdated and detaches it from the code it was about:\n{listed}\n"
            "Resolve them first — or pass --orphan-comments to flatten anyway, knowing the "
            "threads survive only as outdated comments nobody is prompted to read."
        )

    @staticmethod
    def _collateral(plan: FlattenPlan) -> list[str]:
        """What the rewrite costs outside this repository, said out loud before it happens.

        The first sentence is about the forge, and its job is to keep "could not look" and
        "nothing there" apart. A seam that reports an unasked question as a clean answer is
        worse than one that says nothing, because a clean answer is acted on.
        """
        notes: list[str] = []
        if plan.threads_problem:
            notes.append(
                f"review threads: NOT CHECKED — {plan.threads_problem}. Any unresolved thread "
                "on an open pull request will be orphaned by the rewrite."
            )
        elif plan.pull_request is None:
            notes.append("review threads: none — the branch has no open pull request")
        elif plan.threads:
            notes.append(
                f"orphaning {len(plan.threads)} unresolved review thread(s) on "
                f"#{plan.pull_request}:"
            )
            notes += [
                f"  {thread.author} {thread.path}:{thread.line} — {thread.excerpt}"
                for thread in plan.threads
            ]
        else:
            notes.append(f"review threads on #{plan.pull_request}: none unresolved")
        if plan.references:
            notes.append(
                'these timelines say "referenced this in commit" about commits the rewrite '
                f"deletes: {', '.join(plan.references)}"
            )
        return notes

    def _refuse_dirty(self, cfg: GhConfig) -> None:
        """Refuse a dirty tracked tree or index.

        Nothing here reads the working tree, so uncommitted work is not at risk of being
        absorbed — but it is at risk of being MISREAD. Work staged against the old history
        would be committed onto the new one by the next ordinary commit, silently changing
        what it is a change to. Untracked files are excluded: they cannot reach a commit
        built from HEAD's tree object, and refusing on build output would refuse everyone.
        """
        run = self._git(cfg, "status", "--porcelain", "--untracked-files=no")
        if run.returncode != 0:
            raise FlattenError(f"cannot read the working tree: {run.stderr.strip()}")
        dirty = [line for line in run.stdout.splitlines() if line.strip()]
        if dirty:
            shown = ", ".join(line[3:] for line in dirty[:3])
            more = f" (+{len(dirty) - 3} more)" if len(dirty) > 3 else ""
            raise FlattenError(
                f"the working tree or index has uncommitted changes: {shown}{more}. "
                "Commit or stash them; flatten will not decide for you."
            )

    # -- reading the range --------------------------------------------------------

    @staticmethod
    def _base(cfg: GhConfig, onto: str | None) -> str:
        """The base: `--onto` when given, else the integration branch on `origin`.

        Asked in one place because two callers need it before the plan exists — the plan
        itself, and the fetch that has to happen before the plan reads the ref.
        """
        return onto or f"origin/{cfg.integration_branch}"

    def _fetch(self, cfg: GhConfig, base: str) -> None:
        """Update the remote-tracking ref `base` names, when it names one, or refuse.

        The remote is read from the ref rather than assumed to be `origin`, so
        `--onto upstream/main` works without a second configuration key.

        A FAILED fetch is fatal, and treating it as a shrug was the bug. The ancestry guard
        is the whole defence against this command reverting merged work, and it is only as
        good as the ref it is asked about: a transient network or auth failure leaves a
        stale `origin/<base>` on disk, the guard agrees happily with a base the remote moved
        past hours ago, and the flatten builds one commit whose parent omits every
        integration change since. That then force-pushes SUCCESSFULLY, because the lease
        protects the topic branch and has nothing to say about the base. Same work-loss
        class as the ancestry guard itself, through a door the guard cannot watch.
        """
        remote, _, branch = base.partition("/")
        if not branch:
            return
        if remote not in self._git(cfg, "remote").stdout.split():
            return
        run = self._git(cfg, "fetch", "--quiet", remote, branch)
        if run.returncode != 0:
            raise FlattenError(
                f"could not fetch {branch} from {remote}, so {base} here may be behind what "
                f"the remote holds — and the ancestry check that keeps this rewrite from "
                f"reverting merged work would be deciding on a stale ref. Fix the fetch and "
                f"retry, or name a base you already have with --onto:\n{run.stderr.strip()}"
            )

    def _resolve(self, cfg: GhConfig, rev: str, *, kind: str = "commit") -> str:
        run = self._git(cfg, "rev-parse", "--verify", "--quiet", f"{rev}^{{{kind}}}")
        sha = run.stdout.strip()
        if run.returncode != 0 or not sha:
            raise FlattenError(f"cannot resolve {rev} to a {kind}; fetch it or name another --onto")
        return sha

    def _count(self, cfg: GhConfig, base_sha: str) -> int:
        """Every commit in the range, merges included — the test for "anything to flatten"."""
        run = self._git(cfg, "rev-list", "--count", f"{base_sha}..HEAD")
        if run.returncode != 0:
            raise FlattenError(f"cannot read {base_sha}..HEAD: {run.stderr.strip()}")
        return int(run.stdout.strip() or 0)

    def _log(self, cfg: GhConfig, base_sha: str) -> list[tuple[str, str, str, str]]:
        """`(sha, author name, author email, message)` for each non-merge commit, oldest first.

        One call rather than three: the message of the first commit and the authors of all
        of them are the same read, and a second read is a second chance to disagree.
        """
        run = self._git(
            cfg,
            "log",
            "--reverse",
            "--no-merges",
            "--format=%H%x1f%an%x1f%ae%x1f%B%x1e",
            f"{base_sha}..HEAD",
        )
        if run.returncode != 0:
            raise FlattenError(f"cannot read {base_sha}..HEAD: {run.stderr.strip()}")
        records: list[tuple[str, str, str, str]] = []
        for raw in run.stdout.split("\x1e"):
            record = raw.strip("\n")
            if not record:
                continue
            sha, name, email, body = (record.split("\x1f", 3) + ["", "", ""])[:4]
            records.append((sha, name, email, body))
        return records

    # -- what the forge has anchored to the range ---------------------------------

    @staticmethod
    def _review_threads(branch: str) -> tuple[int | None, tuple[ReviewThread, ...], str]:
        """The open pull request's unresolved threads, or why they could not be asked about.

        Three answers, never two: the forge answered and there is no open pull request
        (`None`, no threads, no problem); it answered and here are the threads; or it could
        not be asked, which is the third and is carried as a PROBLEM STRING rather than
        collapsed into an empty list. A seam that reads a missing `gh`, an unauthenticated
        runner or a rate-limited token as "no unresolved threads" reports "could not look"
        as "nothing there" — and here that difference is a force-push somebody would not
        have made.

        `gh` is reached through `github_state`, which is how every other forge call in this
        package is made and therefore how this one is too. It resolves the repository the
        way `gh` always does — `GH_REPO`, else the working directory — so a flatten run from
        inside the worktree being rewritten asks about that worktree's repository.
        """
        try:
            owner, _, name = github_state.repository().partition("/")
            payload: Any = github_state.gh_json(
                "api",
                "graphql",
                # `--raw-field`, not `--field`: these are `String!` variables, and `--field`
                # would coerce a branch or repository named in digits into a number that the
                # API then rejects for the wrong reason.
                "--raw-field",
                f"query={_THREADS_QUERY}",
                "--raw-field",
                f"owner={owner}",
                "--raw-field",
                f"name={name}",
                "--raw-field",
                f"branch={branch}",
            )
        except FileNotFoundError:
            return None, (), "the GitHub CLI (`gh`) is not installed"
        except (OSError, RuntimeError, ValueError, LookupError, TypeError) as exc:
            # Wide on purpose. `gh` exiting non-zero raises `RuntimeError` and unparseable
            # output raises `ValueError`, but the repository lookup also INDEXES the JSON it
            # gets back, so a response shaped differently raises from the subscript instead.
            # Every one of those is the same fact — the forge could not be asked — and none
            # of them is a reason to take the flatten down with a traceback.
            return None, (), f"`gh api graphql` failed: {str(exc).strip() or type(exc).__name__}"
        repository = ((payload or {}).get("data") or {}).get("repository") or {}
        pulls = (repository.get("pullRequests") or {}).get("nodes") or []
        if not pulls:
            # An answer, not an unknown: the forge was asked and there is no open pull
            # request, so nothing of its is anchored to the commits about to be replaced.
            return None, (), ""
        pull = pulls[0]
        threads = tuple(
            Flattener._thread(node)
            for node in ((pull.get("reviewThreads") or {}).get("nodes") or [])
            if not node.get("isResolved")
        )
        return int(pull.get("number") or 0), threads, ""

    @staticmethod
    def _thread(node: Any) -> ReviewThread:
        """One thread as its first comment, with a fallback for every field that is nullable.

        All four are: the author of a deleted account is null, a thread already outdated has
        no current `line`, and an empty comment body is a thing the API will hand back. A
        missing field must not take the refusal down with it — a thread nobody can name is
        still a thread somebody is about to orphan.
        """
        comments = (node.get("comments") or {}).get("nodes") or [{}]
        first = comments[0]
        body = (first.get("body") or "").strip().splitlines() or [""]
        return ReviewThread(
            author=(first.get("author") or {}).get("login") or "someone",
            path=first.get("path") or "?",
            line=str(first.get("line") or first.get("originalLine") or "?"),
            excerpt=body[0],
        )

    @staticmethod
    def _references(records: list[tuple[str, str, str, str]]) -> tuple[str, ...]:
        """Every issue and discussion the range's commits reference, first-seen order kept.

        Not a refusal and not repairable. GitHub writes "referenced this in commit <sha>"
        onto the timeline of anything a pushed commit mentions, and the rewrite is what
        makes that sha stop existing: the entry stays, pointing at nothing. There is no
        trailer to carry and no keyword to preserve, so the only honest thing to do is name
        them and let the operator decide whether the rewrite is worth it.

        Read from the commit MESSAGES rather than asked of the forge, because the messages
        are what created those entries — and because the answer is then the same offline, on
        a dry run, and on a repository `gh` cannot reach.
        """
        seen: dict[str, str] = {}
        for _sha, _name, _email, body in records:
            for match in _REFERENCE.finditer(body):
                repository = match.group("repository") or match.group("owner")
                number = match.group("number") or match.group("id")
                written = f"{repository}#{number}" if repository else f"#{number}"
                seen.setdefault(written.casefold(), written)
        return tuple(seen.values())

    # -- the message --------------------------------------------------------------

    @staticmethod
    def _body(branch: str, message: str | None, records: list[tuple[str, str, str, str]]) -> str:
        """`--message` when given, else the first non-merge commit's, stripped of trailers.

        Stripping is what makes the trailers re-derivable: the co-authors and the
        provenance trailer are computed from the whole range, and a trailer carried over
        from one commit of it would be an assertion nobody made about the other commits.
        `BREAKING-CHANGE:` and a declared `Co-Authored-By:` are the two exceptions, and
        both are read from the WHOLE range afterwards — by `_breaking_footers` and
        `_coauthors` — rather than rescued from this one message.
        """
        if message is not None:
            if not message.strip():
                raise FlattenError("--message is empty; give it a subject or omit it")
            return message
        if not records:
            raise FlattenError(
                f"{branch} has only merge commits in this range, so there is no message to "
                "reuse. Pass --message."
            )
        return Flattener._strip_trailers(records[0][3])

    @staticmethod
    def _strip_trailers(message: str) -> str:
        """The message without its trailing trailer paragraphs.

        The subject is never a trailer. Everything stripped here is recomputed from the
        WHOLE range afterwards — the co-authors, the provenance trailer, and the
        breaking-change footers — because a trailer carried over from this ONE commit
        would be an assertion nobody made about the others. Stripping a `Co-Authored-By:`
        is not dropping it: `_coauthors` reads it back off every commit in the range,
        which is the only way the credit in a LATER commit survives at all.

        The breaking footers used to be rescued in this method, from this message alone,
        and that was the loss: a `BREAKING-CHANGE:` written in the range's third commit
        was never in this message to rescue. `_breaking_footers` reads every commit
        instead, so this one only has to strip.
        """
        lines = message.rstrip().splitlines()
        while True:
            block = Flattener._trailer_block("\n".join(lines))
            if not block:
                break
            del lines[len(lines) - len(block) :]
            while lines and not lines[-1].strip():
                lines.pop()
        return "\n".join(lines)

    @staticmethod
    def _trailer_block(message: str) -> list[str]:
        """The message's trailer lines, or none when its last paragraph is not a block.

        Git recognises trailers in the FINAL PARAGRAPH and nowhere else, so this is where
        every question about them is answered from — what `_strip_trailers` removes, what
        `_existing` searches, and what `_compose` joins rather than reopening. Spelling that
        rule once is the point: three copies of "is this a trailer block" drift, and the
        drift shows up as a provenance trailer written twice or not at all.

        A one-paragraph message has no trailer block however trailer-shaped its single line
        is, because that line is the subject.
        """
        lines = message.rstrip().splitlines()
        start = Flattener._last_paragraph(lines)
        if start <= 0 or not all(_TRAILER_LINE.match(line) for line in lines[start:]):
            return []
        return lines[start:]

    @staticmethod
    def _last_paragraph(lines: list[str]) -> int:
        """Index of the first line of the final paragraph, or -1 when there are no lines.

        Zero means that paragraph IS the subject: a one-paragraph message has no trailer
        block, however trailer-shaped its single line happens to look.
        """
        if not lines:
            return -1
        start = len(lines)
        while start > 0 and lines[start - 1].strip():
            start -= 1
        return start

    @staticmethod
    def _trailer_lines(message: str) -> list[str]:
        """Every trailer line in the message's trailing RUN of trailer paragraphs.

        Git recognises trailers in one final paragraph, and `_trailer_block` answers that
        question exactly. But this repository's own `.githooks/commit-msg` appends the
        provenance trailer as a paragraph of its OWN, so an ordinary commit here ends in
        TWO trailer paragraphs with a blank line between them:

            Co-Authored-By: Someone <someone@example.com>

            Made-With: ...

        A reader that stops at the last paragraph therefore sees the provenance trailer and
        MISSES every `Co-Authored-By:` above it — which silently drops exactly the credit
        this command exists to preserve, on the commits it was written for. That is not
        hypothetical: it is what the first real flatten of this branch did, and nothing
        failed, because dropping a co-author looks like a commit that simply had none.

        `_strip_trailers` already walks the whole run, one paragraph per pass, which is why
        stripping was never wrong. This is that same walk for the readers, so the two cannot
        disagree about where a message's trailers end.
        """
        lines = message.rstrip().splitlines()
        found: list[str] = []
        while True:
            block = Flattener._trailer_block("\n".join(lines))
            if not block:
                return found
            found = block + found
            del lines[len(lines) - len(block) :]
            while lines and not lines[-1].strip():
                lines.pop()

    @staticmethod
    def _coauthors(records: list[tuple[str, str, str, str]]) -> tuple[str, ...]:
        """Everyone the range credits — its authors and the co-authors it declares.

        This is the whole reason a flatten is not a loss: absorbing a review bot's commit
        into someone else's would erase that it contributed at all.

        Authorship is only half of how credit is written, and in this repository it is the
        quieter half: the convention here is to name a collaborator in a `Co-Authored-By:`
        trailer while the git author stays the operator. Deriving credit from authorship
        alone would therefore drop every collaborator the range names — the command's own
        headline promise, defeated on the commits it was written for.

        So a declared co-author is collected exactly the way `_breaking_footers` collects
        the other footer nothing re-derives: from EVERY non-merge commit, because the
        commit that names a collaborator is rarely the commit whose message is reused.
        """
        seen: dict[str, str] = {}
        for _sha, name, email, body in records:
            # The commit's own author first, then whoever that commit credits: first-seen
            # order is reading order, and a name is kept in the case it was first written
            # in, however the later mentions of it are spelled.
            for author in (f"{name} <{email}>", *Flattener._existing(body, COAUTHOR_KEY)):
                seen.setdefault(author.casefold(), author)
        return tuple(seen.values())

    @staticmethod
    def _breaking_lines(text: str) -> list[tuple[str, str]]:
        """`(identity, line)` for every breaking-change footer in `text`.

        The identity is what the footer ASSERTS, casefolded — not the line it is written
        on. Conventional Commits allows two spellings of the key, a range writes both, and
        `BREAKING-CHANGE: the old flag is gone` and `BREAKING CHANGE: the old flag is
        gone` are one break said twice, not two breaks.
        """
        found: list[tuple[str, str]] = []
        for line in text.splitlines():
            match = _BREAKING_LINE.match(line)
            if match is not None:
                found.append((line[match.end() :].strip().casefold(), line.rstrip()))
        return found

    @staticmethod
    def _breaking_footers(records: list[tuple[str, str, str, str]]) -> dict[str, str]:
        """Every distinct breaking-change footer in the range, first-seen order kept.

        From EVERY non-merge commit, not from the first one alone. A range routinely
        breaks something in a later commit than the one whose subject gets reused, and a
        footer read only from the first is a footer silently dropped — which turns a MAJOR
        release into a minor one, in the direction nobody notices until it is published
        and somebody's build breaks against a version that promised not to.

        Nothing else in the flattened message records it. Every other trailer here is
        re-derived from the range; this one is derivable from nothing, so it is collected
        instead — which is the same principle, applied to the same whole range.
        """
        seen: dict[str, str] = {}
        for _sha, _name, _email, body in records:
            for key, line in Flattener._breaking_lines(body):
                seen.setdefault(key, line)
        return seen

    @staticmethod
    def _closing_lines(text: str) -> list[tuple[str, str]]:
        """`(reference, line)` for every issue-closing keyword footer in `text`.

        The identity is the REFERENCE, casefolded — `Closes #12` and `Fixes #12` are one
        issue promised twice, not two issues, and `owner/repo#12` is a different issue from
        `#12` because it is a different repository's.
        """
        found: list[tuple[str, str]] = []
        for line in text.splitlines():
            match = _CLOSING_LINE.match(line)
            if match is not None:
                found.append((match.group("reference").casefold(), line.strip()))
        return found

    @staticmethod
    def _closing_footers(records: list[tuple[str, str, str, str]]) -> dict[str, str]:
        """Every distinct issue-closing keyword in the range, first-seen order kept.

        This was a live data-loss bug and not a hypothetical one. `Closes #12` is not
        re-derivable from anything — not from authorship, not from the tree, not from the
        branch name — and the flatten had two ways to drop it. `Closes: #12` is trailer
        shaped, so `_strip_trailers` removed it with the rest; and either spelling written
        in the range's THIRD commit was never in the first commit's message to survive at
        all. So it is collected from EVERY non-merge commit and put back, which is exactly
        what `_breaking_footers` does with the other footer nothing re-derives.

        The verb is kept as the author wrote it and nothing is invented: a range that never
        promised to close an issue does not start promising it here, because a keyword this
        command added would close somebody's issue on a merge nobody meant to.
        """
        seen: dict[str, str] = {}
        for _sha, _name, _email, body in records:
            for reference, line in Flattener._closing_lines(body):
                seen.setdefault(reference, line)
        return seen

    @staticmethod
    def _marks_breaking(subject: str) -> bool:
        """Whether `subject` declares itself breaking with Conventional Commits' `!`.

        The marker means that only where the spec puts it — immediately before the colon
        of a conventional subject — so conformance is asked of `fingerprints`, which owns
        that shape for this package, rather than spelled a second time here and left to
        drift from it.
        """
        prefix = subject.partition(":")[0]
        return fingerprints.conventional_subject(subject) and prefix.endswith("!")

    @staticmethod
    def _breaking_subject(records: list[tuple[str, str, str, str]]) -> bool:
        """Whether any commit in the range declared itself breaking with `!`.

        The other half of the loss, and the half no footer covers. `feat!: drop the old
        flag` says breaking in its SUBJECT and is complete without a footer — the spec
        treats either as sufficient. Exactly one subject survives a flatten, so when that
        commit is not the one whose subject is reused, its `!` leaves with the subject and
        nothing in the flattened commit says the range breaks anything at all.
        """
        return any(
            Flattener._marks_breaking(body.partition("\n")[0])
            for _sha, _name, _email, body in records
        )

    @staticmethod
    def _marked(text: str) -> str:
        """`text` with `!` on its subject, when the subject is a conventional one without it.

        This is the chosen remedy for a `!` on a commit whose subject is not the one
        reused, and it is RE-MARKING rather than a synthesised footer on purpose.
        Conventional Commits treats either as breaking, so either would do the job; only
        one of them is honest. A footer needs a description, and the discarded commit
        wrote none — inventing one, or pasting that commit's subject in as though it
        described the break, puts words in an author's mouth. The `!` asserts exactly what
        the source asserted and not a word more: this range breaks something. It also
        lands where both a reader of `git log --oneline` and a release tool already look,
        which a footer under the trailer block does not.

        A subject that is not conventional cannot carry the marker in the place the spec
        gives it, so it is left alone rather than mangled into something that only looks
        like one.
        """
        subject, separator, rest = text.partition("\n")
        if Flattener._marks_breaking(subject) or not fingerprints.conventional_subject(subject):
            return text
        prefix, colon, description = subject.partition(":")
        return f"{prefix}!{colon}{description}{separator}{rest}"

    def _compose(
        self,
        cfg: GhConfig,
        body: str,
        coauthors: tuple[str, ...],
        *,
        footers: dict[str, str],
        closings: dict[str, str],
        marked: bool,
    ) -> str:
        """The finished message: conventional subject, closing keywords, footers, trailers.

        The subject is normalised because the Conventional Commits gate is half of why
        this command exists, and `normalize_commit_message` is the same helper the hook
        and `vibey-gh conventional-message` apply — it is a no-op on a subject that
        already conforms. The trailer TEXT is `cfg.trailer`, the one `vibey-gh trailer`
        prints and `.githooks/commit-msg` appends; nothing here spells it a second time.

        The breaking footers go in ahead of the co-authors and only where the message does
        not already assert them, so a footer the reused body kept in place is not repeated
        underneath itself in the other spelling. The closing keywords get a PARAGRAPH OF
        THEIR OWN above the trailer block, and that placement is load-bearing rather than
        decorative: `Closes #12` is not `token: value`, so a trailer block containing one
        stops being a trailer block — and the next flatten of that message would find no
        provenance trailer in it and add a second one.
        """
        text = fingerprints.normalize_commit_message(body).rstrip()
        if not text:
            raise FlattenError("the commit message is empty; pass --message")
        if marked:
            text = self._marked(text)
        said = {key for key, _line in self._breaking_lines(text)}
        additions = [line for key, line in footers.items() if key not in said]
        present = {value.casefold() for value in self._existing(text, COAUTHOR_KEY)}
        additions += [
            f"{COAUTHOR_KEY}: {author}" for author in coauthors if author.casefold() not in present
        ]
        if not self._existing(text, cfg.trailer_key):
            additions.append(cfg.trailer)
        promised = {reference for reference, _line in self._closing_lines(text)}
        keywords = [line for reference, line in closings.items() if reference not in promised]
        if not additions and not keywords:
            # Nothing to add, so nothing is rearranged either: a message that was already
            # complete comes back byte for byte, rather than reflowed into an equivalent one.
            return text + "\n"
        lines = text.splitlines()
        block = self._trailer_block(text)
        body_lines = lines[: len(lines) - len(block)]
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        paragraphs = ["\n".join(body_lines)]
        if keywords:
            paragraphs.append("\n".join(keywords))
        # Never empty by the time control reaches here: something was added, and an empty
        # `additions` can only mean the message already carried the provenance trailer —
        # which `_existing` finds in a trailer block and nowhere else, so `block` has it.
        paragraphs.append("\n".join([*block, *additions]))
        return "\n\n".join(paragraphs) + "\n"

    @staticmethod
    def _existing(message: str, key: str) -> list[str]:
        """The values of every `key:` trailer in the message's TRAILER BLOCK, however cased.

        The trailer paragraphs and not the whole message, because git's trailers live at
        the end and a line elsewhere is prose that happens to have a colon in it. The
        trailing RUN of them rather than only the last, because this repository's hook
        writes the provenance trailer as its own paragraph — see `_trailer_lines`.
        Searching everything made two silent bugs: a body sentence opening `Made-With:` —
        which is exactly how one would write about this tool — suppressed the provenance
        trailer the commit needs to pass its own gate, and a body line quoting
        `Co-Authored-By:` suppressed the real attribution for whoever it named.
        """
        pattern = re.compile(rf"^{re.escape(key)}:[ \t]*(\S.*)$", re.IGNORECASE)
        found = (pattern.match(line) for line in Flattener._trailer_lines(message))
        return [match.group(1).strip() for match in found if match is not None]

    # -- the rewrite --------------------------------------------------------------

    def _build(self, cfg: GhConfig, plan: FlattenPlan) -> str:
        """The new commit: the branch's own tree, the base as its only parent.

        The message goes in on stdin, so it never lands on disk — there is no temporary
        file to clean up on failure and none to leak into the worktree being rewritten.
        """
        run = self._git(
            cfg,
            "commit-tree",
            *self._signing(cfg),
            plan.tree,
            "-p",
            plan.base_sha,
            stdin=plan.message,
        )
        new = run.stdout.strip()
        if run.returncode != 0 or not new:
            raise FlattenError(f"could not build the flattened commit: {run.stderr.strip()}")
        return new

    def _signing(self, cfg: GhConfig) -> tuple[str, ...]:
        """`-S` when the repository signs its commits, because `commit-tree` will not.

        `git commit` reads `commit.gpgsign`; `commit-tree` is plumbing and does not, so a
        repository that signs would get a silently unsigned commit here — and find out
        from a ruleset rejecting the push, after the local history was already rewritten.
        `--type=bool` is what normalises git's `yes`/`on`/`1` spellings, so this compares
        against one value rather than keeping a second list of what truth looks like.
        """
        run = self._git(cfg, "config", "--get", "--type=bool", "commit.gpgsign")
        return ("-S",) if run.stdout.strip() == "true" else ()

    def _move(self, cfg: GhConfig, plan: FlattenPlan, new: str) -> None:
        """Point the branch at the new commit, having proved the content did not move.

        `commit-tree` was handed the tree, so this can only fail if the plan and the
        commit disagree about which tree that was — which is exactly the case where
        moving the ref would lose work, so it is checked rather than assumed.
        """
        built = self._resolve(cfg, new, kind="tree")
        if built != plan.tree:
            raise FlattenError(
                f"refusing to move {plan.branch}: the flattened commit's tree {built[:9]} is "
                f"not {plan.branch}'s tree {plan.tree[:9]}"
            )
        run = self._git(cfg, "update-ref", f"refs/heads/{plan.branch}", new, plan.old_sha)
        if run.returncode != 0:
            raise FlattenError(
                f"{plan.branch} moved while it was being flattened, so it was left alone: "
                f"{run.stderr.strip()}"
            )

    @staticmethod
    def _push_remote(cfg: GhConfig, branch: str) -> str:
        """The remote `branch` is pushed to: the one it tracks, else `origin`.

        Where the base comes FROM and where the branch goes TO are two different
        questions, and answering the second with the first is a bug wearing somebody
        else's name: `--onto upstream/main` would have pushed this topic branch to
        `upstream`. The base's remote is what gets FETCHED, and that is all it decides.

        A branch that has never been pushed has no upstream at all — the common case here
        rather than the edge one, since a branch is flattened before its first push at
        least as often as after it — so the fallback is `origin`, which is where a bare
        `git push` would have aimed too.

        `branch.<name>.remote` is read rather than `@{upstream}` parsed, because the
        config holds the remote's NAME as a value while the upstream is one string with a
        slash in it: splitting `origin/feat/a/b` back into a remote and a branch is a
        guess about which slash is the seam. A value that is not a remote — `.`, which is
        how a branch tracking a LOCAL branch is spelled — is not a push target either, so
        it takes the fallback along with the absent one.
        """
        tracked = Flattener._git(cfg, "config", "--get", f"branch.{branch}.remote").stdout.strip()
        remotes = Flattener._git(cfg, "remote").stdout.split()
        return tracked if tracked in remotes else "origin"

    @staticmethod
    def _push_command(cfg: GhConfig, plan: FlattenPlan, remote: str) -> tuple[str, ...]:
        """The push, as the exact argv it would be run with, so it can be printed or run."""
        return ("git", "push", *Flattener._lease(cfg, remote, plan), remote, plan.branch)

    @staticmethod
    def _tracked(cfg: GhConfig, remote: str, branch: str) -> str:
        """What this clone last saw `remote` holding for `branch`, or "" if it never has."""
        run = Flattener._git(
            cfg, "rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}^{{commit}}"
        )
        return run.stdout.strip() if run.returncode == 0 else ""

    @staticmethod
    def _lease(cfg: GhConfig, remote: str, plan: FlattenPlan) -> tuple[str, ...]:
        """The lease on what the remote last held — unless the remote has nothing to lease.

        A lease exists to detect SOMEBODY ELSE's push, and the value that detects one is the
        remote-tracking ref: what this clone last saw the remote holding. The pre-rewrite
        LOCAL sha looks like the same number and is not, whenever the branch carries a
        commit that was never pushed — which is the ordinary state of a branch about to be
        flattened, not an edge case. The remote has never held that value, so the lease
        cannot be met, so `--push` refused every normal flatten and the protection was
        indistinguishable from a blanket no.

        A lease names the value the remote ref must still hold, and a ref that does not
        exist holds nothing. `--force-with-lease=refs/heads/x:<sha>` against a remote that
        has never heard of `x` therefore cannot be satisfied, so the FIRST push of a
        branch fails — and fails as a refused lease, which is the one thing it is not. It
        tells the reader somebody else pushed. Nobody did; the ref simply is not there
        yet. With nothing on the remote to protect there is nothing to lease, and the push
        is an ordinary create, which git will still refuse if the branch appears meanwhile.

        The question is put to the REMOTE, not answered by pushing and reading the
        wreckage: `ls-remote` is the remote's actual state, whereas a failed push is
        equally consistent with a dozen other facts about the world. And when the remote
        cannot be asked at all — unreachable, no credentials — the lease STAYS. The two
        mistakes are not the same size: a lease that was not needed costs a push that
        refuses and can be retried, and a lease wrongly dropped costs somebody else's
        commits. So the unanswered question gets the careful answer.

        The same asymmetry decides the last case: the remote has the branch and this clone
        has never fetched it, so there is no value it can honestly pin. The pre-rewrite
        local sha goes in, the remote will not match it, and the push refuses — which sends
        the reader to `git fetch`, and is the right outcome, because the alternative is
        force-pushing over history this clone has never seen.
        """
        run = Flattener._git(cfg, "ls-remote", "--heads", remote, f"refs/heads/{plan.branch}")
        if run.returncode == 0 and not run.stdout.strip():
            return ()
        seen = Flattener._tracked(cfg, remote, plan.branch)
        return (f"--force-with-lease=refs/heads/{plan.branch}:{seen or plan.old_sha}",)

    @staticmethod
    def _leased(command: tuple[str, ...]) -> str:
        """The SHA `command`'s lease pins, or "" when it carries none.

        One accessor for the one fact both the success note and the failure need, and it
        reads the value off the command rather than recomputing it — a note that names a
        different SHA from the one the push actually leased is a note that lies.
        """
        for argument in command:
            if argument.startswith("--force-with-lease="):
                return argument.rpartition(":")[2]
        return ""

    @staticmethod
    def _pushed(plan: FlattenPlan, remote: str, command: tuple[str, ...]) -> str:
        """What the push did, which is not the same sentence when there was no lease to take.

        The destination is named because it is a choice the reader did not make and cannot
        otherwise see — the branch's own upstream, or `origin` when it has none. A push
        that reports no destination is how a push to the wrong remote stays invisible;
        this sentence is the one that would have shown it.
        """
        pinned = Flattener._leased(command)
        if pinned:
            return f"pushed {plan.branch} to {remote} with a lease on {pinned[:9]}"
        return (
            f"pushed {plan.branch} to {remote}; the remote had no such branch, so no lease "
            "was needed"
        )

    def _push(
        self, cfg: GhConfig, plan: FlattenPlan, remote: str, command: tuple[str, ...]
    ) -> None:
        """Send the rewrite, or say plainly that the local rewrite stands and the push did not.

        The lease is what this clone last saw on the remote, so a refusal means the remote
        branch is no longer there — somebody pushed to it since. Either way the remote holds
        commits this flatten did not see, and naming a new lease is a judgement about
        someone else's work, not a retry: the retry printed below fetches FIRST and leases
        on what the fetch brought back, so pasting it is a decision taken after looking
        rather than instead of looking.

        Every OTHER way a push fails is a different fact about the world and is reported
        as itself: calling an unreachable remote a refused lease sends the reader looking
        for a concurrent push nobody made, and past the thing that is actually wrong. A
        push carrying NO lease is the same error told the same way — `[rejected]` after a
        leaseless create means the branch appeared on the remote between the check and the
        push, and a story about a lease that was never named is not a truer one for being
        shorter.
        """
        run = self._git(cfg, *command[1:])
        if run.returncode == 0:
            return
        stderr = run.stderr.strip()
        pinned = self._leased(command)
        if not pinned or not _LEASE_REFUSED.search(stderr):
            # An unreachable remote, a declined hook, no credentials. Naming a refused
            # lease here would send the reader looking for a concurrent push that never
            # happened, so git's own words go through instead of a story about them.
            raise FlattenError(
                f"{plan.branch} was flattened locally but NOT pushed. The local rewrite "
                f"stands; git said:\n{stderr}\nRetry the push with:\n  {' '.join(command)}"
            )
        raise FlattenError(
            f"{plan.branch} was flattened locally but NOT pushed: the lease on "
            f"{pinned[:9]} was refused, so {remote}/{plan.branch} is no longer at the commit "
            f"this clone last saw it at — somebody pushed to it. Compare it with "
            f"`git log {remote}/{plan.branch}` before deciding; the local rewrite stands "
            f"either way.\n{stderr}\nIf you still want the rewrite after looking, fetch what "
            f"the remote has and lease on that:\n"
            f"  git fetch {remote}\n"
            f"  git push --force-with-lease=refs/heads/{plan.branch}:"
            f"$(git rev-parse {remote}/{plan.branch}) {remote} {plan.branch}"
        )

    @staticmethod
    def _git(
        cfg: GhConfig, *args: str, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cfg.root,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
