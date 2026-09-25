# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's own TLS certificate, and the fingerprint a paired device pins (ADR-0068).

No public authority can vouch for a laptop on a home network, so the hub makes its own
certificate on first run: a P-256 key and a self-signed certificate naming the names this
computer answers to. A device does not trust it because of who signed it; it trusts it
because the pairing QR code, which the person holding the device scanned off the host's
own screen, carries its SHA-256 fingerprint (`fingerprint`). Any other certificate on the
same address -- a rebinding page's, a neighbour's -- is refused by the device.

Both files are written owner-only (0600) into the hub's 0700 state directory, created
exclusively and never through a symlink, beside the host token. ADR-0068 names OpenBao
(`SecretsPort`) as where the key should live; until a store is wired into `vibey serve`,
the file has the host token's protection and no less.
"""

import datetime as _dt
import hashlib
import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CERT_FILE: Final = "hub-cert.pem"
KEY_FILE: Final = "hub-key.pem"
VALID_DAYS: Final = 825
"""How long the certificate is valid: the longest a client platform accepts for a leaf."""


@dataclass(frozen=True, slots=True)
class HubTls:
    """The certificate and key files `uvicorn` serves with, and the pinned fingerprint."""

    cert_path: Path
    key_path: Path
    fingerprint: str


class HubCertificate:
    """Makes the hub's certificate once, and reads it after.

    Declared by `interfaces/tls_interface.py::HubCertificateInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir

    def ensure(self, names: frozenset[str], now: _dt.datetime) -> HubTls:
        """The certificate, made on first call for `names`; later calls read the one made."""
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        cert_path, key_path = self._dir / CERT_FILE, self._dir / KEY_FILE
        if not cert_path.exists():
            key = ec.generate_private_key(ec.SECP256R1())
            self._write(
                key_path,
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                ),
            )
            self._write(cert_path, self._certificate(key, names, now))
        pem = self._read(cert_path)
        return HubTls(cert_path=cert_path, key_path=key_path, fingerprint=self.fingerprint(pem))

    @staticmethod
    def fingerprint(pem: bytes) -> str:
        """The SHA-256 of the certificate's DER encoding, as lower-case hex."""
        der = x509.load_pem_x509_certificate(pem).public_bytes(serialization.Encoding.DER)
        return hashlib.sha256(der).hexdigest()

    @staticmethod
    def _certificate(
        key: ec.EllipticCurvePrivateKey, names: frozenset[str], now: _dt.datetime
    ) -> bytes:
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "vibey hub")])
        alternatives: list[x509.GeneralName] = []
        for name in sorted(names | {"localhost", "127.0.0.1", "::1"}):
            try:
                alternatives.append(x509.IPAddress(ipaddress.ip_address(name)))
            except ValueError:
                alternatives.append(x509.DNSName(name))
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - _dt.timedelta(minutes=5))
            .not_valid_after(now + _dt.timedelta(days=VALID_DAYS))
            .add_extension(x509.SubjectAlternativeName(alternatives), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        return certificate.public_bytes(serialization.Encoding.PEM)

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)

    @staticmethod
    def _read(path: Path) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            status = os.fstat(handle.fileno())
            if status.st_uid != os.getuid() or status.st_mode & 0o077:
                raise PermissionError(f"{path} is not this account's alone; refusing to use it")
            return handle.read()
