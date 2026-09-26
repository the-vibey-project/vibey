"""The krypton launcher: `vibey serve`, then the browser -- or an honest refusal."""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from shutil import which
from typing import IO, Protocol

from krypton_app.interfaces.krypton_launcher_interface import KryptonLauncherInterface

AVAILABLE_INSTEAD = (
    "What you can use now:\n"
    "  vibey --help            the vibey command line\n"
    "  vibey doctor            what is installed and what is missing\n"
    "  the VS Code extension   krypton inside your editor (clients/vscode)\n"
)


class _Process(Protocol):
    def poll(self) -> int | None: ...
    def wait(self) -> int: ...
    def terminate(self) -> None: ...


def _probe(url: str) -> bool:
    """Whether anything answers HTTP at `url`, whatever the status."""
    try:
        with urllib.request.urlopen(url, timeout=2):  # nosec B310 - loopback URL we built
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


@dataclass
class KryptonLauncher(KryptonLauncherInterface):
    """Launches the hub through the installed `vibey`, with every side effect injectable."""

    out: IO[str]
    vibey: str | None = None
    ready_timeout: float = 60.0
    find: Callable[[str], str | None] = which
    run: Callable[[Sequence[str]], int] = field(
        default=lambda argv: (
            subprocess.run(  # nosec B603 - argv, no shell
                list(argv), capture_output=True, timeout=30, check=False
            ).returncode
        )
    )
    spawn: Callable[[Sequence[str]], _Process] = field(
        default=lambda argv: subprocess.Popen(list(argv))  # nosec B603 - argv, no shell
    )
    probe: Callable[[str], bool] = _probe
    browse: Callable[[str], object] = webbrowser.open
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic

    def launch(self, host: str, port: int, open_browser: bool) -> int:
        vibey = self.vibey or self.find("vibey")
        if vibey is None:
            self.out.write(
                "krypton: the vibey command is not installed, so there is no hub to start.\n"
                "Install the engine with: pip install vibey-engine\n"
            )
            return 1
        if self.run([vibey, "serve", "--help"]) != 0:
            self.out.write(
                "krypton: the local web app is started by `vibey serve`, and the installed\n"
                f"vibey ({vibey}) does not provide it yet. Nothing was started.\n"
                + AVAILABLE_INSTEAD
            )
            return 1
        url = f"http://{host}:{port}/"
        process = self.spawn([vibey, "serve", "--host", host, "--port", str(port)])
        deadline = self.clock() + self.ready_timeout
        while not self.probe(url):
            status = process.poll()
            if status is not None:
                self.out.write(
                    f"krypton: vibey serve exited with status {status} before it answered.\n"
                )
                return status or 1
            if self.clock() >= deadline:
                self.out.write(
                    f"krypton: nothing answered at {url} within {self.ready_timeout:g}s.\n"
                )
                process.terminate()
                return 1
            self.sleep(0.5)
        self.out.write(f"krypton: the vibey hub is at {url}\n")
        if open_browser:
            self.browse(url)
        try:
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            return 130
