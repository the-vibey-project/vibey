# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`python -m vibey_gh`: the same entry point as the `vibey-gh` console script.

A runtime that has the package but not the script on PATH -- a bare virtualenv
interpreter, a worktree whose script shebangs point at another checkout's venv -- still
needs a way to reach the CLI, and `python -m` is the standard one. This module only
delegates; every command lives in `vibey_gh.cli`.
"""

from __future__ import annotations

from vibey_gh.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
