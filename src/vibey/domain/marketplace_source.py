# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which marketplace sources vibey fetches, and how: its pure half (SP-LOOPS Task 7).

`vibey loops marketplace add NAME SOURCE` records a source and `marketplace update` fetches it.
git reads far more than URLs as a place to fetch from -- `ext::<command>` runs a command, any
`<helper>::<address>` starts a transport helper, `file://` and a bare path read a repository on
this computer, and an argument that starts with `-` is an option -- so a source is classified here,
against an allowlist, before anything is written or run:

- **git**, over one of two protocols: an `https://` URL with a host and no credentials (a token in
  the URL would be written into `vibey.toml`), or ssh -- an `ssh://` URL with a host (a plain user
  name is fine: letters, digits, `.`, `_`, `-`, starting with a letter or digit, never
  %-encoded; a password is not) or the scp-like `user@host:path`. Infrastructure hands git only
  these, after `--`, with `protocol.allow=never` and these two allowed. `git://` is refused like
  `http://`: both are plaintext with no integrity, so an on-path attacker could serve any tree.
- **local**: an absolute folder path. It is copied without git, so git never reads a local
  repository. A relative path is refused: it would be read from the folder vibey runs in, which
  may be a project's.

Everything else -- `file://`, `http://`, `git://`, a `<helper>::`, a relative or `~` path, a leading `-`, a host
that is not a plain name or address, whitespace, control characters -- is a
`MarketplaceSourceError` naming why (a `::` is refused where git would read it as a helper: right
after the leading scheme characters, so an IPv6 host such as `https://[::1]/x` is still a URL). A
ref is held to a plain-name subset of
`git check-ref-format` (no `..`, `:`, `^`, `~`, `@{`, `//`, leading `-`, `+` or `/`, trailing
`/` or `.lock`), so it can never be read as an option or a refspec.

Pure: no I/O. Declared by `interfaces/marketplace_source_interface.py`.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Final, Literal
from urllib.parse import urlsplit

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError

SourceKind = Literal["git", "local"]
SourceProtocol = Literal["https", "ssh", "local"]
GIT_PROTOCOLS: Final[tuple[SourceProtocol, ...]] = ("https", "ssh")
"""The only protocols git is allowed for a marketplace (its `protocol.<name>.allow`)."""
REF_MAX_CHARS: Final = 255
_REF: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
_HELPER: Final = re.compile(r"[A-Za-z0-9+.-]*::")
"""git's own test for a transport helper (`transport.c`): scheme characters, then `::`."""
_COMMIT: Final = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_HOST: Final = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?")
_SCP: Final = re.compile(
    r"(?P<user>[A-Za-z0-9._-]+)@(?P<host>[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)"
    r":(?P<path>[A-Za-z0-9._~][^:]*)"
)
_USER: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
"""A user name in an `ssh://` URL: the shape `_SCP` holds a user to, so it can never be read as
an ssh option."""
_SCHEMES: Final[dict[str, SourceProtocol]] = {"https": "https", "ssh": "ssh"}
REFUSED: Final = (
    "is not a source vibey fetches: give an https:// or ssh:// URL, user@host:path, or an "
    "absolute folder path (file://, http://, git://, transport helpers and relative paths are "
    "refused)"
)


class MarketplaceSourceError(ValueError):
    """A source or ref vibey will not fetch; the message says why."""


@dataclass(frozen=True, slots=True)
class MarketplaceSource:
    """A source as `classify` read it. A value type (ADR-0016 exempts it)."""

    text: str
    kind: SourceKind
    protocol: SourceProtocol


class MarketplaceSourceRule:
    """Declared by `interfaces/marketplace_source_interface.py::MarketplaceSourceRuleInterface`."""

    def classify(self, source: str) -> MarketplaceSource:
        try:
            text = BundleSpec.option_safe_text(source, "source")
        except BundleError as exc:
            raise MarketplaceSourceError(str(exc)) from exc
        if _HELPER.match(text):
            raise MarketplaceSourceError(
                f"source {text!r} names a git transport helper (`<helper>::`), which can run a "
                "command; it is refused"
            )
        if any(char.isspace() for char in text):
            raise MarketplaceSourceError(f"source {text!r} {REFUSED}")
        if text.startswith("/"):
            if ".." in text.split("/"):
                raise MarketplaceSourceError(f"source {text!r} must not hold '..'")
            return MarketplaceSource(text, "local", "local")
        scheme, separator, _ = text.partition("://")
        if separator and scheme in _SCHEMES:
            return MarketplaceSource(text, "git", self._url(text, _SCHEMES[scheme]))
        if not separator and _SCP.fullmatch(text):
            return MarketplaceSource(text, "git", "ssh")
        raise MarketplaceSourceError(f"source {text!r} {REFUSED}")

    def check_ref(self, ref: str) -> str:
        why = (
            f"the ref {ref!r} must be a plain branch, tag or commit name: letters, digits, '.', "
            f"'_', '-' and '/', starting with a letter or digit, at most {REF_MAX_CHARS} "
            "characters, with no '..', '//', or trailing '/' or '.lock'"
        )
        if (
            len(ref) > REF_MAX_CHARS
            or _REF.fullmatch(ref) is None
            or ".." in ref
            or "//" in ref
            or ref.endswith(("/", ".lock"))
        ):
            raise MarketplaceSourceError(why)
        return ref

    def is_commit(self, ref: str) -> bool:
        return _COMMIT.fullmatch(ref) is not None

    @staticmethod
    def _url(text: str, protocol: SourceProtocol) -> SourceProtocol:
        try:
            parts = urlsplit(text)
            host = parts.hostname
            user, password = parts.username, parts.password
            parts.port  # noqa: B018 - raises ValueError for a port that is not a number in range
        except ValueError as exc:
            raise MarketplaceSourceError(f"source {text!r} must be a URL with a host") from exc
        if not host or not MarketplaceSourceRule._plain_host(host):
            raise MarketplaceSourceError(f"source {text!r} must be a URL with a host")
        if password is not None or (protocol == "https" and user is not None):
            raise MarketplaceSourceError(
                f"source {text!r} must not carry credentials (they would be written into "
                "vibey.toml); use ssh with your agent, or a URL without them"
            )
        userinfo = parts.netloc.rpartition("@")[0]
        if user is not None and ("%" in userinfo or not _USER.fullmatch(user)):
            raise MarketplaceSourceError(
                f"source {text!r} must name a plain user: letters, digits, '.', '_' and '-', "
                "starting with a letter or digit, never %-encoded"
            )
        return protocol

    @staticmethod
    def _plain_host(host: str) -> bool:
        if _HOST.fullmatch(host):
            return True
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            return False
        return True


MARKETPLACE_SOURCE_RULE: Final = MarketplaceSourceRule()
