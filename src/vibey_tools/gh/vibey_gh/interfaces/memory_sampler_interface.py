# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for reading the hardware side of the fit (ADR-0016).

One contract, one implementation per platform: `vibey_gh.fit` picks the sampler that
matches the machine it is actually running on, and every sampler answers the same way —
including when it cannot read the machine at all, which is a loud `Machine.readable ==
False` rather than a silent zero (doctrine 10).

`Machine` is imported for typing only. It is a frozen data record, the same standing
`vibey_gh.config`'s settings have in the marketplace seam: naming the shape a seam
speaks in is declaring, not consuming.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.fit import Machine


@runtime_checkable
class MemorySamplerInterface(Protocol):
    """Reads what this machine says about its own memory and paging space."""

    def sample(self) -> Machine:
        """The machine as it states itself, never as it is assumed to be.

        A field this machine will not state is reported as zero with `readable` false,
        so a caller can fail loudly at the floor instead of projecting onto a machine
        that appears to have no memory.
        """
        ...
