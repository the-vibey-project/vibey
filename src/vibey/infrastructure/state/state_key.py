# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""StateKeyStore: where the state key is kept on this machine (ADR-0086).

The key is looked for in order: `VIBEY_STATE_KEY` (a runner gets it from the repository's
`VIBEY_STATE_KEY` secret), then the macOS keychain (service `dev.vibey.state`, account the
repository), then the key file, which must be readable by its owner alone. `vibey state
key --new` makes one where it would be found first on this machine -- the keychain on macOS,
the key file elsewhere -- and refuses when one exists anywhere: replacing a key makes every
state sealed under it unreadable, so it is never done by a command that could be re-run.
"""

import os
import stat
import subprocess  # nosec B404 -- fixed argv, never shell=True
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.errors import VibeyError
from vibey.infrastructure.state.aes_gcm_cipher import StateKey
from vibey.infrastructure.state.interfaces.settings_interface import StateSyncSettingsInterface
from vibey.infrastructure.state.interfaces.state_key_interface import StateKeyStoreInterface

KEYCHAIN_SERVICE: Final[str] = "dev.vibey.state"
SECURITY: Final[str] = "/usr/bin/security"

#: Runs an argument vector with optional stdin; the exit code and stdout.
Runner = Callable[[Sequence[str], str | None], tuple[int, str]]


class StateKeyMissing(VibeyError):
    """No state key on this machine, or one that cannot be used."""


def run_security(argv: Sequence[str], stdin: str | None) -> tuple[int, str]:
    """Runs `security`. Module-level: it is the one seam the key store's tests replace."""
    done = subprocess.run(  # nosec B603 -- an argument vector, never a shell
        list(argv), input=stdin, capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout


class StateKeyStore(StateKeyStoreInterface):
    """Declared by `interfaces/state_key_interface.py::StateKeyStoreInterface`."""

    def __init__(
        self,
        settings: StateSyncSettingsInterface,
        *,
        keychain: bool | None = None,
        runner: Runner = run_security,
    ) -> None:
        if keychain is None:
            keychain = sys.platform == "darwin" and Path(SECURITY).exists()
        if '"' in settings.repository:
            raise ValueError("a repository name has no quotes")
        self._settings = settings
        self._keychain = keychain
        self._runner = runner

    @property
    def _account(self) -> str:
        return self._settings.repository or "default"

    def _from_keychain(self) -> str:
        if not self._keychain:
            return ""
        code, out = self._runner(
            (SECURITY, "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", self._account, "-w"),
            None,
        )
        return out.strip() if code == 0 else ""

    def _from_file(self) -> str:
        path = Path(self._settings.key_file)
        if not path.is_file():
            return ""
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise StateKeyMissing(
                f"{path} can be read by others: `chmod 600 {path}`, then sync again"
            )
        return path.read_text(encoding="utf-8").strip()

    def where(self) -> str:
        """Where the key in use was found, or "" when there is none."""
        if self._settings.key:
            return "VIBEY_STATE_KEY"
        if self._from_keychain():
            return f"the keychain ({KEYCHAIN_SERVICE}, {self._account})"
        if self._from_file():
            return self._settings.key_file
        return ""

    def text(self) -> str:
        found = self._settings.key or self._from_keychain() or self._from_file()
        if not found:
            raise StateKeyMissing(
                "no state key on this machine: `vibey state key --new` makes one; on another "
                "machine, set VIBEY_STATE_KEY to the key the first one shows"
            )
        StateKey.parse(found)
        return found

    def load(self) -> bytes:
        return StateKey.parse(self.text())

    def create(self) -> str:
        """Make a key and keep it; refuses while one exists. Where it was kept."""
        existing = self.where()
        if existing:
            raise StateKeyMissing(f"a state key already exists ({existing}); it is never replaced")
        key = StateKey.new()
        if self._keychain:
            # Through `security -i` on stdin, so the key is never on an argument vector
            # another user's `ps` could read.
            command = (
                f'add-generic-password -s "{KEYCHAIN_SERVICE}" -a "{self._account}" -w "{key}"\n'
            )
            code, _ = self._runner((SECURITY, "-i"), command)
            if code == 0:
                return f"the keychain ({KEYCHAIN_SERVICE}, {self._account})"
        path = Path(self._settings.key_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(key + "\n")
        return str(path)
