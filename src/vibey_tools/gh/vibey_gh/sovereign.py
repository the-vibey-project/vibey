# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sovereign readiness (doctrine 8.a): is the free path actually able to take this?

Doctrine 8.a makes the 100% sovereign path the *preferred* way to run, not the
fallback of last resort. Acting on that safely needs one fact a workflow cannot
otherwise learn: whether a runner carrying the sovereign label is online **now**.

Without that fact the compliant-looking change is a trap, and it is worth naming
because it has already cost this project a production outage in another costume.
`review-sovereign` runs on a self-hosted runner. Disabled, the job *skips*, and a
skipped job counts as completed. Enabled with no runner online, it **queues** — not
failed, not cancelled, simply pending. The job that publishes the required
`PR evaluate / gate` and `PR review / gate` checks need it and the review gate is guarded by `always()`, which waits for
needs to *complete*. So switching the sovereign lane on by default, with no probe,
blocks every pull request permanently and silently, with no red check to point at.

**The workflow cannot ask GitHub**: the runners API needs `administration: read`, which
`GITHUB_TOKEN` cannot be granted at all. Depending on a privileged forge API to discover
whether one's *own* machine is up would also invert 8.a — it makes the sovereign lane's
availability contingent on a counterparty's capability, which is precisely what doctrine
10.a warns about.

So the machine says so itself, in the plainest artifact both sides already share: a
git ref. A timer on the operator's machine calls `beat()`, which pushes an empty
commit to a ref outside `refs/heads/` — no branch, nothing for doctrine 9.a's tidy
pass to find. Any job with ordinary `contents: read` fetches that ref and reads its
timestamp. Fresh means ready.

**A heartbeat is a claim, so it is published only when it is true** (ADR-0059). The machine
that publishes it CAN ask GitHub, with the runner's own credential, and does: `beat()` takes
a `LaneReadinessInterface` and pushes nothing unless the runner is registered and online and
the model endpoint answers. A read that fails is a refusal, never an assumed "up". Withheld,
the heartbeat goes stale on its own and the gate falls back honestly. The old publisher said
"up" whenever its supervisor had a live process, which included the thirty seconds of every
failing restart cycle.

**And it is only ever pushed through a gate.** `beat()` pushes from the repository it is
given -- the timer's own clone (`vibey_gh.heartbeat_clone`) -- and withholds, saying why,
when that repository or its pre-push gate is missing. A refused push is reported with the
tail of what git said, credentials scrubbed, so the record carries its own evidence.

The failure direction is deliberate throughout: anything unreadable, unparseable, or stale
reports **not ready**. A missing heartbeat costs a sovereign review; a false positive costs
every gate in the repository.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.interfaces.push_scope_interface import PushScopeInterface
from vibey_gh.interfaces.sovereign_interface import (
    LaneReadinessInterface,
    LaneStateInterface,
    SovereignHeartbeatInterface,
)
from vibey_gh.push_scope import NO_REPLACE_OBJECTS, PushScope

__all__ = ["TIMED_OUT", "Readiness", "SovereignHeartbeat", "beat", "probe"]

# The exit status `_run` reports for a git that did not finish in time, as timeout(1) does:
# distinct from every status git itself exits with, so a hung push reads as one.
TIMED_OUT = 124
# How long any one git command may take before it is abandoned.
_TIMEOUT_SECONDS = 60

# Credentials a git error line could echo back: a URL's userinfo, and the shapes GitHub
# gives its tokens. Scrubbed before any of it reaches a reason or a record.
_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
_TOKEN = re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})\b")
_COLOUR = re.compile(r"\x1b\[[0-9;]*m")


@dataclass(frozen=True)
class Readiness:
    """Whether the sovereign lane may be scheduled, and why."""

    ready: bool
    reason: str
    age_seconds: int | None = None


GitSeam = Callable[..., tuple[int, str]]


def _run(*cmd: str, cwd: str | None = None, stderr: bool = False) -> tuple[int, str]:
    """(exit status, stripped standard output -- or, with `stderr`, standard error).

    A module function rather than a method: it is the one place this module starts a
    process, and the seam its tests have always replaced. The class calls it by name at
    call time, so replacing it here reaches every instance. `stderr` is how a push is run:
    git says why it refused a push on standard error and nowhere else. A git that did not
    finish in time is `TIMED_OUT`; one that could not be started is 127.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS, check=False, cwd=cwd
        )
    except subprocess.TimeoutExpired:
        return TIMED_OUT, ""
    except OSError:
        return 127, ""
    return proc.returncode, (proc.stderr if stderr else proc.stdout).strip()


class SovereignHeartbeat(SovereignHeartbeatInterface):
    """Publishes and reads the heartbeat on one ref of one remote.

    `cwd` is the repository the heartbeat is pushed from: the timer's own clone. `git` is
    the seam: it takes the arguments after `git` (and `stderr=True` for the push) and
    returns the exit status and the stripped output. `scope` judges whether the value the
    ref already holds is itself a heartbeat; by default it asks through the same seam.
    """

    def __init__(
        self,
        ref: str,
        *,
        remote: str = "origin",
        cwd: str | None = None,
        git: GitSeam | None = None,
        scope: PushScopeInterface | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._ref = ref
        self._remote = remote
        self._cwd = cwd
        self._git_seam = git
        self._scope = scope or PushScope(git=lambda args: self._git(*args))
        self._clock = clock

    def _git(self, *args: str, stderr: bool = False) -> tuple[int, str]:
        if self._git_seam is not None:
            return self._git_seam(*args, stderr=stderr)
        return _run("git", *args, cwd=self._cwd, stderr=stderr)

    def _now(self) -> float:
        return self._clock() if self._clock is not None else time.time()

    # --- publishing -----------------------------------------------------------------------

    def beat(self, readiness: LaneReadinessInterface) -> Readiness:
        """Publish a heartbeat, but only through a gate and only when the lane can serve.

        The repository it is pushed from is checked first: it must exist and hold an
        executable pre-push hook where git will run one, or nothing is pushed and the
        reason says which is missing. Then `readiness` is asked, and a lane that cannot
        serve publishes nothing: the refusal comes back with its reason. That is the whole
        point of the heartbeat -- the gate schedules the sovereign review on its word, so a
        word given when no runner can take the job queues that job forever. A readiness
        that raises is a refusal too: this never raises.

        The heartbeat itself is an empty commit on a ref outside `refs/heads/`, so it is
        never a branch a human or a tidy pass has to reason about. It replaces the previous
        one with a **compare-and-swap**, not a bare force: the ref's current value is read,
        confirmed to be a heartbeat (the empty tree, no parents, nothing else carried, read
        as the push would send it), and named as the lease
        (`--force-with-lease=<ref>:<value>`). Only that exact value is ever replaced -- a
        concurrent write, or anything on the ref that is not a heartbeat, is refused and
        left as it was. Sub-doctrine 12.d allows no unattended act that cannot be undone;
        replacing a commit that carries nothing, and only the one that was read, is not one.

        There is no `--no-verify`. The push goes through the repository's own pre-push gate,
        and the gate lets it through by its own rule (`vibey_gh.push_scope`): the declared
        heartbeat ref, the empty tree with no parents, nothing else. The gate is applying
        its scope, not being skipped -- a heartbeat that carried a single file, or rode
        beside a branch, would be judged in full. A push the gate or the remote refuses
        comes back with the tail of what git said, credentials scrubbed out of it.
        """
        problem = self._gate_problem()
        if problem:
            return Readiness(False, f"heartbeat withheld: {problem}")
        try:
            state: LaneStateInterface = readiness.assess()
        except Exception as exc:  # noqa: BLE001 - a readiness that raises is a refusal
            return Readiness(
                False,
                "heartbeat withheld: the lane's readiness could not be read"
                f" ({type(exc).__name__}: {self._evidence(str(exc))})",
            )
        if not state.serving:
            return Readiness(False, f"heartbeat withheld: {state.reason}")
        code, tree = self._git("hash-object", "-t", "tree", "/dev/null")
        if code != 0 or not tree:
            return Readiness(
                False, "could not write the empty tree object; is this a git repository?"
            )
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._now()))
        code, commit = self._git("commit-tree", tree, "-m", f"sovereign heartbeat {stamp}")
        if code != 0 or not commit:
            return Readiness(False, "could not create the heartbeat commit")
        lease, problem = self._lease()
        if problem:
            return Readiness(False, problem)
        code, said = self._git(
            "push",
            f"--force-with-lease={self._ref}:{lease}",
            self._remote,
            f"{commit}:{self._ref}",
            stderr=True,
        )
        if code != 0:
            return Readiness(False, self._push_refused(code, said))
        return Readiness(True, f"heartbeat published to {self._ref} at {stamp}: {state.reason}", 0)

    def _gate_problem(self) -> str:
        """Why no heartbeat may be pushed from this repository, or "": it must exist, and git
        must find an executable pre-push hook for it (`core.hooksPath` honoured)."""
        where = self._cwd or "the current directory"
        if self._cwd is not None and not Path(self._cwd).is_dir():
            return (
                f"the repository the heartbeat is pushed from, {self._cwd}, does not exist"
                " (vibey-gh heartbeat install creates it)"
            )
        code, hook = self._git(
            "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-push"
        )
        if code != 0 or not hook:
            return (
                f"{where} is not a git repository the heartbeat can be pushed from"
                " (vibey-gh heartbeat install creates one)"
            )
        if not Path(hook).is_file() or not os.access(hook, os.X_OK):
            return (
                f"{where} has no executable pre-push gate at {hook}, and a heartbeat is only"
                " ever pushed through one (vibey-gh heartbeat install writes it)"
            )
        return ""

    def _push_refused(self, code: int, said: str) -> str:
        if code == TIMED_OUT:
            return (
                f"the push to {self._remote} {self._ref} timed out after {_TIMEOUT_SECONDS}s"
                f" (exit {TIMED_OUT}); whether it landed is unknown until the next beat reads"
                " the ref"
            )
        heard = self._evidence(said)
        return (
            f"could not push the heartbeat to {self._remote} {self._ref} (exit {code}: the"
            f" remote, the lease or the pre-push gate refused it){': ' + heard if heard else ''}"
        )

    @staticmethod
    def _evidence(text: str, *, lines: int = 4, limit: int = 500) -> str:
        """The last few lines of what a command said, on one line, colour codes dropped and
        any URL userinfo or GitHub token scrubbed: evidence for a record, never a secret."""
        kept = [
            line for line in (_COLOUR.sub("", raw).strip() for raw in text.splitlines()) if line
        ]
        tail = " | ".join(kept[-lines:])
        tail = _TOKEN.sub("[token]", _URL_USERINFO.sub(r"\1", tail))
        return tail[-limit:]

    def _lease(self) -> tuple[str, str]:
        """(the value the push may replace, problem). An empty value leases on absence:
        the push then succeeds only if the ref still does not exist."""
        code, listed = self._git("ls-remote", self._remote, self._ref)
        if code != 0:
            return (
                "",
                f"could not read {self._ref} on {self._remote}, so there is nothing to lease against; nothing was pushed",
            )
        current = ""
        for line in listed.splitlines():
            value, _, name = line.partition("\t")
            if name.strip() == self._ref:
                current = value.strip()
        if not current:
            return "", ""
        if self._git(NO_REPLACE_OBJECTS, "cat-file", "-e", current)[0] != 0:
            code, _ = self._git(
                "fetch", "--no-tags", "--no-write-fetch-head", self._remote, self._ref
            )
            if code != 0:
                return "", (
                    f"could not fetch what {self._ref} holds on {self._remote} to confirm it is"
                    " a heartbeat; nothing was pushed"
                )
        is_heartbeat, why = self._scope.is_empty_root(current)
        if not is_heartbeat:
            return "", (
                f"{self._ref} on {self._remote} holds {current}, which is not a heartbeat"
                f" ({why}); it is not replaced and nothing was pushed"
            )
        return current, ""

    # --- reading --------------------------------------------------------------------------

    def probe(self, *, max_age_minutes: int, now: float | None = None) -> Readiness:
        """Read the heartbeat and decide whether the sovereign lane may be scheduled.

        Every failure path answers "not ready" rather than raising: a probe that throws
        inside a workflow step is a red job, and a red job here would be a *worse* outcome
        than the absent sovereign review it is reporting.
        """
        code, _ = self._git("fetch", "--depth=1", self._remote, self._ref)
        if code != 0:
            return Readiness(
                False, f"no sovereign heartbeat at {self._ref} — the local lane is not offered"
            )
        code, raw = self._git("log", "-1", "--format=%ct", "FETCH_HEAD")
        if code != 0 or not raw.isdigit():
            return Readiness(False, "the heartbeat ref carries no readable timestamp")
        age = int((self._now() if now is None else now) - int(raw))
        if age < 0:
            return Readiness(
                False, "the heartbeat is dated in the future; refusing to trust it", age
            )
        if age > max_age_minutes * 60:
            return Readiness(
                False,
                f"the sovereign heartbeat is {age // 60}m old, past the {max_age_minutes}m"
                " window — treating the runner as offline",
                age,
            )
        return Readiness(True, f"sovereign runner heartbeat is {age}s old", age)


# The two module functions below are the entry points the CLI and adopters' scripts have
# always called. They stay functions so those callers keep working; each is one line into
# the class, which is where the behaviour lives.


def beat(
    ref: str,
    *,
    readiness: LaneReadinessInterface,
    remote: str = "origin",
    cwd: str | None = None,
) -> Readiness:
    """`SovereignHeartbeat(...).beat(readiness)`: publish only through the gate of the
    repository at `cwd`, and only when the lane can serve."""
    return SovereignHeartbeat(ref, remote=remote, cwd=cwd).beat(readiness)


def probe(
    ref: str,
    *,
    max_age_minutes: int,
    remote: str = "origin",
    cwd: str | None = None,
    now: float | None = None,
) -> Readiness:
    """`SovereignHeartbeat(...).probe(...)`: whether the lane may be scheduled now."""
    return SovereignHeartbeat(ref, remote=remote, cwd=cwd).probe(
        max_age_minutes=max_age_minutes, now=now
    )
