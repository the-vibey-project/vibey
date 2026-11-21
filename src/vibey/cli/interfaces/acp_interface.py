# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey acp`: the stdio Agent Client Protocol command (SP-ACP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.interfaces.acp_agent_interface import AcpAgentInterface
    from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
    from vibey.domain.acp.settings import AcpSettings


@runtime_checkable
class AcpCommandInterface(Protocol):
    def run(self, *, no_bootstrap: bool) -> None:
        """Guard stdout, read `[acp]`, and serve ACP over stdio until stdin closes.
        `no_bootstrap` turns `[acp] auto_bootstrap` off for this process."""
        ...


class AcpAgentBuilder(Protocol):
    """Composes the ACP agent for one process: the shape of `bootstrap.build_acp_agent`."""

    def __call__(
        self, *, settings: AcpSettings, channel: ClientChannelInterface
    ) -> AcpAgentInterface: ...
