# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Is a running hub's network exposure declared? `vibey doctor`'s `hub-exposure` line.

`vibey serve` refuses to bind a LAN address the configuration does not declare, so an
undeclared exposure means the declaration changed under a running hub -- `[hub] lan`
switched off, or the file replaced -- or something bound it by other means. Either way
the hub is listening where nothing written down says it may, and that is a FAIL
(sub-doctrines 10.f and 10.j): a surface nobody declared is not configuration, it is an
accident.

The verdict names what the evidence is: `PASS` for loopback or a declared LAN address,
`FAIL` for an undeclared one, and `UNKNOWN` when no hub is running (nothing to judge) or
the runtime record names a process that is gone (stale: it proves nothing).
"""

import os
from dataclasses import dataclass
from typing import Final

from vibey.domain.hub_binding import HUB_BINDING, Exposure
from vibey.domain.interfaces.hub_binding_interface import HubBindingPolicyInterface
from vibey.infrastructure.hub.interfaces.local_token_interface import LocalTokenStoreInterface
from vibey.infrastructure.hub.settings import HubSettings

CHECK_NAME: Final = "hub-exposure"


@dataclass(frozen=True, slots=True)
class ExposureFinding:
    """One doctor line: PASS, FAIL or UNKNOWN, and what it rests on."""

    mark: str
    detail: str

    @property
    def ok(self) -> bool:
        """False only for FAIL: UNKNOWN is reported, never passed off as a failure."""
        return self.mark != "FAIL"


class HubExposureCheck:
    """Judges a running hub's bound address against `[hub] lan`.

    Declared by `interfaces/exposure_interface.py::HubExposureCheckInterface`."""

    def __init__(self, binding: HubBindingPolicyInterface = HUB_BINDING) -> None:
        self._binding = binding

    def run(self, settings: HubSettings, store: LocalTokenStoreInterface) -> ExposureFinding:
        try:
            record = store.serving()
        except ValueError as exc:
            return ExposureFinding("UNKNOWN", f"the runtime record cannot be read: {exc}")
        if record is None:
            return ExposureFinding("UNKNOWN", "no hub is running; nothing is exposed")
        if not self._alive(record.pid):
            return ExposureFinding(
                "UNKNOWN", f"the runtime record names process {record.pid}, which is gone"
            )
        where = f"{record.host}:{record.port}"
        exposure = self._binding.exposure(record.host, lan_declared=settings.lan)
        if exposure is Exposure.LOOPBACK:
            return ExposureFinding("PASS", f"the hub listens on loopback only ({where})")
        if exposure is Exposure.DECLARED_LAN:
            return ExposureFinding("PASS", f"the hub listens on {where}, declared by [hub] lan")
        return ExposureFinding(
            "FAIL",
            f"the hub listens on {where}, and vibey.toml does not declare [hub] lan = true",
        )

    @staticmethod
    def _alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # The process exists and belongs to another account.
            return True
        return True


HUB_EXPOSURE: Final = HubExposureCheck()
"""The check `vibey doctor` and the hub's own doctor both run."""
