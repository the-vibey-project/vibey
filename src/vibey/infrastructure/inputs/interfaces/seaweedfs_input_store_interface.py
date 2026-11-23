# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the SeaweedFS input store, beside its class (ADR-0016; ADR-0105).

Mirrors `infrastructure/inputs/seaweedfs_input_store.py`. The runtime seam the run inputs service
consumes is `application/interfaces/input_store_interface.py::InputStoreInterface`; it is
restated here with what the S3 store promises about its layout and its failures. Interfaces
declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.input_store_interface import InputStoreInterface
from vibey.domain.run_input import StoreProbe


@runtime_checkable
class SeaweedFsInputStoreInterface(InputStoreInterface, Protocol):
    """`InputStoreInterface` over the S3 API of a SeaweedFS gateway (path-style,
    `<endpoint>/<bucket>/<key>`, every request signed with SigV4 by the family's one signer).

    Layout under `<prefix>/<project id>/`: `objects/<digest[:2]>/<digest>` holds each input's
    bytes once, and `index/<ns:020d>-<uuid hex>.json` one object per row, since S3 has no append;
    the listing's key order is the add order. The bucket is never created. A listing is paged to
    its end and refused, unparsed, when a page is too large or carries a DOCTYPE or ENTITY.
    `InputStoreUnavailable` (retryable) when the store does not answer, times out or answers 5xx;
    `InputStoreError` for everything else, naming the credential variables and never their
    values."""

    def describe(self) -> str:
        """The store in words: scheme, host, bucket and prefix. Never a credential."""
        ...

    def probe(self) -> StoreProbe:
        """One ListObjectsV2 of at most one key under the prefix: whether the store answers, and
        if not, why (not reachable, credentials refused, bucket missing). Never raises."""
        ...
