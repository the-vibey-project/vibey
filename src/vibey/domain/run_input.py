# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run input: one pasted text or one file a person gives every BUILD run of a project
(SP-LOOPS Phase 3; design Goal 4 and Decision 6).

A run input is stored once under its digest, the lowercase hex SHA-256 of its bytes, and the
ledger records that digest, its kind and its size, never its content. Its name is what a run
sees it as (the file's base name; `paste` for a paste), so a name is held to one path segment:
not empty, not `.` or `..`, no `/`, `\\` or NUL, writable as UTF-8 and at most `NAME_MAX_BYTES`
UTF-8 bytes. Any other character, a control character included, is allowed and escaped wherever
it is shown.

Pure: no I/O. Declared by `interfaces/run_input_interface.py::RunInputRuleInterface`.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal, cast
from urllib.parse import urlsplit

from vibey.domain.interfaces.run_input_interface import RunInputRuleInterface

InputKind = Literal["paste", "file"]
INPUT_KINDS: Final[tuple[InputKind, ...]] = ("paste", "file")
NAME_MAX_BYTES: Final = 255
"""The longest a run input's name may be, in UTF-8 bytes: the common file-name limit."""
_DIGEST: Final = re.compile(r"[0-9a-f]{64}")

GIVEN_ARTIFACT_TYPE: Final = "vibey_run_inputs_given"
"""The artifact type of the ledger event recording the digests one BUILD run was given."""
HANDOFF_INPUTS_KEY: Final = "handoff_input_digests"
"""The key of a wind-down follow-up's payload that pins the digests the outgoing run was given,
so the handed-off run is given exactly those (SP-LOOPS Phase 3c, Task 7)."""

StoreKind = Literal["local", "seaweedfs"]
STORE_KINDS: Final[tuple[StoreKind, ...]] = ("local", "seaweedfs")
_BUCKET: Final = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
_PREFIX_SEGMENT: Final = re.compile(r"[A-Za-z0-9._-]+")
_ENV_NAME: Final = re.compile(r"[A-Z_][A-Z0-9_]*")
_REGION: Final = re.compile(r"[A-Za-z0-9_-]{1,64}")
_LOOPBACK_NAMES: Final = frozenset({"localhost"})
_CREDENTIAL_KEYS: Final = frozenset({"access_key", "secret_key", "password", "token"})
_LIMIT_KEYS: Final = frozenset(
    {"max_item_bytes", "max_project_bytes", "max_items", "max_prompt_bytes"}
)
_REMOTE_KEYS: Final = frozenset(
    {
        "endpoint",
        "bucket",
        "prefix",
        "region",
        "access_key_env",
        "secret_key_env",
        "timeout_seconds",
        "max_listed_rows",
    }
)
_STORE_KEYS: Final = frozenset({"store", "store_dir"}) | _REMOTE_KEYS


@dataclass(frozen=True, slots=True)
class InputStoreLocation:
    """Where a person's run inputs are stored (`[inputs] store` and its keys; ADR-0105).

    `local` is the person's state folder, or the absolute `store_dir` they name. `seaweedfs` is a
    bucket on an S3 endpoint they name, reached with the two credentials held in the environment
    variables `access_key_env` and `secret_key_env` -- never in `vibey.toml`. Every field is a
    key and these are its defaults (ADR-0018). Constructing one that breaks a rule raises
    `ValueError`, and no message carries a credential or an endpoint's user info."""

    kind: StoreKind = "local"
    store_dir: str | None = None
    endpoint: str | None = None
    bucket: str | None = None
    prefix: str = "vibey/inputs"
    region: str = "us-east-1"
    access_key_env: str = "VIBEY_INPUTS_ACCESS_KEY"
    secret_key_env: str = "VIBEY_INPUTS_SECRET_KEY"
    timeout_seconds: float = 10.0
    max_listed_rows: int = 1024
    """The most index rows one listing of a project reads from a SeaweedFS store: a bound on the
    requests a run makes when another writer of a shared bucket plants rows (16 times the
    default `max_items`). A listing past it is refused, never read in part."""

    def __post_init__(self) -> None:
        if self.kind not in STORE_KINDS:
            raise ValueError(
                f"[inputs] store must be one of {', '.join(STORE_KINDS)}, not "
                f"{ascii(self.kind)[:64]}"
            )
        if self.kind == "local":
            if self.endpoint is not None or self.bucket is not None:
                raise ValueError(
                    '[inputs] endpoint and bucket are for store = "seaweedfs"; a local store '
                    "has neither"
                )
            if self.store_dir is not None and not self.store_dir.startswith("/"):
                raise ValueError(
                    f"[inputs] store_dir must be an absolute path, not {ascii(self.store_dir)[:128]}"
                )
        else:
            if self.store_dir is not None:
                raise ValueError('[inputs] store_dir is for store = "local" only')
            if self.endpoint is None or self.bucket is None:
                raise ValueError('[inputs] store = "seaweedfs" needs an endpoint and a bucket')
            _check_endpoint(self.endpoint)
            if _BUCKET.fullmatch(self.bucket) is None:
                raise ValueError(
                    f"[inputs] bucket {ascii(self.bucket)[:72]} is not an S3 bucket name "
                    "(3 to 63 of a-z, 0-9, '.' and '-', starting and ending with a letter or digit)"
                )
        for segment in self.prefix.split("/"):
            if segment in {"", ".", ".."} or _PREFIX_SEGMENT.fullmatch(segment) is None:
                raise ValueError(
                    f"[inputs] prefix {ascii(self.prefix)[:128]} must be '/'-separated segments "
                    "of A-Z, a-z, 0-9, '.', '_' and '-', none empty, '.' or '..'"
                )
        if _REGION.fullmatch(self.region) is None:
            raise ValueError(f"[inputs] region {ascii(self.region)[:72]} is not a region name")
        for key, name in (
            ("access_key_env", self.access_key_env),
            ("secret_key_env", self.secret_key_env),
        ):
            if _ENV_NAME.fullmatch(name) is None or _looks_like_a_key(name):
                # The value is never repeated: a person who wrote the credential itself where
                # its variable's name belongs would otherwise see it in an error and a log.
                raise ValueError(
                    f"[inputs] {key} must name an environment variable (A-Z, 0-9 and '_', not "
                    "starting with a digit, and not a key itself); the value given is not shown"
                )
        timeout = self.timeout_seconds
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int | float)
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError(
                f"[inputs] timeout_seconds must be a positive number, not {ascii(timeout)[:32]}"
            )

        rows = self.max_listed_rows
        if isinstance(rows, bool) or not isinstance(rows, int) or rows < 1:
            raise ValueError(
                f"[inputs] max_listed_rows must be a positive integer, not {ascii(rows)[:32]}"
            )

    def describe(self) -> str:
        """The store in words for doctor and errors: scheme, host, bucket and prefix, or the
        local folder. Never a credential (none is held here) and never user info (refused)."""
        if self.kind == "local":
            where = self.store_dir if self.store_dir is not None else "your state folder"
            return f"local store at {where}"
        endpoint = cast(str, self.endpoint).rstrip("/")
        return f"seaweedfs store {endpoint}/{self.bucket}/{self.prefix}"

    @classmethod
    def from_table(cls, table: Mapping[str, object]) -> InputStoreLocation:
        """The location an `[inputs]` table's store keys declare, each missing key its default.
        A key that would do nothing for the chosen store is refused, so a typo cannot hide."""
        store = table.get("store", "local")
        if not isinstance(store, str) or store not in STORE_KINDS:
            raise ValueError(
                f"[inputs] store must be one of {', '.join(STORE_KINDS)}, not {ascii(store)[:64]}"
            )
        present = sorted(key for key in table if key in _STORE_KEYS - {"store"})
        idle = (
            [key for key in present if key in _REMOTE_KEYS]
            if store == "local"
            else [key for key in present if key == "store_dir"]
        )
        if idle:
            raise ValueError(
                f"[inputs] {', '.join(idle)} does nothing with store = {store!r}; remove it or "
                "change store"
            )
        values: dict[str, object] = {"kind": store}
        for key in ("store_dir", "endpoint", "bucket", "prefix", "region"):
            if key in table:
                value = table[key]
                if not isinstance(value, str):
                    raise ValueError(f"[inputs] {key} must be a string")
                values[key] = value.rstrip("/") if key == "endpoint" else value
        for key in ("access_key_env", "secret_key_env"):
            if key in table:
                value = table[key]
                if not isinstance(value, str):
                    raise ValueError(f"[inputs] {key} must be a string")
                values[key] = value
        for key in ("timeout_seconds", "max_listed_rows"):
            if key in table:
                values[key] = table[key]
        return cls(**values)  # type: ignore[arg-type]  # each value is checked in __post_init__


def _check_endpoint(endpoint: str) -> None:
    """Refuses an endpoint that is not `http(s)://host[:port]`. Module-level: one rule used by
    one constructor, with no state; a class would add a name and nothing else. The messages never
    repeat the endpoint, which could carry user info (a credential)."""
    rule = (
        "[inputs] endpoint must be http(s)://host[:port] with no user info, path, query or fragment"
    )
    try:
        parts = urlsplit(endpoint)
        _ = parts.port  # read only so that a port that is not a number raises here
    except ValueError:
        raise ValueError(rule) from None
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError(rule)
    if "@" in parts.netloc or parts.path not in {"", "/"} or parts.query or parts.fragment:
        raise ValueError(rule)
    if parts.scheme == "http" and not _is_loopback(parts.hostname):
        raise ValueError(
            "[inputs] endpoint may use plain http only for localhost, 127.0.0.1 or ::1; "
            "credentials are never sent over plain http to another host"
        )


def _looks_like_a_key(name: str) -> bool:
    """Whether a would-be variable name looks like a credential instead: 16 or more characters
    with no `_` (an access key id such as `AKIA...` is 20 upper-case letters and digits), or more
    than 64. Module-level for the same reason as `_check_endpoint`: one rule, one caller."""
    return (len(name) >= 16 and "_" not in name) or len(name) > 64


def _is_loopback(host: str) -> bool:
    """Whether `host` is this machine by name or address. Module-level for the same reason as
    `_check_endpoint`, which is its one caller."""
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host) in {
            ipaddress.ip_address("127.0.0.1"),
            ipaddress.ip_address("::1"),
        }
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class RunInput:
    """One stored run input as the index records it: no content."""

    digest: str
    kind: InputKind
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class InputListing:
    """A project's run inputs in the order they were added, and how many index lines could not
    be read (a torn last line after a crash, say) and were skipped rather than raised."""

    items: tuple[RunInput, ...]
    skipped: int


@dataclass(frozen=True, slots=True)
class StoreProbe:
    """What one probe of a run input store found (`vibey doctor`'s `run-inputs` line): whether it
    answered as a store should, and the words that say so. Never a credential."""

    reachable: bool
    detail: str


@dataclass(frozen=True, slots=True)
class RunInputsSettings:
    """`[inputs]`: how much a project's run inputs may hold (ADR-0018: each a key, these its
    defaults). Read only from the person's own `vibey.toml`; a project's file is never heard."""

    max_item_bytes: int = 1_048_576
    """The largest one pasted text or file may be (1 MiB)."""
    max_project_bytes: int = 8_388_608
    """The most all of one project's inputs may hold together (8 MiB)."""
    max_items: int = 64
    """The most inputs one project may have."""
    max_prompt_bytes: int = 65_536
    """The most pasted text (UTF-8 bytes, all pastes together) inlined into a run's prompt; a
    paste past it is named, with its path in the run's `paste.md`, instead (64 KiB: a 32k-token
    model's context stays usable)."""
    store: InputStoreLocation = field(default_factory=InputStoreLocation)
    """Where the inputs are stored: `store` and its keys (ADR-0105)."""

    @classmethod
    def from_table(cls, table: Mapping[str, object]) -> RunInputsSettings:
        """The settings an `[inputs]` table declares, each missing key its default. Raises
        `ValueError` naming the key for an unknown key, a value that is not a positive integer
        (a bool is not one), a `max_item_bytes` over `max_project_bytes`, and every store rule of
        `InputStoreLocation`. A credential key is refused first, and its value is never echoed."""
        defaults = cls()
        held = sorted(key for key in table if key in _CREDENTIAL_KEYS)
        if held:
            raise ValueError(
                f"[inputs] holds no credential ({', '.join(held)}); name the environment "
                "variable in access_key_env / secret_key_env"
            )
        known = _LIMIT_KEYS | _STORE_KEYS
        for key in table:
            if key not in known:
                raise ValueError(
                    f"[inputs] {ascii(key)[:64]} is not a setting; the keys are "
                    f"{', '.join(sorted(known))}"
                )
        store = InputStoreLocation.from_table(
            {key: value for key, value in table.items() if key in _STORE_KEYS}
        )
        values: dict[str, int] = {}
        for key in sorted(_LIMIT_KEYS):
            value = table.get(key, getattr(defaults, key))
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"[inputs] {key} must be a positive integer, not {value!r}")
            values[key] = value
        if values["max_item_bytes"] > values["max_project_bytes"]:
            raise ValueError(
                f"[inputs] max_item_bytes ({values['max_item_bytes']}) is more than "
                f"max_project_bytes ({values['max_project_bytes']})"
            )
        return cls(**values, store=store)


class RunInputRule:
    """Declared by `interfaces/run_input_interface.py::RunInputRuleInterface`."""

    def digest_of(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def valid_name(self, name: str, *, max_bytes: int = NAME_MAX_BYTES) -> str | None:
        if not name:
            return "is empty"
        if name in {".", ".."}:
            return f"{name!r} names a folder, not a file"
        if "/" in name or "\\" in name:
            return "contains a path separator"
        if "\x00" in name:
            return "contains a NUL"
        try:
            size = len(name.encode("utf-8"))
        except UnicodeEncodeError:
            return "is not text that can be written as UTF-8"
        if size > max_bytes:
            return f"is {size} bytes long; at most {max_bytes} are allowed"
        return None

    def is_digest(self, text: str) -> bool:
        return _DIGEST.fullmatch(text) is not None

    def name_digest(self, name: str) -> str:
        return hashlib.sha256(name.encode("utf-8", errors="surrogatepass")).hexdigest()

    def row_of(self, line: bytes) -> RunInput | None:
        try:
            row = json.loads(line)
        except ValueError:  # not JSON, or not UTF-8
            return None
        if not isinstance(row, dict):
            return None
        digest, kind, name, size = (row.get(key) for key in ("digest", "kind", "name", "size"))
        if not (isinstance(digest, str) and self.is_digest(digest)):
            return None
        if kind not in INPUT_KINDS or not isinstance(name, str):
            return None
        if self.valid_name(name) is not None:
            return None  # an index is data a person or a bucket's writer can edit: check names
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return None
        return RunInput(digest=digest, kind=cast(InputKind, kind), name=name, size=size)


RUN_INPUT_RULE: Final[RunInputRuleInterface] = RunInputRule()
"""The one rule. Annotated with the interface so `mypy --strict` checks the class against it."""
digest_of: Final = RUN_INPUT_RULE.digest_of
"""`RUN_INPUT_RULE.digest_of`, under the name the run input plan gives it."""
valid_name: Final = RUN_INPUT_RULE.valid_name
"""`RUN_INPUT_RULE.valid_name`, under the name the run input plan gives it."""
