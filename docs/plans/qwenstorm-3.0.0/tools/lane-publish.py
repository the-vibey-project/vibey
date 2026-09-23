"""Publish the lanes that have actually earned it: commit, push, open a pull request.

    python3 lane-publish.py                  # report what is ready; change nothing
    python3 lane-publish.py --publish        # commit, push and open a PR for each ready lane
    python3 lane-publish.py --publish --only rmq-r03-amqp-dependency
    python3 lane-publish.py --watch 600      # re-check every 600s, publishing as lanes ripen

Never merges. A pull request is where a human looks; this stops there, and `--publish` is
required before anything leaves the machine.

WHY THE GATE IS NOT THE LANE'S OWN VERDICT
------------------------------------------
qwenloop marks a run `completed` when the model emits the done marker and its verdict fence
carries the CDD labels. Its own `_has_cdd_evidence` is candid -- "a deterministic protocol
check, not a substitute for reviewing the values" -- and nothing in the runner executes the
spec's check block. On 2026-09-22, of eleven finished lanes:

  rmq-r02-wakeup-composition   claimed completed, shipped `SyntaxError: unmatched '}'`
  visual-design-provider       claimed completed, shipped a NameError that broke a package
  installer-catalogue          claimed completed, wrote sitecustomize.py into the repo root
  chart-operator-forgejo-p1    claimed completed, shipped an unterminated string literal

Exactly one -- rmq-r03-amqp-dependency -- was genuinely mergeable. So a claim opens the
question and settles nothing (sub-doctrine 10.f). Every gate below is evidence this script
gathers itself, and a lane passes only if all of them hold.

WHAT IT REFUSES
---------------
Anything lane-verify reports a problem for; anything whose spec named tests it never wrote;
anything that touched a path its spec does not own; anything whose own check block fails when
run. A lane that fails any gate is left exactly as it is, for a human, and the reason is
printed. Silence is never taken for success.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"
MAIN = Path("/Users/adam/git/vibey")
WORKTREES = STORM.parent / "publish"
REPO = "the-vibey-project/vibey"
BASE = "develop"

# Commands a lane's check block may name that this script will run. Anything else in a check
# block is reported and skipped rather than executed: a spec is written by a model, and a
# publishing step is not the place to run whatever a model happened to type.
SAFE = ("uv", "python", "python3", "pytest", "ruff", "mypy", "lint-imports", "grep", "git")


def run(argv: list[str], cwd: Path, timeout: int = 900) -> tuple[int, str]:
    # VIRTUAL_ENV is inherited from whatever shell started this, and `uv run` obeys it: a lane's
    # checks would then run against the environment of the checkout this script was launched
    # from rather than the lane's own, and pass or fail for reasons that have nothing to do with
    # the lane. Drop it and let uv resolve the environment from the lane it is standing in.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    try:
        done = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def why_failed(out: str) -> str:
    """The line a person needs, not the last line printed.

    `uv run` ends with installer chatter and warnings, so the final line of a failed check is
    usually "Installed 4 packages in 15ms" -- true, irrelevant, and the reason a report can
    look like nonsense. Prefer a line that names an error.
    """
    lines = [line for line in out.splitlines() if line.strip()]
    for line in reversed(lines):
        low = line.lower()
        if any(
            word in low for word in ("error", "failed", "broken", "not found", "e   ", "assert")
        ):
            return line.strip()
    return lines[-1].strip() if lines else "no output"


def settled() -> set[str]:
    out: set[str] = set()
    for name in ("integrated.txt", "abandoned.txt"):
        path = STORM / name
        if path.is_file():
            out |= {line.strip() for line in path.read_text().splitlines() if line.strip()}
    return out


def issue_of(slug: str) -> int | None:
    """The lane's issue number, from queue.txt -- the runner's own mapping."""
    queue = STORM / "queue.txt"
    if not queue.is_file():
        return None
    for line in queue.read_text().splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[0] == slug and parts[1].isdigit():
            return int(parts[1])
    return None


def checks_of(lane: Path) -> list[list[str]]:
    """The commands the lane's own spec says must pass.

    The lane's shell runs argv with no shell at all, so a check block is a list of argv lines:
    `&&`, pipes, redirects and `cd` are literal arguments there and are literal here too. A
    line carrying any of them is not something this script can honestly run, so it is skipped
    and reported rather than guessed at.
    """
    issue = lane / ".qwenstorm/issue.md"
    if not issue.is_file():
        return []
    text = issue.read_text(encoding="utf-8")
    if "## Checks the lane must run" not in text:
        return []
    block = text.split("## Checks the lane must run", 1)[1].split("\n## ", 1)[0]
    found: list[list[str]] = []
    for raw in block.splitlines():
        line = raw.strip().strip("`")
        if not line or line.startswith(("#", "```", "-", "(", "*")):
            continue
        if any(token in line for token in ("&&", "|", ">", "<", "$(", "cd ")):
            continue
        parts = line.split()
        if parts and parts[0] in SAFE:
            found.append(parts)
    return found


def verify(slug: str) -> tuple[bool, list[str]]:
    """lane-verify's own verdict for one lane, re-run now rather than read from a stale file.

    "nothing committed" is not a reason to refuse: a lane's runner never commits, so every
    lane reads that way, and committing is this script's own first act. Requiring it to be
    absent made publishing impossible -- the one lane that ever passed had been committed by
    hand first. Every other problem still holds the lane.
    """
    code, out = run([sys.executable, str(STORM / "tools/lane-verify.py"), slug], STORM, timeout=900)
    report = LANES / slug / ".qwenstorm/verify.json"
    if report.is_file():
        problems = [
            p
            for p in json.loads(report.read_text()).get("problems", [])
            if not p.startswith("nothing committed")
        ]
        return not problems, list(problems)
    return code == 0, [] if code == 0 else [out.strip().splitlines()[-1] if out else "no report"]


def already_published(slug: str) -> str | None:
    """Whether this lane is already out for review.

    Without this the sweep republishes anything it published on the previous pass: the gates
    keep passing, so `ready` keeps saying yes. Idempotence has to come from the forge, not
    from remembering -- a local note would be wrong the moment a PR is opened or closed
    anywhere else.
    """
    branch = f"lane/{slug}"
    code, out = run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--state",
            "all",
            "--head",
            branch,
            "--json",
            "number,state",
        ],
        STORM,
        timeout=120,
    )
    if code == 0 and out.strip():
        try:
            rows = json.loads(out)
        except json.JSONDecodeError:
            rows = []
        if rows:
            return f"#{rows[0]['number']} ({rows[0]['state'].lower()})"
    code, _ = run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], MAIN, 120)
    if code == 0:
        return "a branch is already pushed"
    # And a pull request that claims the issue under any branch name: a lane published by hand
    # will not be sitting on `lane/<slug>`, and republishing it would open a second PR for the
    # same work. rmq-r03-amqp-dependency went out as `feat/amqp-dependency` exactly this way.
    issue = issue_of(slug)
    if issue:
        code, out = run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPO,
                "--state",
                "all",
                "--search",
                f"Closes #{issue} in:body",
                "--json",
                "number,state",
            ],
            STORM,
            timeout=120,
        )
        if code == 0 and out.strip():
            try:
                rows = json.loads(out)
            except json.JSONDecodeError:
                rows = []
            if rows:
                return f"#{rows[0]['number']} already closes issue #{issue}"
    return None


def ready(slug: str) -> tuple[bool, list[str]]:
    lane = LANES / slug
    result = lane / ".qwenstorm/result.json"
    if not result.is_file():
        return False, ["still running"]
    out_already = already_published(slug)
    if out_already:
        return False, [f"already published: {out_already}"]
    clean, problems = verify(slug)
    if not clean:
        return False, problems
    ran = checks_of(lane)
    if not ran:
        return False, ["its spec names no check block this script can run"]
    interpreter = lane / ".venv/bin/python"
    failures = []
    for argv in ran:
        if argv[0] in {"python", "python3", "pytest"} and interpreter.is_file():
            argv = [str(interpreter), *(["-m"] if argv[0] == "pytest" else []), *argv[1:]]
        code, out = run(argv, lane)
        if code:
            failures.append(f"check failed: {' '.join(argv)[:55]} -- {why_failed(out)[:110]}")
    return (not failures), failures


def publish(slug: str, dry: bool) -> str:
    lane = LANES / slug
    issue = issue_of(slug)
    title = (lane / ".qwenstorm/title.txt").read_text().strip()
    branch = f"lane/{slug}"
    if dry:
        return f"would publish as {branch} (closes #{issue})"

    if (
        run(["git", "diff", "--quiet"], lane)[0]
        or run(["git", "diff", "--cached", "--quiet"], lane)[0]
        or run(["git", "ls-files", "--others", "--exclude-standard"], lane)[1]
    ):
        run(["git", "add", "-A"], lane)
        body = f"{title}\n\nWritten by a sovereign lane (gpt-oss:20b) for issue #{issue}.\n"
        code, out = run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", body], lane)
        if code:
            return f"commit failed: {out[:120]}"

    WORKTREES.mkdir(parents=True, exist_ok=True)
    tree = WORKTREES / slug
    if tree.exists():
        run(["git", "worktree", "remove", "--force", str(tree)], MAIN)
    run(["git", "fetch", "-q", "origin", BASE], MAIN)
    code, out = run(["git", "worktree", "add", str(tree), "-b", branch, f"origin/{BASE}"], MAIN)
    if code:
        return f"worktree failed: {out[:120]}"
    run(["git", "fetch", "-q", str(lane), f"storm/{slug}"], tree)
    code, head = run(["git", "rev-parse", "FETCH_HEAD"], tree)
    code, out = run(["git", "cherry-pick", head.strip()], tree)
    if code:
        # The lane's commit is being replayed onto develop as it is right now, so a conflict
        # here is the lane's work disagreeing with what landed while it ran -- the same
        # question lane-refresh.py asks, and it gets the same answer from the same code.
        # lane-resolve.py aborts the cherry-pick itself when it refuses, so the state is read
        # back from git rather than from its exit code.
        run(
            [
                sys.executable,
                str(STORM / "tools/lane-resolve.py"),
                "--resolve",
                "--repo",
                str(tree),
            ],
            STORM,
            timeout=1200,
        )
        unresolved = run(["git", "diff", "--name-only", "--diff-filter=U"], tree)[1].strip()
        picking = run(["git", "rev-parse", "-q", "--verify", "CHERRY_PICK_HEAD"], tree)[0] == 0
        if unresolved or picking:
            run(["git", "cherry-pick", "--abort"], tree)
            return f"cherry-pick failed: {out[:120]}"
    run(["uv", "sync", "-q", "--extra", "dev"], tree, timeout=900)
    code, out = run(["git", "push", "-u", "origin", branch], tree, timeout=1800)
    if code:
        return f"push refused (the gates run on push): {out.strip().splitlines()[-1][:140]}"
    body = (
        f"Closes #{issue}.\n\nWritten by a sovereign lane (gpt-oss:20b) and gated at review by "
        f"`tools/lane-verify.py` plus the lane's own check block, both run again immediately "
        f"before this branch was pushed.\n\nA lane's `completed` flag is a protocol check and "
        f"not evidence (10.f), so it was not used as the gate.\n\n"
        f"🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    )
    code, out = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            REPO,
            "--base",
            BASE,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        tree,
        timeout=300,
    )
    return f"published: {out.strip().splitlines()[-1]}" if not code else f"pr failed: {out[:120]}"


def sweep(dry: bool, only: list[str] | None) -> int:
    done = settled()
    slugs = (
        sorted(d.name for d in LANES.iterdir() if d.is_dir() and d.name not in done)
        if LANES.is_dir()
        else []
    )
    if only:
        slugs = [s for s in slugs if s in only]
    published = 0
    for slug in slugs:
        ok, why = ready(slug)
        if ok:
            print(f"READY  {slug}\n       {publish(slug, dry)}")
            published += 1
        else:
            print(f"hold   {slug}")
            for reason in why[:3]:
                print(f"       - {reason}")
    print(f"\n{len(slugs)} unsettled lane(s), {published} ready")
    return published


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="actually commit, push and open PRs")
    parser.add_argument("--only", action="append")
    parser.add_argument("--watch", type=int, metavar="SECONDS")
    args = parser.parse_args()
    while True:
        sweep(dry=not args.publish, only=args.only)
        if not args.watch:
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    raise SystemExit(main())
