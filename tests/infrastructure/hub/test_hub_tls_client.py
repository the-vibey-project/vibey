# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`HubCertificate.client_context`: a client trusts the hub's own certificate and nothing else
(SP-ACP Task 11b). `vibey hub pair` and the MCP/ACP gateway used to pass the certificate's path
as httpx's `verify`, which httpx deprecates; the context replaces it without widening the trust.

The handshakes run over memory BIOs, both ends in this process: no socket, no network, no
thread. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import datetime as _dt
import ssl
from pathlib import Path

import pytest

from vibey.infrastructure.hub.tls import CERT_FILE, KEY_FILE, HubCertificate

NOW = _dt.datetime(2026, 11, 22, tzinfo=_dt.UTC)


def _hub(state: Path) -> HubCertificate:
    certificate = HubCertificate(state)
    certificate.ensure(frozenset({"127.0.0.1"}), NOW)
    return certificate


def _handshake(client: ssl.SSLContext, server_state: Path, host: str = "127.0.0.1") -> None:
    """A TLS handshake between `client` and a server presenting `server_state`'s certificate."""
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(server_state / CERT_FILE, server_state / KEY_FILE)
    to_server, to_client = ssl.MemoryBIO(), ssl.MemoryBIO()
    s_in, s_out = ssl.MemoryBIO(), ssl.MemoryBIO()
    tls_client = client.wrap_bio(to_client, to_server, server_hostname=host)
    tls_server = server_context.wrap_bio(s_in, s_out, server_side=True)
    client_done = server_done = False
    for _ in range(20):
        if not client_done:
            try:
                tls_client.do_handshake()
                client_done = True
            except ssl.SSLWantReadError:
                pass
        s_in.write(to_server.read())
        if not server_done:
            try:
                tls_server.do_handshake()
                server_done = True
            except (ssl.SSLWantReadError, ssl.SSLError):
                pass
        to_client.write(s_out.read())
        if client_done and server_done:
            return
    raise AssertionError("the handshake never finished")


def test_the_hubs_own_certificate_is_trusted(tmp_path: Path) -> None:
    hub = _hub(tmp_path / "hub")
    _handshake(hub.client_context(), tmp_path / "hub")


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
