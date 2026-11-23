# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A real TLS handshake with both ends in the test process, over memory BIOs: no socket, no
network, no thread (SP-ACP Task 11b). Shared by the tests that prove which certificate a client
context trusts -- the hub's own one, and not another."""

from __future__ import annotations

import datetime as _dt
import ssl
from pathlib import Path

from vibey.infrastructure.hub.tls import CERT_FILE, KEY_FILE, HubCertificate


class TlsHandshake:
    """Handshakes between a client context and a hub state folder's certificate."""

    NOW = _dt.datetime(2026, 11, 22, tzinfo=_dt.UTC)

    @classmethod
    def certificate(cls, state: Path) -> HubCertificate:
        """The hub's own certificate in `state`, as `vibey serve` makes it."""
        certificate = HubCertificate(state)
        certificate.ensure(frozenset({"127.0.0.1"}), cls.NOW)
        return certificate

    @staticmethod
    def run(client: ssl.SSLContext, server_state: Path, host: str = "127.0.0.1") -> str | None:
        """A handshake between `client` and a server presenting `server_state`'s certificate;
        the protocol version the client settled on. A refusal raises `ssl.SSLError`."""
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
                return tls_client.version()
        raise AssertionError("the handshake never finished")

    @classmethod
    def trusts_only(cls, client: ssl.SSLContext, state: Path, elsewhere: Path) -> bool:
        """Whether `client` accepts `state`'s certificate and refuses a fresh one made in
        `elsewhere`: the context is pinned to that state folder's own certificate."""
        if cls.run(client, state) not in {"TLSv1.2", "TLSv1.3"}:
            return False
        cls.certificate(elsewhere)
        try:
            cls.run(client, elsewhere)
        except ssl.SSLCertVerificationError:
            return True
        return False
