# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey's service-manager units, as files: a launchd agent on macOS, a systemd user
unit on Linux.

- **The probe's timer (ADR-0070).** Runs `vibey driver probe --cwd <worktree>` every
  `[failover] probe_interval_seconds`. The probe itself decides whether anything is due,
  so a timer firing with no failover active does nothing and records nothing.
- **Supervised services (#1189).** Keep a long-running process alive: started at load,
  restarted after `[supervisor] restart_seconds` whenever it exits with a failure, never
  after a clean exit (a worker drained by SIGTERM stays down), its output appended to a
  durable log. `vibey supervisor install` renders the worker's and the delivery bridge's.

The units are rendered, written where the operator says, and loaded by the operator's
own `launchctl` / `systemctl --user` command, which the rendering command prints: vibey
never loads an agent into the operator's session behind their back.
"""

import hashlib
from collections.abc import Sequence
from xml.sax.saxutils import escape  # nosec B406 -- escaping text we write, parsing none

from vibey.domain.supervisor import SupervisedService


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

    def launchd_service(
        self, service: SupervisedService, *, path_env: str, restart_seconds: int
    ) -> str:
        args = "\n".join(f"    <string>{escape(part)}</string>" for part in service.argv)
        log = escape(service.log_path)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            "<!-- Rendered by `vibey supervisor install` from [supervisor] in vibey.toml."
            " Edit the table and install again. -->\n"
            '<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{escape(service.label)}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}\n  </array>\n"
            f"  <key>WorkingDirectory</key>\n  <string>{escape(service.working_directory)}</string>\n"
            "  <key>EnvironmentVariables</key>\n  <dict>\n"
            f"    <key>PATH</key>\n    <string>{escape(path_env)}</string>\n  </dict>\n"
            "  <key>RunAtLoad</key>\n  <true/>\n"
            "  <key>KeepAlive</key>\n  <dict>\n"
            "    <key>SuccessfulExit</key>\n    <false/>\n  </dict>\n"
            f"  <key>ThrottleInterval</key>\n  <integer>{restart_seconds}</integer>\n"
            f"  <key>StandardOutPath</key>\n  <string>{log}</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{log}</string>\n"
            "</dict>\n</plist>\n"
        )

    def systemd_service(
        self, service: SupervisedService, *, path_env: str, restart_seconds: int
    ) -> str:
        exec_start = " ".join(self._quote(part) for part in service.argv)
        log = self._bare(service.log_path)
        return (
            "# Rendered by `vibey supervisor install` from [supervisor] in vibey.toml.\n"
            "# Edit the table and install again.\n"
            f"[Unit]\nDescription=vibey {service.name} (supervised; #1189)\n"
            "After=network-online.target\nWants=network-online.target\n\n"
            "[Service]\nType=simple\n"
            f"WorkingDirectory={self._bare(service.working_directory)}\n"
            f"Environment={self._quote('PATH=' + path_env)}\n"
            f"ExecStart={exec_start}\n"
            f"Restart=on-failure\nRestartSec={restart_seconds}\n"
            f"StandardOutput=append:{log}\nStandardError=append:{log}\n\n"
            "[Install]\nWantedBy=default.target\n"
        )

    @staticmethod
    def _bare(path: str) -> str:
        """A path setting that takes no quotes: only systemd's specifier escaped."""
        return path.replace("%", "%%")

    @staticmethod
    def _quote(part: str) -> str:
        return '"' + part.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'
