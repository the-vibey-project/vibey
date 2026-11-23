# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`HubCertificate.client_context`: a client trusts the hub's own certificate and nothing else
(SP-ACP Task 11b). `vibey hub pair` and the MCP/ACP gateway used to pass the certificate's path
as httpx's `verify`, which httpx deprecates; the context replaces it without widening the trust.

The handshakes run over memory BIOs, both ends in this process: no socket, no network, no
thread. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import os
import ssl
from pathlib import Path

import pytest

from tests.fakes.tls_handshake import TlsHandshake
from vibey.infrastructure.hub.tls import CERT_FILE, HubCertificate

_hub = TlsHandshake.certificate
_handshake = TlsHandshake.run


def test_the_hubs_own_certificate_is_trusted(tmp_path: Path) -> None:
    hub = _hub(tmp_path / "hub")
    assert _handshake(hub.client_context(), tmp_path / "hub") in {"TLSv1.2", "TLSv1.3"}


def test_a_different_certificate_is_refused(tmp_path: Path) -> None:
    mine = _hub(tmp_path / "mine")
    _hub(tmp_path / "impostor")
    with pytest.raises(ssl.SSLCertVerificationError):
        _handshake(mine.client_context(), tmp_path / "impostor")


def test_the_context_trusts_that_one_certificate_and_checks_the_name(tmp_path: Path) -> None:
    hub = _hub(tmp_path / "hub")
    context = hub.client_context()
    # One certificate in the store, never the system's beside it (a leaf, so not counted a CA).
    assert context.cert_store_stats()["x509"] == 1
    assert context.verify_mode is ssl.CERT_REQUIRED and context.check_hostname
    with pytest.raises(ssl.SSLCertVerificationError):
        _handshake(context, tmp_path / "hub", host="192.0.2.1")  # not a name it carries


def test_a_certificate_that_is_missing_open_to_others_or_a_link_is_never_trusted(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        HubCertificate(tmp_path / "none").client_context()
    _hub(tmp_path / "hub")
    (tmp_path / "hub" / CERT_FILE).chmod(0o644)
    with pytest.raises(PermissionError):
        HubCertificate(tmp_path / "hub").client_context()
    _hub(tmp_path / "real")
    (tmp_path / "linked").mkdir()
    (tmp_path / "linked" / CERT_FILE).symlink_to(tmp_path / "real" / CERT_FILE)
    with pytest.raises(OSError):
        HubCertificate(tmp_path / "linked").client_context()


def test_a_certificate_that_is_not_a_regular_file_is_refused_without_waiting(
    tmp_path: Path,
) -> None:
    """Task 11b review S-2: a FIFO of the account's own (mode 0600) in the certificate's place
    would make a plain `open` wait for a writer forever. It is opened without blocking and
    refused on its `fstat`, as is a folder."""
    state = tmp_path / "fifo"
    state.mkdir(mode=0o700)
    os.mkfifo(state / CERT_FILE, 0o600)
    with pytest.raises(PermissionError, match="not a regular file"):
        HubCertificate(state).client_context()
    folder = tmp_path / "folder"
    (folder / CERT_FILE).mkdir(mode=0o700, parents=True)
    with pytest.raises(PermissionError, match="not a regular file"):
        HubCertificate(folder).client_context()
