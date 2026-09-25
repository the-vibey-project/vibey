# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The probe's timer, as files (ADR-0070): a launchd agent on macOS, a systemd user
service and timer on Linux. Each runs `vibey driver probe --cwd <worktree>` every
`[failover] probe_interval_seconds`. The probe itself decides whether anything is due,
so a timer firing with no failover active does nothing and records nothing.

The units are rendered, written where the operator says, and loaded by the operator's
own `launchctl` / `systemctl --user` command, which `vibey driver timer` prints: vibey
never loads an agent into the operator's session behind their back.
"""

import hashlib
from collections.abc import Sequence
from xml.sax.saxutils import escape  # nosec B406 -- escaping text we write, parsing none


class TimerUnitRenderer:
    """Declared by `interfaces/timer_units_interface.py`."""

    def label(self, cwd: str) -> str:
        return "dev.vibey.driver-probe." + hashlib.sha256(cwd.encode()).hexdigest()[:12]

    def launchd(self, *, argv: Sequence[str], cwd: str, interval_seconds: int) -> str:
        args = "\n".join(f"    <string>{escape(part)}</string>" for part in argv)
        log = escape(f"{cwd}/.vibey/driver/probe.log")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{escape(self.label(cwd))}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}\n  </array>\n"
            f"  <key>WorkingDirectory</key>\n  <string>{escape(cwd)}</string>\n"
            f"  <key>StartInterval</key>\n  <integer>{interval_seconds}</integer>\n"
            f"  <key>StandardOutPath</key>\n  <string>{log}</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{log}</string>\n"
            "</dict>\n</plist>\n"
        )

    def systemd(self, *, argv: Sequence[str], cwd: str, interval_seconds: int) -> tuple[str, str]:
        exec_start = " ".join(self._quote(part) for part in argv)
        service = (
            "[Unit]\nDescription=vibey driver probe (ADR-0070)\n\n"
            "[Service]\nType=oneshot\n"
            f"WorkingDirectory={self._quote(cwd)}\n"
            f"ExecStart={exec_start}\n"
        )
        timer = (
            "[Unit]\nDescription=vibey driver probe timer (ADR-0070)\n\n"
            f"[Timer]\nOnBootSec={interval_seconds}s\nOnUnitActiveSec={interval_seconds}s\n"
            f"Unit={self.label(cwd)}.service\n\n"
            "[Install]\nWantedBy=timers.target\n"
        )
        return service, timer

    @staticmethod
    def _quote(part: str) -> str:
        return '"' + part.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'
