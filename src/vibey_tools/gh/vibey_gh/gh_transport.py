# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One way to run `gh`, with each of the three answers the tree already relies on.

The contract is `vibey_gh.interfaces.gh_transport_interface`. Each result shape below is
the extraction of a runner that exists today, kept to the byte — the error text, the empty
answer, which exceptions escape — because a module only moves onto this transport safely if
nothing it returns to its own callers changes when it does:

- `json` is `github_state.gh_json`, and the merge train's `_gh_json`, which is its twin.
- `probe` is `promote._gh` by default and the merge train's `_gh` with
  `strip=False, with_stderr=True`.
- `survey` is what `tidy._gh_json` was, before the clean-repo survey moved onto the GitHub
  forge adapter (`vibey_gh.forge_github`), which now reads through it.

`github_state` was the first consumer and the forge adapter the second. The rest of the
package still runs its own and moves over one module at a time.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface, WorkingDirectory


@dataclass(frozen=True)
class GhTransport(GhTransportInterface):
    """Runs `executable` on PATH with an argv this process built.

    `executable` is the one literal every runner in the package used to repeat. Nothing
    reads it from configuration yet.

    `host` pins the client to one forge host by exporting it as `GH_HOST`, which is how
    `gh` is pointed at a GitHub Enterprise Server instead of github.com. `None`, the
    default, leaves the child's environment exactly as this process has it: every runner
    this transport replaced did that, and a `GH_HOST` the caller exported keeps working.
    The forge adapter sets it from `[platform] host`, and only for a host other than the
    one `gh` assumes on its own.
    """

    executable: str = "gh"
    host: str | None = None

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        # `cwd=None`, `input=None` and `env=None` are `subprocess.run`'s own defaults, so a
        # call that sets none of them is the very call the runners it replaces made.
        return subprocess.run(
            [self.executable, *args],
            cwd=cwd,
            input=stdin,
            env=None if self.host is None else {**os.environ, "GH_HOST": self.host},
            capture_output=True,
            text=True,
            check=False,
        )

    def json(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> Any:
        run = self.run(args, cwd=cwd, stdin=stdin)
        if run.returncode:
            raise RuntimeError(f"{self.executable} {' '.join(args)}: {run.stderr.strip()}")
        return json.loads(run.stdout or "null")

    def probe(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
        strip: bool = True,
        with_stderr: bool = False,
    ) -> tuple[bool, str]:
        run = self.run(args, cwd=cwd, stdin=stdin)
        out = run.stdout or ""
        if with_stderr:
            out += run.stderr or ""
        return run.returncode == 0, out.strip() if strip else out

    def survey(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[list[Any] | dict[str, Any], str]:
        label = " ".join((self.executable, *args[:2]))
        try:
            run = self.run(args, cwd=cwd, stdin=stdin)
        except FileNotFoundError:
            return [], f"the GitHub CLI (`{self.executable}`) is not installed"
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
