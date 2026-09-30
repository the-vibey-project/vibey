# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The host platform behind the application's host-platform port.

A model that is not told where its shell commands run writes them for the platform it
saw most in training. Measured live on 2026-09-30 (vibey project 893c4fc1): gpt-oss:20b
ran GNU `sed -i '34i ...' README.md` twice on macOS, where BSD sed takes the expression
as `-i`'s backup suffix and fails with `invalid command code R`. The run's system prompt
now names the host, and for the two userlands this runs on says what differs.
"""

import platform
from collections.abc import Callable, Mapping


class HostPlatform:
    """`uname`, as one line a model can write shell commands against."""

    #: What each operating system's userland means for a command written elsewhere.
    USERLANDS: Mapping[str, str] = {
        "Darwin": (
            "macOS, BSD userland: `sed -i` takes a required backup-suffix argument "
            "(`sed -i ''`), and GNU-only options such as `grep -P` or `sed --in-place` fail"
        ),
        "Linux": "GNU userland",
    }

    def __init__(
        self,
        uname: Callable[[], platform.uname_result] = platform.uname,
        *,
        userlands: Mapping[str, str] | None = None,
    ) -> None:
        self._uname = uname
        self._userlands = self.USERLANDS if userlands is None else userlands

    def describe(self) -> str:
        host = self._uname()
        line = " ".join(part for part in (host.system, host.release, host.machine) if part)
        userland = self._userlands.get(host.system)
        return f"{line} ({userland})" if userland else line
