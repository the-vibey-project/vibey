"""A lane's commands run in the lane's own environment -- never one inherited from outside it.

WHAT WENT WRONG
---------------
QwenStorm 3.0.0 measured it: 25 runs in 16 lanes ran pytest under the operator's MAIN
checkout venv, and one `pip install`ed pytest and hypothesis into it. The model's own test
feedback -- the thing every repair attempt steers by -- was measuring a different tree, and
a lane wrote into an environment outside its workspace.

Nothing chose that. It was inherited, one hop at a time:

    operator shell   VIRTUAL_ENV=<main>/.venv-...  PATH=<main>/.venv-.../bin:...
      storm-queue.sh   passes its environment on unchanged
        qwenlane.py      runs qwenloop IN-PROCESS, so qwenloop's environment is this one
          shell tool       copies os.environ (minus *KEY*/*TOKEN*) into every command
            `python -m pytest`  ->  <main>/.venv-.../bin/python

`lane-setup.sh` gives every lane its own `.venv`; nothing ever put it in front.

POSIX ONLY
----------
The storm runs on macOS. This assumes a POSIX venv (`bin/python`, `bin/python3`) and says
so: on any other platform `verify()` refuses the lane outright rather than half-supporting
a layout it has never been run against.

THE RULE
--------
Nothing a lane's command inherits may point outside the lane's workspace. A relative path is
read the way a lane's command reads it -- from the lane, the directory every command runs in
-- so `../other/.venv/bin` on PATH is judged by where it lands, not by how it is spelled. That
is derived,
not a denylist of one path (12.h): a PATH entry is dropped because the directory IS a Python
environment's `bin/` -- it sits beside a `pyvenv.cfg` or a `conda-meta/` -- and lies outside
the lane, not because it is spelled like the operator's. The variables that choose an
interpreter or its import path are Python's own, a fixed vocabulary, and a value among them
survives only while every path it names is inside the lane.

THE GUARD
---------
Cleaning an environment is a claim; `verify()` is the evidence. Before a lane starts,
`python` and `python3` are resolved on the lane's PATH and the interpreter is asked for its
`sys.prefix`. Either landing outside the lane refuses the lane loudly (`ForeignEnvironment`)
rather than letting it run and report on somebody else's tree. A lane with no `.venv` of its
own -- `lane-setup.sh` only warns when `uv sync` fails -- is refused the same way.

python is not the only way back out: the lane venv shadows it, and a foreign `pytest` or
`pip` further down PATH would not be shadowed if the lane has none of its own. So the other
tools a lane runs are resolved too, and each must land inside the lane or somewhere that is
not a Python environment. A console script (`pip`, `pytest`) runs in the environment it is
installed in, so its symlink is followed -- pipx's `~/.local/bin/pytest` is a foreign venv's
pytest. `uv` is a native binary that chooses the interpreter from the project, not from where
it is installed, so its symlink is not followed (a `uv tool install`ed uv lives in a venv).

A class, per sub-doctrine 9.b, with its declaration beside it in
`interfaces/lane_environment_interface.py`. Underscored because it is imported, not run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, MutableMapping
from pathlib import Path

BIN = "bin"


class ForeignEnvironment(RuntimeError):
    """A lane's python would resolve outside the lane: the lane must not start."""


class LaneEnvironment:
    """The environment every command of one lane runs in, and the check that it holds."""

    # Python's own vocabulary for "which interpreter, which imports". A value survives only
    # while every absolute path in it lies inside the lane (PYTHONPATH keeps its inside
    # entries). VIRTUAL_ENV is then set to the lane's own venv.
    INTERPRETER_VARIABLES = frozenset(
        {
            "VIRTUAL_ENV",
            "PYTHONHOME",
            "PYTHONPATH",
            "PYTHONUSERBASE",
            "PYTHONEXECUTABLE",
            "__PYVENV_LAUNCHER__",
            "UV_PROJECT_ENVIRONMENT",
            "UV_PYTHON",
        }
    )
    # Activation state of a conda environment. A lane's environment is its `.venv`, so any
    # conda activation names somebody else's -- CONDA_DEFAULT_ENV=base points nowhere as a
    # path and still selects an interpreter.
    CONDA_FAMILY = "CONDA_"
    # It labels whichever venv VIRTUAL_ENV used to name; left behind, it would lie.
    DROPPED = frozenset({"VIRTUAL_ENV_PROMPT"})
    # The tools a lane runs besides python, and whether each runs in the environment it is
    # installed in (a console script: follow its symlink) or not (a native binary).
    TOOLS = {"pip": True, "pip3": True, "pytest": True, "uv": False}
    # The platform this was written for and has been run on; anything else is refused.
    platform = os.name

    def __init__(self, lane: Path) -> None:
        self.lane = lane.absolute()
        self.venv = self.lane / ".venv"
        self.bin = self.venv / BIN
        self._real = Path(os.path.realpath(self.lane))

    def inside(self, path: str | Path) -> bool:
        """True when `path` lies within the lane, symlinks followed (/tmp is /private/tmp)."""
        real = Path(os.path.realpath(path))
        return real == self._real or self._real in real.parents

    def build(self, inherited: Mapping[str, str]) -> dict[str, str]:
        """The lane's environment, from the one this process was started with."""
        env = dict(inherited)
        # Environments named by the inherited activation leave PATH even if their directories
        # are gone -- a deleted venv cannot be recognised by its files, only by its name.
        activated = {
            str(Path(prefix) / BIN)
            for prefix in (inherited.get("VIRTUAL_ENV"), inherited.get("CONDA_PREFIX"))
            if prefix and not self.inside(prefix)
        }
        for name in list(env):
            if name in self.DROPPED or name.startswith(self.CONDA_FAMILY):
                del env[name]
            elif name in self.INTERPRETER_VARIABLES:
                self._confine(env, name)
        kept: list[str] = []
        for entry in env.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            if not os.path.isabs(entry):
                # A lane's commands run with cwd=lane, so that is where this entry points.
                # Written absolute so it means the same thing from any directory, and
                # dropped when it lands outside the lane at all.
                entry = str(self.lane / entry)
                if not self.inside(entry):
                    continue
            if (
                entry in activated
                or self._python_environment_bin(Path(entry))
                or Path(entry) == self.bin
                or entry in kept
            ):
                continue
            kept.append(entry)
        env["PATH"] = os.pathsep.join([str(self.bin), *kept])
        env["VIRTUAL_ENV"] = str(self.venv)
        return env

    def verify(self, env: Mapping[str, str]) -> Path:
        """The lane's python under `env`, or `ForeignEnvironment` saying where it went instead."""
        if self.platform != "posix":
            raise ForeignEnvironment(
                f"the storm is POSIX-only (macOS) and this platform is {self.platform!r}; "
                "a lane is refused rather than run against a venv layout never tested"
            )
        if not (self.bin / "python").exists():
            raise ForeignEnvironment(
                f"{self.lane} has no .venv of its own ({self.bin / 'python'} is missing); "
                "lane-setup.sh's `uv sync` failed or never ran, and without it every "
                "`python` this lane runs would be somebody else's"
            )
        search = self._from_lane(env.get("PATH", ""))
        python = ""
        for name in ("python3", "python"):
            found = shutil.which(name, path=search)
            # The directory, not the file: a venv's python is a symlink to its base
            # interpreter, which is outside the lane by design.
            if found is None or not self.inside(Path(found).parent):
                raise ForeignEnvironment(
                    f"`{name}` resolves outside the lane: {found or 'nowhere'} "
                    f"(lane {self.lane}); its tests would measure another tree"
                )
            python = found
        for name, runs_in_its_environment in self.TOOLS.items():
            found = shutil.which(name, path=search)
            if found is None:
                continue
            homes = {Path(found).parent}
            if runs_in_its_environment:
                homes.add(Path(os.path.realpath(found)).parent)
            if any(self._python_environment_bin(home) for home in homes):
                raise ForeignEnvironment(
                    f"`{name}` resolves outside the lane, into another Python environment: "
                    f"{found} (lane {self.lane}); it would run and install against that tree"
                )
        try:
            done = subprocess.run(  # nosec B603 - the lane's own interpreter, fixed argv
                [python, "-c", "import sys; print(sys.prefix)"],
                cwd=self.lane,
                env=dict(env),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ForeignEnvironment(f"the lane's python did not run: {exc}") from exc
        prefix = done.stdout.strip()
        if done.returncode != 0 or not prefix or not self.inside(prefix):
            raise ForeignEnvironment(
                f"the lane's python reports sys.prefix={prefix or '<none>'} "
                f"(exit {done.returncode}), outside the lane {self.lane}"
            )
        return Path(python)

    def enter(self, environ: MutableMapping[str, str] | None = None) -> Path:
        """Make `environ` (this process's, by default) the lane's, once it has been verified.

        In place, because qwenloop runs in this process and its shell tool reads
        `os.environ` for every command. Nothing is changed when verification fails.
        """
        target = os.environ if environ is None else environ
        env = self.build(target)
        python = self.verify(env)
        target.clear()
        target.update(env)
        return python

    def _confine(self, env: dict[str, str], name: str) -> None:
        """Keep `env[name]` only while every path it names is inside the lane.

        A relative entry is read from the lane, as a lane's command reads it.
        """
        entries = [entry for entry in env[name].split(os.pathsep) if entry]
        inside = [e for e in entries if self.inside(self.lane / e)]
        if name == "PYTHONPATH" and inside:
            env[name] = os.pathsep.join(inside)
        elif not entries or len(inside) != len(entries):
            del env[name]

    def _from_lane(self, path: str) -> str:
        """`path` with every relative entry made absolute from the lane, where commands run."""
        return os.pathsep.join(str(self.lane / entry) for entry in path.split(os.pathsep) if entry)

    def _python_environment_bin(self, directory: Path) -> bool:
        """True when `directory` is the executables directory of a Python environment elsewhere.

        Inside the lane is never "elsewhere": the lane's own venv is the one allowed.
        """
        if self.inside(directory):
            return False
        home = directory.parent
        return (home / "pyvenv.cfg").is_file() or (home / "conda-meta").is_dir()
