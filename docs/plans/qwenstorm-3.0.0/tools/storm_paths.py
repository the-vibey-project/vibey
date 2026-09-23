"""Where the storm and the repository are: declared in `storm.toml`, never typed into a tool.

Five tools carried `MAIN = Path("/Users/adam/git/vibey")` and one carried a storm path as a
literal. That is one operator's machine compiled into the toolchain: a second person cloning
this repository gets tools that address a directory they do not have, and they get it
silently, because a wrong absolute path does not fail loudly -- it reports an empty tree,
which reads exactly like a healthy one.

Sub-doctrine 12.h is the rule this implements, and 12.c is the older one it sharpens: a
hard-coded value that could have been a key is a decision taken away from the next adopter.
A location is never a fact about the program. It is a fact about the machine the program was
run on, and it belongs in a file that machine owns.

Underscored, not hyphenated, because this one is imported rather than run.

THE ONE THING THAT CANNOT BE CONFIGURED
---------------------------------------
Where the configuration itself is. A tool has to find `storm.toml` before it can read
anything out of it, so the storm root is derived from the calling tool's own location and
everything else is declared. That is the whole of the exception, and it is stated here
rather than left as an oversight for somebody to discover.

The caller passes its own `__file__` because `tools/` is a SYMLINK into the planning
worktree. `.absolute()` keeps the path the caller was invoked by, where `lanes/` and
`integration/` exist; `.resolve()` would follow the link into the planning tree, where they
do not -- and a tool that resolves reports "0 lanes, nothing to do". That is not a style
choice. It is why every tool here spells `.absolute()` out with a comment, and it cost a
wasted `lane-refresh` run on 2026-09-23 to learn.

WHAT storm.toml LOOKS LIKE
--------------------------
    [paths]
    repo = "~/git/vibey"        # the repository the storm publishes into

Every key is optional. An absent key is derived from the tree rather than guessed at, so a
storm with no `storm.toml` at all still works on the machine it was set up on -- the file is
how a DIFFERENT machine says where things are, which is the point of having it.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

CONFIG = "storm.toml"


def storm(caller: str) -> Path:
    """The storm runtime root: the directory holding `lanes/`, `queue.txt` and the ledgers."""
    # .absolute(), never .resolve() -- see the module docstring.
    return Path(caller).absolute().parent.parent


def declared(root: Path, section: str, key: str) -> str | None:
    """One key from `storm.toml`, or None when the file or the key is absent."""
    path = root / CONFIG
    if not path.is_file():
        return None
    try:
        found = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        # A malformed config is not the same as an absent one. Falling through to derivation
        # here would run the storm against a tree the operator did not choose, having been
        # told in the file which tree they did choose -- so this refuses instead (10.f).
        raise SystemExit(f"{path} could not be read: {exc}") from exc
    value = found.get(section, {}).get(key)
    return str(value) if value is not None else None


def repo(root: Path) -> Path:
    """The vibey repository the storm publishes into."""
    if (declared_path := declared(root, "paths", "repo")) is not None:
        return Path(declared_path).expanduser()
    # Derived, not guessed -- but from the right directory, which took a wrong answer to
    # find. `integration/` looks like the obvious place to ask and is a full CLONE, so its
    # common git directory is its own and `repo()` confidently returned the clone. Every
    # tool then ran `gh` and `git` against a tree with no origin/develop and no pull
    # requests, and said so in the vocabulary of a broken network.
    #
    # `tools/` is a symlink into the planning WORKTREE, which is a worktree of the real
    # repository, so `.resolve()` -- following the link, the exact opposite of what `storm()`
    # must do -- lands somewhere whose common git directory is the repository's. The two
    # rules are opposite because the two questions are: `lanes/` exists only where the link
    # points FROM, and the repository is reachable only where it points TO.
    for start in (Path(__file__).resolve().parent, root / "integration"):
        if not start.is_dir():
            continue
        try:
            done = subprocess.run(
                [
                    "git",
                    "-C",
                    str(start),
                    "rev-parse",
                    "--path-format=absolute",
                    "--git-common-dir",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if done.returncode == 0 and done.stdout.strip():
            # `--git-common-dir` is the MAIN checkout's .git even when asked of a worktree,
            # which is the whole reason it is asked of the integration worktree.
            return Path(done.stdout.strip()).parent
    raise SystemExit(
        f"cannot locate the vibey repository. Declare it in {root / CONFIG}:\n\n"
        '    [paths]\n    repo = "~/git/vibey"\n'
    )


def interpreter(root: Path) -> str:
    """The Python the storm's runners use, declared or the one running this."""
    return declared(root, "paths", "python") or sys.executable


def slug(root: Path) -> str:
    """`owner/name` for the forge, declared or read from the repository's own remote.

    Derived rather than typed for the same reason as everything else here: a fork, a
    rename or a second adopter each make a written slug wrong, and a wrong slug does not
    raise -- `gh issue view -R wrong/repo` fails in the vocabulary of a missing issue.
    """
    if (declared_slug := declared(root, "paths", "slug")) is not None:
        return declared_slug
    done = subprocess.run(
        ["git", "-C", str(repo(root)), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if done.returncode != 0:
        raise SystemExit(f"cannot read origin. Declare [paths] slug in {root / CONFIG}")
    url = done.stdout.strip().removesuffix(".git")
    # Both spellings of a remote: git@host:owner/name and https://host/owner/name
    return "/".join(url.replace(":", "/").split("/")[-2:])


def main() -> int:
    """A CLI so the shell tools read the same answers the Python tools do.

    `storm-queue.sh` and `lane-setup.sh` carried their own copies of these paths, which is
    how six literals became eight. A shell script cannot read TOML without help, and the
    help it gets should be the one resolver rather than a second one that agrees today.

        MAIN="$(python3 tools/storm_paths.py repo)"
    """
    if len(sys.argv) != 2 or sys.argv[1] not in {"storm", "repo", "python", "slug"}:
        print("usage: storm_paths.py {storm|repo|python|slug}", file=sys.stderr)
        return 2
    root = storm(__file__)
    print(
        {
            "storm": lambda: root,
            "repo": lambda: repo(root),
            "python": lambda: interpreter(root),
            "slug": lambda: slug(root),
        }[sys.argv[1]]()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
