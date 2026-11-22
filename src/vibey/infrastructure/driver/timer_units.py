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

- **The units `vibey acp` loads (ADR-0101).** The hub and the worker, restarted `always`
  (launchd `KeepAlive` true, systemd `Restart=always`), throttled by the same
  `restart_seconds` and, on systemd, a start limit, so a crash loop is slowed and then
  stopped, never spun.

`vibey supervisor install` and `vibey driver timer` print the operator's own `launchctl` /
`systemctl --user` command and load nothing. `vibey acp` loads its two user-level units itself,
only under `[acp] auto_bootstrap` and `[acp] auto_services`, and says which and how to unload
them (ADR-0101, which amends ADR-0070's "the operator loads" for those two units alone).

Every value a unit takes from settings or the environment is escaped for its format: XML text
for launchd; for systemd, quotes, backslashes, `%` specifiers and, in `ExecStart`, `$`
variables. A value no format can carry -- a control character, or a byte that was never text
-- is refused with `ValueError` rather than written, since a newline would start a directive.
"""

import hashlib
from collections.abc import Sequence
from typing import Final
from xml.sax.saxutils import escape  # nosec B406 -- escaping text we write, parsing none

from vibey.domain.supervisor import SupervisedService

_SURROGATES: Final = range(0xD800, 0xE000)


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
        self._carried(service, path_env)
        args = "\n".join(f"    <string>{escape(part)}</string>" for part in service.argv)
        log = escape(service.log_path)
        if service.restart == "always":
            header = (
                "<!-- Rendered by `vibey acp` from [acp] and [supervisor] in vibey.toml (ADR-0101)."
                " vibey leaves this file alone once it differs from what it renders. -->\n"
            )
            keep_alive = "  <key>KeepAlive</key>\n  <true/>\n"
        else:
            header = (
                "<!-- Rendered by `vibey supervisor install` from [supervisor] in vibey.toml."
                " Edit the table and install again. -->\n"
            )
            keep_alive = (
                "  <key>KeepAlive</key>\n  <dict>\n"
                "    <key>SuccessfulExit</key>\n    <false/>\n  </dict>\n"
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f"{header}"
            '<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{escape(service.label)}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}\n  </array>\n"
            f"  <key>WorkingDirectory</key>\n  <string>{escape(service.working_directory)}</string>\n"
            "  <key>EnvironmentVariables</key>\n  <dict>\n"
            f"    <key>PATH</key>\n    <string>{escape(path_env)}</string>\n  </dict>\n"
            "  <key>RunAtLoad</key>\n  <true/>\n"
            f"{keep_alive}"
            f"  <key>ThrottleInterval</key>\n  <integer>{restart_seconds}</integer>\n"
            f"  <key>StandardOutPath</key>\n  <string>{log}</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{log}</string>\n"
            "</dict>\n</plist>\n"
        )

    def systemd_service(
        self,
        service: SupervisedService,
        *,
        path_env: str,
        restart_seconds: int,
        start_limit_interval_seconds: int = 0,
        start_limit_burst: int = 0,
    ) -> str:
        self._carried(service, path_env)
        exec_start = " ".join(self._exec_quote(part) for part in service.argv)
        log = self._bare(service.log_path)
        if service.restart == "always":
            header = (
                "# Rendered by `vibey acp` from [acp] and [supervisor] in vibey.toml (ADR-0101).\n"
                "# vibey leaves this file alone once it differs from what it renders.\n"
            )
            limits = (
                f"StartLimitIntervalSec={start_limit_interval_seconds}\n"
                f"StartLimitBurst={start_limit_burst}\n"
                if start_limit_interval_seconds > 0 and start_limit_burst > 0
                else ""
            )
        else:
            header = (
                "# Rendered by `vibey supervisor install` from [supervisor] in vibey.toml.\n"
                "# Edit the table and install again.\n"
            )
            limits = ""
        return (
            f"{header}"
            f"[Unit]\nDescription=vibey {service.name} (supervised; #1189)\n"
            "After=network-online.target\nWants=network-online.target\n"
            f"{limits}\n"
            "[Service]\nType=simple\n"
            f"WorkingDirectory={self._bare(service.working_directory)}\n"
            f"Environment={self._quote('PATH=' + path_env)}\n"
            f"ExecStart={exec_start}\n"
            f"Restart={service.restart}\nRestartSec={restart_seconds}\n"
            f"StandardOutput=append:{log}\nStandardError=append:{log}\n\n"
            "[Install]\nWantedBy=default.target\n"
        )

    @staticmethod
    def _carried(service: SupervisedService, path_env: str) -> None:
        """Refuse a value no unit format can carry: a control character would start a new
        directive (systemd) or break the property list (launchd), and a surrogate is a byte
        that was never text. Every other value is escaped where it is written."""
        values = (
            *service.argv,
            service.label,
            service.working_directory,
            service.log_path,
            path_env,
        )
        for value in values:
            if any(ord(c) < 0x20 or ord(c) == 0x7F or ord(c) in _SURROGATES for c in value):
                raise ValueError(
                    f"a value for the {service.name} unit holds a control character or a byte "
                    "that is not text; no unit can carry it"
                )

    @staticmethod
    def _bare(path: str) -> str:
        """A path setting that takes no quotes: only systemd's specifier escaped."""
        return path.replace("%", "%%")

    @staticmethod
    def _quote(part: str) -> str:
        """A quoted value systemd expands specifiers in but no variables (`Environment=`)."""
        return '"' + part.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'

    @classmethod
    def _exec_quote(cls, part: str) -> str:
        """One `ExecStart` argument: quoted, with `$` doubled so `$VAR` and `${VAR}` are not
        expanded and the argument reaches the process as planned."""
        return cls._quote(part).replace("$", "$$")
