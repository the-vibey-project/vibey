# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/macos_app_bundle.py` implements. Interfaces declare; they never consume.

A *runner* runs one command; it is the one place the bundler touches the system, so every
other class is exercised over a fake one. A *Mach-O reader* reports what one Mach-O file
links and where it looks. A *closure* finds every library a set of files needs that the
operating system does not provide. A *bundler* turns a `meson install` into a `.app`; a
*verifier* proves a finished bundle names nothing outside itself; a *signer* signs it; a
*disk imager* puts it in a `.dmg`; a *notariser* has Apple notarise and staple it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class CommandRunnerInterface(Protocol):
    """Runs one command and returns its standard output."""

    def run(self, argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
        """The command's standard output; raises when it exits non-zero."""
        ...


class MachOReaderInterface(Protocol):
    """What one Mach-O file is, from its load commands."""

    def is_macho(self, path: Path) -> bool:
        """True when `path` is a Mach-O executable, library or bundle."""
        ...

    def read(self, path: Path) -> Any:
        """Its install id, the libraries it loads, its run paths and its minimum macOS."""
        ...


class DylibClosureInterface(Protocol):
    """Every non-system library a set of Mach-O files needs, transitively."""

    def close(self, roots: Sequence[Path]) -> Mapping[Path, str]:
        """Each needed library's real path, mapped to the name it is bundled under."""
        ...


class AppBundlerInterface(Protocol):
    """A `meson install` of krypton desktop, made into a self-contained `.app`."""

    def bundle(self, *, prefix: Path, build_dir: Path, homebrew: Path, out: Path) -> Path:
        """The `.app` written under `out`, ad-hoc signed so that it runs."""
        ...


class BundleVerifierInterface(Protocol):
    """Proves a finished `.app` stands on its own."""

    def problems(self, app: Path) -> list[str]:
        """Each reference outside the bundle, unresolved library or missing key; empty when none."""
        ...


class SignerInterface(Protocol):
    """Signs every Mach-O file in a bundle, innermost first, then the bundle."""

    def sign(self, app: Path, identity: str, *, keychain: Path | None = None) -> None:
        """Signs with `identity` ("-" for ad-hoc), with the hardened runtime when not ad-hoc."""
        ...


class DiskImagerInterface(Protocol):
    """Puts a bundle in a compressed disk image, with a link to /Applications beside it."""

    def create(self, app: Path, out: Path, *, volume_name: str) -> Path:
        """The `.dmg`, verified by mounting it and checking the app's signature inside."""
        ...


class NotariserInterface(Protocol):
    """Submits a signed file to Apple's notary service and staples the ticket to it."""

    def notarise(self, path: Path, credentials: Mapping[str, str]) -> None:
        """Returns once the file is accepted and stapled; raises otherwise."""
        ...
