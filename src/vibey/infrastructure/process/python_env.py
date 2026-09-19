# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the orchestrator's own Python environment lives (#283).

Engine sessions and gate commands both run with vibey's Python environment removed
(`isolate_python_env`). This class answers the question that comes first: which
directories are vibey's? The engine spawn and the gate runner each answered it
separately, and only the gate runner answered it correctly (#212). Now both ask here.
"""

import os
import sys
from collections.abc import Mapping


class OrchestratorPythonEnv:
    """The active venv and the running interpreter's venv, if it runs from one.

    Declared by `interfaces/python_env_interface.py`. Reads `sys` and the
    environment at call time, not at construction, so one instance stays correct for
    the life of a worker.
    """

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        # None means the live process environment, read on every call.
        self._environ = environ

    def interpreter_venv(self) -> str | None:
        # sys.prefix names a venv only when it differs from sys.base_prefix. On an
        # interpreter installed into the system, both are `/usr`. Treating that as a
        # venv strips every PATH entry under it: /usr/bin and /usr/local/bin, and
        # with them git, sh, the engine CLIs and most of what a session or a gate
        # runs.
        return sys.prefix if sys.prefix != sys.base_prefix else None

    def venv_prefixes(self) -> tuple[str | None, ...]:
        environ = os.environ if self._environ is None else self._environ
        return (environ.get("VIRTUAL_ENV"), self.interpreter_venv())
