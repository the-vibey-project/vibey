# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pairing and trust (ADR-0068): the registry, signed requests, pairing, TLS and mDNS.

The matrix at the heart of it: a paired device's request is admitted only when it is
signed with its own key, fresh, never seen before, and from a device still paired; the
scopes it was granted -- never more -- decide what it may do; and only the host pairs,
lists or revokes. Replays, stale or future timestamps, foreign keys, tampered bodies and
revoked devices are each refused.
"""

import datetime as dt
import hashlib
import hmac
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import asyncpg
import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import HubPrincipal
from vibey.bootstrap import build_app, migrations_dir
from vibey.domain.errors import WrongPhase
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_pairing import HUB_PAIRING, MAX_WRONG_CLAIMS, PairingRefused
from vibey.domain.hub_scope import HubScope
from vibey.domain.ledger import EventKind
from vibey.infrastructure.hub.app import HubAppFactory
from vibey.infrastructure.hub.authenticator import FirstOf, HubRequest, LocalTokenAuthenticator
from vibey.infrastructure.hub.devices import (
    DEVICES_FILE,
    DeviceAuthenticator,
    DeviceRegistry,
    PairedDevice,
)
from vibey.infrastructure.hub.interfaces.devices_interface import DeviceRegistryInterface
from vibey.infrastructure.hub.interfaces.mdns_interface import (
    AdvertisementInterface,
    MdnsAdvertiserInterface,
)
from vibey.infrastructure.hub.interfaces.pairing_interface import (
    HubPairingInterface,
    PairingLedgerInterface,
)
from vibey.infrastructure.hub.interfaces.tls_interface import HubCertificateInterface
from vibey.infrastructure.hub.mdns import SERVICE_TYPE, Advertisement, MdnsAdvertiser, _zeroconf
from vibey.infrastructure.hub.pairing import HubPairing, _device_id, _digits, _key
from vibey.infrastructure.hub.pairing_ledger import PostgresPairingLedger
from vibey.infrastructure.hub.tls import CERT_FILE, KEY_FILE, HubCertificate

TOKEN = "host-t0ken"
HOST = "127.0.0.1:8765"
NOW = 1_000_000.0


class Clock:
    def __init__(self, now: float = NOW) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class Ledger:
    """Records what the pairing service asked the ledger to write."""

    def __init__(self) -> None:
        self.written: list[tuple[EventKind, dict[str, object]]] = []

    async def record(self, kind: EventKind, payload: Any, at: dt.datetime) -> int:
        self.written.append((kind, dict(payload)))
        return 1


def _device(device_id: str = "d1", scopes: frozenset[HubScope] | None = None) -> PairedDevice:
    return PairedDevice(
        device_id=device_id,
        name="phone",
        scopes=scopes if scopes is not None else frozenset({HubScope.VIEW}),
        key="k" * 43,
        paired_at=NOW,
    )


def _signed(
    device: PairedDevice,
    *,
    method: str = "GET",
    path: str = "/api/v1/projects",
    query: str = "",
    body: bytes = b"",
    at: float = NOW,
    nonce: str | None = None,
    key: str | None = None,
) -> dict[str, str]:
    stamp = repr(at)
    nonce = nonce or uuid4().hex
    canonical = HUB_PAIRING.canonical(
        device_id=device.device_id,
        method=method,
        path=path,
        query=query,
        timestamp=stamp,
        nonce=nonce,
        body_sha256=hashlib.sha256(body).hexdigest(),
    )
    signature = hmac.new((key or device.key).encode(), canonical, hashlib.sha256).hexdigest()
    return {
        "x-vibey-device": device.device_id,
        "x-vibey-timestamp": stamp,
        "x-vibey-nonce": nonce,
        "x-vibey-signature": f"sha256={signature}",
    }


def _request(headers: dict[str, str], **fields: Any) -> HubRequest:
    return HubRequest(
        method=fields.get("method", "GET"),
        path=fields.get("path", "/api/v1/projects"),
        query=fields.get("query", ""),
        headers=headers,
        body=fields.get("body", b""),
    )


# --- the registry ---------------------------------------------------------------------


def test_the_registry_meets_its_seam_and_keeps_devices_owner_only(tmp_path: Path) -> None:
    registry = DeviceRegistry(tmp_path / "state")
    assert isinstance(registry, DeviceRegistryInterface)
    assert registry.all() == ()
    registry.add(_device("d1"))
    registry.add(_device("d2", frozenset({HubScope.VIEW, HubScope.ANSWER})))
    path = tmp_path / "state" / DEVICES_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [d.device_id for d in registry.all()] == ["d1", "d2"]
    assert registry.get("d2") == _device("d2", frozenset({HubScope.VIEW, HubScope.ANSWER}))
    assert registry.get("nope") is None
    with pytest.raises(ValueError, match="already paired"):
        registry.add(_device("d1"))
    assert registry.remove("d1") == _device("d1")
    assert registry.remove("d1") is None
    assert [d.device_id for d in registry.all()] == ["d2"]


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"devices": 3}',
        '{"devices": [3]}',
        '{"devices": [{"id": "d", "name": "n", "key": "k", "scopes": "view", "paired_at": 1}]}',
        '{"devices": [{"id": "d", "name": "n", "key": "k", "scopes": [1], "paired_at": 1}]}',
        '{"devices": [{"id": "d", "name": "n", "key": "k", "scopes": [], "paired_at": "x"}]}',
        '{"devices": [{"id": 1, "name": "n", "key": "k", "scopes": [], "paired_at": 1}]}',
        '{"devices": [{"id": "d", "name": 1, "key": "k", "scopes": [], "paired_at": 1}]}',
        '{"devices": [{"id": "d", "name": "n", "key": 1, "scopes": [], "paired_at": 1}]}',
    ],
)
def test_a_malformed_registry_is_refused_never_read_as_empty(tmp_path: Path, content: str) -> None:
    (tmp_path / DEVICES_FILE).write_text(content)
    os.chmod(tmp_path / DEVICES_FILE, 0o600)
    with pytest.raises(ValueError):
        DeviceRegistry(tmp_path).all()


def test_a_registry_others_can_read_or_another_account_owns_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = DeviceRegistry(tmp_path)
    registry.add(_device())
    os.chmod(tmp_path / DEVICES_FILE, 0o644)
    with pytest.raises(PermissionError, match="open to other accounts"):
        registry.all()
    os.chmod(tmp_path / DEVICES_FILE, 0o600)
    monkeypatch.setattr(os, "getuid", lambda: -5)
    with pytest.raises(PermissionError, match="another account"):
        registry.all()


def test_a_symlinked_registry_is_never_followed(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text('{"devices": []}')
    (tmp_path / DEVICES_FILE).symlink_to(elsewhere)
    with pytest.raises(OSError):
        DeviceRegistry(tmp_path).all()


# --- signed requests: the replay and tamper matrix -------------------------------------


def _auth(tmp_path: Path, *devices: PairedDevice, clock: Clock | None = None) -> Any:
    registry = DeviceRegistry(tmp_path)
    for device in devices:
        registry.add(device)
    return DeviceAuthenticator(registry, clock=clock or Clock()), registry


async def test_a_signed_fresh_request_names_the_device_with_its_scopes(tmp_path: Path) -> None:
    device = _device(scopes=frozenset({HubScope.VIEW, HubScope.ANSWER}))
    auth, _ = _auth(tmp_path, device)
    found = await auth.authenticate(_request(_signed(device)))
    assert found == HubPrincipal(name="device:d1", scopes=device.scopes)


async def test_a_replayed_request_is_refused(tmp_path: Path) -> None:
    device = _device()
    auth, _ = _auth(tmp_path, device)
    headers = _signed(device, nonce="once")
    assert await auth.authenticate(_request(headers)) is not None
    assert await auth.authenticate(_request(headers)) is None


@pytest.mark.parametrize("skew", [-61.0, 61.0])
async def test_a_stale_or_future_timestamp_is_refused(tmp_path: Path, skew: float) -> None:
    device = _device()
    auth, _ = _auth(tmp_path, device)
    assert await auth.authenticate(_request(_signed(device, at=NOW + skew))) is None


async def test_what_the_signature_covers_cannot_be_changed(tmp_path: Path) -> None:
    device = _device()
    auth, _ = _auth(tmp_path, device)
    headers = _signed(device, method="POST", path="/api/v1/gates/g/answer", body=b'{"a":1}')
    for changed in (
        {"method": "GET", "path": "/api/v1/gates/g/answer", "body": b'{"a":1}'},
        {"method": "POST", "path": "/api/v1/gates/h/answer", "body": b'{"a":1}'},
        {"method": "POST", "path": "/api/v1/gates/g/answer", "body": b'{"a":2}'},
        {"method": "POST", "path": "/api/v1/gates/g/answer", "body": b'{"a":1}', "query": "x"},
    ):
        assert await auth.authenticate(_request(headers, **changed)) is None
    assert await auth.authenticate(
        _request(headers, method="POST", path="/api/v1/gates/g/answer", body=b'{"a":1}')
    )


async def test_another_devices_key_an_unknown_device_or_missing_headers_prove_nothing(
    tmp_path: Path,
) -> None:
    device = _device("d1")
    auth, _ = _auth(tmp_path, device, PairedDevice("d2", "tab", device.scopes, "o" * 43, NOW))
    assert await auth.authenticate(_request(_signed(device, key="o" * 43))) is None
    assert await auth.authenticate(_request(_signed(_device("ghost")))) is None
    partial = _signed(device)
    del partial["x-vibey-nonce"]
    assert await auth.authenticate(_request(partial)) is None
    assert await auth.authenticate(_request({})) is None
    bad_stamp = dict(_signed(device), **{"x-vibey-timestamp": "soon"})
    assert await auth.authenticate(_request(bad_stamp)) is None
    newline = dict(_signed(device), **{"x-vibey-nonce": "a\nb"})
    assert await auth.authenticate(_request(newline)) is None


async def test_a_revoked_device_is_refused_at_its_very_next_request(tmp_path: Path) -> None:
    device = _device()
    auth, registry = _auth(tmp_path, device)
    assert await auth.authenticate(_request(_signed(device))) is not None
    registry.remove(device.device_id)
    assert await auth.authenticate(_request(_signed(device))) is None


async def test_a_full_nonce_memory_refuses_rather_than_forgets(tmp_path: Path) -> None:
    device = _device()
    clock = Clock()
    registry = DeviceRegistry(tmp_path)
    registry.add(device)
    auth = DeviceAuthenticator(registry, clock=clock, max_nonces=2)
    assert await auth.authenticate(_request(_signed(device, nonce="a")))
    assert await auth.authenticate(_request(_signed(device, nonce="b")))
    assert await auth.authenticate(_request(_signed(device, nonce="c"))) is None
    # Once the remembered nonces are older than any fresh request could be, they go.
    clock.now = NOW + 200
    assert await auth.authenticate(_request(_signed(device, nonce="c", at=clock.now)))


# --- pairing ---------------------------------------------------------------------------


def _pairing(tmp_path: Path, clock: Clock | None = None) -> tuple[HubPairing, Ledger, Any]:
    ledger = Ledger()
    registry = DeviceRegistry(tmp_path)
    codes = iter(["111111", "222222", "333333", "444444"])
    pairing = HubPairing(
        registry,
        ledger,
        clock=clock or Clock(),
        fingerprint="ab" * 32,
        address=("192.168.1.5", 8765),
        digits=lambda: next(codes),
        key=lambda: "the-key",
        device_id=lambda: "dev1",
    )
    return pairing, ledger, registry


async def test_a_claimed_offer_pairs_once_and_is_written_to_the_ledger(tmp_path: Path) -> None:
    pairing, ledger, registry = _pairing(tmp_path)
    assert isinstance(pairing, HubPairingInterface)
    offered = pairing.offer(frozenset({HubScope.VIEW, HubScope.ANSWER}))
    assert offered["code"] == "111111" and offered["scopes"] == ["answer", "view"]
    assert offered["uri"] == (f"vibey-pair://192.168.1.5:8765?fp={'ab' * 32}&code=111111&v=1")
    claimed = await pairing.claim("111111", "Adam's phone")
    assert claimed == {
        "device_id": "dev1",
        "key": "the-key",
        "scopes": ["answer", "view"],
        "fingerprint": "ab" * 32,
    }
    assert registry.get("dev1").name == "Adam's phone"
    assert ledger.written == [
        (
            EventKind.HUB_DEVICE_PAIRED,
            {
                "device_id": "dev1",
                "name": "Adam's phone",
                "scopes": ["answer", "view"],
                "by": "host",
            },
        )
    ]
    assert "the-key" not in repr(ledger.written)
    with pytest.raises(PairingRefused):
        await pairing.claim("111111", "again")
    assert pairing.devices() == [
        {
            "device_id": "dev1",
            "name": "Adam's phone",
            "scopes": ["answer", "view"],
            "paired_at": NOW,
        }
    ]


async def test_an_expired_offer_cannot_be_claimed(tmp_path: Path) -> None:
    clock = Clock()
    pairing, _, _ = _pairing(tmp_path, clock)
    pairing.offer(frozenset({HubScope.VIEW}))
    clock.now += 121
    with pytest.raises(PairingRefused):
        await pairing.claim("111111", "late")
    # A new offer sweeps out the expired one.
    pairing.offer(frozenset({HubScope.VIEW}))
    assert [o.code for o in pairing._offers] == ["222222"]


async def test_enough_wrong_codes_withdraw_every_open_offer(tmp_path: Path) -> None:
    pairing, _, _ = _pairing(tmp_path)
    pairing.offer(frozenset({HubScope.VIEW}))
    for _ in range(MAX_WRONG_CLAIMS):
        with pytest.raises(PairingRefused):
            await pairing.claim("999999", "guesser")
    with pytest.raises(PairingRefused):
        await pairing.claim("111111", "too late")


@pytest.mark.parametrize("name", ["", "x" * 65, "bad\nname"])
async def test_a_device_name_is_short_and_printable(tmp_path: Path, name: str) -> None:
    pairing, _, _ = _pairing(tmp_path)
    pairing.offer(frozenset({HubScope.VIEW}))
    with pytest.raises(PairingRefused):
        await pairing.claim("111111", name)


async def test_revoking_removes_the_device_and_records_it(tmp_path: Path) -> None:
    pairing, ledger, registry = _pairing(tmp_path)
    pairing.offer(frozenset({HubScope.VIEW}))
    await pairing.claim("111111", "phone")
    assert await pairing.revoke("dev1") is True
    assert registry.get("dev1") is None
    assert ledger.written[-1][0] is EventKind.HUB_DEVICE_REVOKED
    assert await pairing.revoke("dev1") is False


def test_the_default_codes_keys_and_ids_are_fresh_and_well_formed() -> None:
    codes = {_digits() for _ in range(50)}
    assert all(len(c) == 6 and c.isdigit() for c in codes) and len(codes) > 1
    assert len(_key()) >= 43 and _key() != _key()
    assert len(_device_id()) == 16 and _device_id() != _device_id()


# --- the HTTP surface ------------------------------------------------------------------


class Service:
    async def projects(self, principal: HubPrincipal) -> Any:
        from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubForbidden

        if not HUB_SCOPES.permits(principal.scopes, HubAction.READ):
            raise HubForbidden("no")
        return {"ran": "projects", "by": principal.name}

    async def answer_gate(
        self, principal: HubPrincipal, gate_id: Any, answer: Any, *, request_id: Any
    ) -> Any:
        from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubForbidden

        if not HUB_SCOPES.permits(principal.scopes, HubAction.ANSWER_GATE):
            raise HubForbidden("no")
        return {"ran": "answer_gate"}


class Quiet:
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def subscribe(self, project_id: Any) -> Any:  # pragma: no cover - never subscribed
        raise AssertionError


def _hub(tmp_path: Path, *, pairing: bool = True) -> tuple[Any, HubPairing, DeviceRegistry]:
    service, ledger, registry = _pairing(tmp_path)

    async def ready() -> bool:
        return True

    app = HubAppFactory().build(
        Service(),  # type: ignore[arg-type]
        authenticator=FirstOf(
            [LocalTokenAuthenticator(TOKEN), DeviceAuthenticator(registry, clock=Clock())]
        ),
        allowed_hosts=HUB_BINDING.allowed_hosts(8765, frozenset()),
        ready=ready,
        live=Quiet(),
        pairing=service if pairing else None,
    )
    return app, service, registry


def _client(app: Any, host: str = HOST) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://{host}")


HOST_AUTH = {"authorization": f"Bearer {TOKEN}"}


async def test_pairing_end_to_end_then_scopes_decide_then_revocation_binds(
    tmp_path: Path,
) -> None:
    app, _, _ = _hub(tmp_path)
    async with _client(app) as client:
        offered = await client.post(
            "/api/v1/pairing/offers", json={"scopes": ["view"]}, headers=HOST_AUTH
        )
        assert offered.status_code == 200, offered.text
        claimed = await client.post(
            "/api/v1/pairing/claim", json={"code": offered.json()["code"], "name": "phone"}
        )
        assert claimed.status_code == 200 and claimed.json()["key"] == "the-key"
        device = PairedDevice("dev1", "phone", frozenset({HubScope.VIEW}), "the-key", NOW)
        read = await client.get("/api/v1/projects", headers=_signed(device))
        assert read.json() == {"ran": "projects", "by": "device:dev1"}
        body = b'{"answer": {"choice": "yes"}}'
        path = f"/api/v1/gates/{uuid4()}/answer"
        answered = await client.post(
            path,
            content=body,
            headers={
                "content-type": "application/json",
                **_signed(device, method="POST", path=path, body=body),
            },
        )
        assert answered.status_code == 403  # granted view, never answer
        # A device can never manage pairings, even its own.
        for method, route, payload in (
            ("POST", "/api/v1/pairing/offers", b'{"scopes": ["view"]}'),
            ("GET", "/api/v1/devices", b""),
            ("DELETE", "/api/v1/devices/dev1", b""),
        ):
            refused = await client.request(
                method,
                route,
                content=payload,
                headers={
                    "content-type": "application/json",
                    **_signed(device, method=method, path=route, body=payload),
                },
            )
            assert refused.status_code == 403, (route, refused.text)
        listed = await client.get("/api/v1/devices", headers=HOST_AUTH)
        assert [d["device_id"] for d in listed.json()] == ["dev1"]
        assert "key" not in listed.json()[0]
        assert (await client.delete("/api/v1/devices/dev1", headers=HOST_AUTH)).status_code == 200
        assert (await client.delete("/api/v1/devices/dev1", headers=HOST_AUTH)).status_code == 404
        gone = await client.get("/api/v1/projects", headers=_signed(device))
        assert gone.status_code == 401


async def test_offers_need_a_scope_and_claims_need_a_real_code(tmp_path: Path) -> None:
    app, _, _ = _hub(tmp_path)
    async with _client(app) as client:
        empty = await client.post("/api/v1/pairing/offers", json={"scopes": []}, headers=HOST_AUTH)
        assert empty.status_code == 422
        unknown = await client.post(
            "/api/v1/pairing/offers", json={"scopes": ["root"]}, headers=HOST_AUTH
        )
        assert unknown.status_code == 422
        nobody = await client.post("/api/v1/pairing/offers", json={"scopes": ["view"]})
        assert nobody.status_code == 401
        wrong = await client.post("/api/v1/pairing/claim", json={"code": "000000", "name": "x"})
        assert wrong.status_code == 403
        short = await client.post("/api/v1/pairing/claim", json={"code": "1", "name": "x"})
        assert short.status_code == 422


async def test_claims_are_rate_limited_per_address(tmp_path: Path) -> None:
    app, _, _ = _hub(tmp_path)
    async with _client(app) as client:
        codes = []
        for _ in range(12):
            response = await client.post(
                "/api/v1/pairing/claim", json={"code": "000000", "name": "x"}
            )
            codes.append(response.status_code)
    assert 429 in codes


async def test_a_hub_without_pairing_says_so(tmp_path: Path) -> None:
    app, _, _ = _hub(tmp_path, pairing=False)
    async with _client(app) as client:
        response = await client.get("/api/v1/devices", headers=HOST_AUTH)
    assert response.status_code == 503


@pytest.mark.parametrize(
    "host", ["evil.example:8765", "attacker.test", "127.0.0.1:9999", "192.168.1.5:8765"]
)
async def test_dns_rebinding_never_reaches_pairing(tmp_path: Path, host: str) -> None:
    """A page that rebinds its own name to 127.0.0.1 sends its own Host: refused (421)
    before any route -- the claim route included, which needs no principal."""
    app, _, _ = _hub(tmp_path)
    async with _client(app, host) as client:
        claim = await client.post("/api/v1/pairing/claim", json={"code": "000000", "name": "x"})
        offer = await client.post(
            "/api/v1/pairing/offers", json={"scopes": ["view"]}, headers=HOST_AUTH
        )
    assert claim.status_code == offer.status_code == 421
    assert "access-control-allow-origin" not in claim.headers


async def test_pairing_sets_no_cookie_so_there_is_no_ambient_credential(tmp_path: Path) -> None:
    """CSRF needs a credential the browser attaches by itself. The hub issues none: every
    credential is a header the caller sets (the host token, a device signature)."""
    app, _, _ = _hub(tmp_path)
    async with _client(app) as client:
        offered = await client.post(
            "/api/v1/pairing/offers", json={"scopes": ["view"]}, headers=HOST_AUTH
        )
        claimed = await client.post(
            "/api/v1/pairing/claim", json={"code": offered.json()["code"], "name": "p"}
        )
    for response in (offered, claimed):
        assert "set-cookie" not in response.headers
        assert "default-src 'none'" in response.headers["content-security-policy"]


# --- TLS -------------------------------------------------------------------------------


def test_the_certificate_is_made_once_owner_only_and_its_fingerprint_is_stable(
    tmp_path: Path,
) -> None:
    certificate = HubCertificate(tmp_path / "state")
    assert isinstance(certificate, HubCertificateInterface)
    at = dt.datetime(2026, 9, 25, tzinfo=dt.UTC)
    first = certificate.ensure(frozenset({"studio.local", "192.168.1.5"}), at)
    again = certificate.ensure(frozenset({"other"}), at)
    assert first == again and len(first.fingerprint) == 64
    for name in (CERT_FILE, KEY_FILE):
        assert stat.S_IMODE((tmp_path / "state" / name).stat().st_mode) == 0o600
    loaded = x509.load_pem_x509_certificate(first.cert_path.read_bytes())
    names = loaded.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "studio.local" in names.get_values_for_type(x509.DNSName)
    assert any(str(ip) == "192.168.1.5" for ip in names.get_values_for_type(x509.IPAddress))
    der = loaded.public_bytes(Encoding.DER)
    assert first.fingerprint == hashlib.sha256(der).hexdigest()


def test_a_certificate_others_can_read_is_refused(tmp_path: Path) -> None:
    certificate = HubCertificate(tmp_path)
    at = dt.datetime(2026, 9, 25, tzinfo=dt.UTC)
    certificate.ensure(frozenset(), at)
    os.chmod(tmp_path / CERT_FILE, 0o644)
    with pytest.raises(PermissionError):
        certificate.ensure(frozenset(), at)


# --- mDNS ------------------------------------------------------------------------------


class FakeZeroconf:
    """Stands in for the `zeroconf` module: records what was registered and withdrawn."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.info: Any = None
        fake = self

        class ServiceInfo:
            def __init__(self, type_: str, name: str, **fields: Any) -> None:
                fake.info = SimpleNamespace(type=type_, name=name, **fields)

        class AsyncZeroconf:
            async def async_register_service(self, info: Any) -> None:
                fake.events.append("register")

            async def async_unregister_service(self, info: Any) -> None:
                fake.events.append("unregister")

            async def async_close(self) -> None:
                fake.events.append("close")

        self.ServiceInfo = ServiceInfo
        self.asyncio = SimpleNamespace(AsyncZeroconf=AsyncZeroconf)


async def test_the_hub_is_advertised_as_vibey_tcp_with_its_fingerprint() -> None:
    fake = FakeZeroconf()
    advertiser = MdnsAdvertiser(module=lambda: fake)
    assert isinstance(advertiser, MdnsAdvertiserInterface)
    advert = await advertiser.advertise(
        instance="studio",
        server="studio.local",
        port=8765,
        addresses=["127.0.0.1", "192.168.1.5"],
        fingerprint="ab12",
        api_version="1",
    )
    assert isinstance(advert, AdvertisementInterface) and isinstance(advert, Advertisement)
    assert fake.info.type == SERVICE_TYPE == "_vibey._tcp.local."
    assert fake.info.name == "studio._vibey._tcp.local."
    assert fake.info.server == "studio.local."
    assert fake.info.port == 8765
    assert fake.info.addresses == [bytes([192, 168, 1, 5])]  # loopback never announced
    assert fake.info.properties == {"fp": "ab12", "api": "1", "tls": "1"}
    await advert.close()
    assert fake.events == ["register", "unregister", "close"]


async def test_a_loopback_only_hub_is_never_advertised() -> None:
    advertiser = MdnsAdvertiser(module=lambda: pytest.fail("zeroconf must not load"))
    with pytest.raises(ValueError, match="loopback"):
        await advertiser.advertise(
            instance="s",
            server="s",
            port=1,
            addresses=["127.0.0.1", "::1"],
            fingerprint="f",
            api_version="1",
        )


def test_lan_addresses_and_the_instance_name() -> None:
    names = frozenset({"studio.local", "127.0.0.1", "192.168.1.5", "fe80::1", "::1"})
    assert MdnsAdvertiser.lan_addresses(names) == ["192.168.1.5", "fe80::1"]
    assert MdnsAdvertiser.instance()


def test_the_real_zeroconf_module_loads_lazily() -> None:
    module = _zeroconf()
    assert hasattr(module, "ServiceInfo") and hasattr(module.asyncio, "AsyncZeroconf")


# --- the ledger, against real Postgres -------------------------------------------------


@pytest.fixture
async def _an_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    conn = await asyncpg.connect(owner)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()
    await TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir())
    monkeypatch.setenv("VIBEY_PG_URL", os.environ["VIBEY_TEST_APP_DATABASE_URL"])


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_pairing_is_written_to_every_projects_ledger(tmp_path: Path) -> None:
    async with build_app() as resources:
        first = await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        second = await resources.projects.create("b", tmp_path / "b", max_cycles=1, config={})
        ledger = PostgresPairingLedger(resources.ledger._pool)
        assert isinstance(ledger, PairingLedgerInterface)
        at = dt.datetime(2026, 9, 25, tzinfo=dt.UTC)
        payload = {"device_id": "d1", "name": "phone", "scopes": ["view"], "by": "host"}
        assert await ledger.record(EventKind.HUB_DEVICE_PAIRED, payload, at) == 2
        for project in (first, second):
            events = await resources.ledger.all_for_project(project.project_id)
            paired = [e for e in events if e.kind is EventKind.HUB_DEVICE_PAIRED]
            assert len(paired) == 1 and paired[0].payload == payload


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_project_in_an_unknown_phase_refuses_the_whole_pairing(tmp_path: Path) -> None:
    async with build_app() as resources:
        await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})

        class Rows:
            def to_record(self, row: Any) -> Any:
                return SimpleNamespace(project_id=row["id"], cycle=1, phase=_Unknown())

        ledger = PostgresPairingLedger(resources.ledger._pool, rows=Rows())  # type: ignore[arg-type]
        with pytest.raises(WrongPhase):
            await ledger.record(EventKind.HUB_DEVICE_PAIRED, {}, dt.datetime.now(dt.UTC))


class _Unknown:
    value = "FUTURE"
