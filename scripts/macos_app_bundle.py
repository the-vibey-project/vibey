# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""krypton desktop as a self-contained macOS app: a `.app` carrying its GTK runtime, in a `.dmg`.

    python scripts/macos_app_bundle.py brew-packages
    python scripts/macos_app_bundle.py bundle --prefix P --build-dir B --homebrew H --out D
    python scripts/macos_app_bundle.py verify --app A
    python scripts/macos_app_bundle.py smoke --app A
    python scripts/macos_app_bundle.py package --app A --dmg F [--github-output G]

`bundle` takes a `meson install` of clients/desktop (its prefix) and the Homebrew it was
built against, and writes `<name>.app`: the program, a launcher (`launcher.c`) that points
GLib, GTK and gdk-pixbuf at the bundle, every library they load that macOS does not provide
(found by walking the load commands, copied in, and rewritten to `@rpath`), gdk-pixbuf's SVG
loader, GIO's TLS module, GTK's GSettings schemas, the Adwaita symbolic icons, the design
system's icon as an `.icns`, and an Info.plist that takes the app id and name from the
desktop entry meson installed. It is ad-hoc signed, so it runs.

`verify` proves the bundle names nothing outside itself (every load command, run path and
text file); `smoke` runs it with every Homebrew prefix made unreadable and checks that it is
still alive with a window on screen, mapping no file from outside the bundle. `package`
puts it in a `.dmg`: signed with the Developer ID and notarised when the credentials
`scripts/macos_app_bundle.toml` names are all present, ad-hoc signed and said so when not.

The scripted equivalent of gtk-mac-bundler (which is unmaintained for GTK 4), written as
classes over one command runner so every decision is tested without a Mac.
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import json
import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.macos_app_bundle_interface import (
        AppBundlerInterface,
        BundleVerifierInterface,
        CommandRunnerInterface,
        DiskImagerInterface,
        DylibClosureInterface,
        MachOReaderInterface,
        NotariserInterface,
        SignerInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.macos_app_bundle_interface import (  # type: ignore[import-not-found,no-redef]
        AppBundlerInterface,
        BundleVerifierInterface,
        CommandRunnerInterface,
        DiskImagerInterface,
        DylibClosureInterface,
        MachOReaderInterface,
        NotariserInterface,
        SignerInterface,
    )

SCRIPT = "scripts/macos_app_bundle.py"
#: Where this script finds its own configuration: the one location derived rather than
#: declared, because a tool must find its configuration before it can read anything out of
#: it (sub-doctrine 12.h states this exception and forbids widening it).
DEFAULT_CONFIG = Path(__file__).resolve().with_suffix(".toml")
REPO = Path(__file__).resolve().parents[1]
#: The text the loader cache template carries in place of the bundle's Contents/Resources.
PLACEHOLDER = "@KRYPTON_BUNDLE_RESOURCES@"
#: The first four bytes of a Mach-O file, thin or universal, either byte order.
MACHO_MAGIC = {
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
}
#: The Info.plist keys a bundle cannot launch, or be identified, without.
REQUIRED_KEYS = (
    "CFBundleIdentifier",
    "CFBundleName",
    "CFBundleExecutable",
    "CFBundleIconFile",
    "CFBundleShortVersionString",
    "LSMinimumSystemVersion",
)


class BundleError(RuntimeError):
    """A declaration, a library or a bundle that is not what it must be."""


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class BundleConfig:
    """`[macos_bundle]` from the TOML, with every repository path resolved."""

    root: Path
    brew: tuple[str, ...]
    program: str
    launcher_source: Path
    window_probe_source: Path
    iconset: Path
    category: str
    bonjour_services: tuple[str, ...]
    local_network_usage: str
    system_prefixes: tuple[str, ...]
    forbidden_prefixes: tuple[str, ...]
    smoke_seconds: int
    dmg_format: str
    dmg_filesystem: str
    dmg_attempts: int
    runtime: Mapping[str, Any]
    icons: Mapping[str, tuple[str, ...]]
    signing: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG, root: Path = REPO) -> BundleConfig:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        section = data.get("macos_bundle")
        if not isinstance(section, dict):
            raise BundleError(f"{path} declares no [macos_bundle] table")
        try:
            runtime = dict(section["runtime"])
            icons = {str(k): tuple(str(p) for p in v) for k, v in runtime.pop("icons").items()}
            return cls(
                root=root,
                brew=tuple(str(one) for one in section["brew"]),
                program=str(section["program"]),
                launcher_source=root / section["launcher_source"],
                window_probe_source=root / section["window_probe_source"],
                iconset=root / section["iconset"],
                category=str(section["category"]),
                bonjour_services=tuple(str(one) for one in section["bonjour_services"]),
                local_network_usage=str(section["local_network_usage"]),
                system_prefixes=tuple(str(one) for one in section["system_prefixes"]),
                forbidden_prefixes=tuple(str(one) for one in section["forbidden_prefixes"]),
                smoke_seconds=int(section["smoke_seconds"]),
                dmg_format=str(section["dmg_format"]),
                dmg_filesystem=str(section["dmg_filesystem"]),
                dmg_attempts=int(section["dmg_attempts"]),
                runtime=runtime,
                icons=icons,
                signing=dict(section["signing"]),
            )
        except KeyError as missing:
            raise BundleError(f"{path}: [macos_bundle] lacks {missing}") from None


# ------------------------------------------------------------------------- running


class SubprocessRunner(CommandRunnerInterface):
    """Implements `CommandRunnerInterface` with `subprocess`."""

    def run(self, argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
        result = subprocess.run(  # noqa: S603 -- argv is built here, never a shell string
            [str(arg) for arg in argv],
            check=False,
            capture_output=True,
            text=True,
            env=dict(env) if env is not None else None,
        )
        if result.returncode != 0:
            raise BundleError(
                f"`{' '.join(str(arg) for arg in argv[:3])} ...` exited {result.returncode}: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result.stdout


# -------------------------------------------------------------------------- Mach-O


@dataclass(frozen=True)
class MachO:
    """What one Mach-O file's load commands say."""

    path: Path
    install_id: str | None
    loads: tuple[str, ...]
    rpaths: tuple[str, ...]
    minos: tuple[int, ...] | None


def parse_version(text: str) -> tuple[int, ...]:
    """`"14.0"` as `(14, 0)`. A module-level function: one pure parse, shared by two
    classes, with nothing to hold."""
    return tuple(int(part) for part in text.split("."))


class OtoolReader(MachOReaderInterface):
    """Implements `MachOReaderInterface` over `otool -l`."""

    _NAME = re.compile(r"^\s*(name|path) (.+) \(offset \d+\)$")
    _LOADS = ("LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB")

    def __init__(self, runner: CommandRunnerInterface) -> None:
        self._runner = runner

    def is_macho(self, path: Path) -> bool:
        if not path.is_file() or path.is_symlink():
            return False
        with path.open("rb") as handle:
            return handle.read(4) in MACHO_MAGIC

    def read(self, path: Path) -> MachO:
        return self.parse(path, self._runner.run(["otool", "-l", str(path)]))

    @classmethod
    def parse(cls, path: Path, text: str) -> MachO:
        install_id: str | None = None
        loads: list[str] = []
        rpaths: list[str] = []
        minos: tuple[int, ...] | None = None
        command = ""
        platform = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("cmd "):
                command = stripped.split()[1]
                platform = ""
                continue
            if stripped.startswith("platform "):
                platform = stripped.split()[1]
                continue
            match = cls._NAME.match(line)
            if match is not None:
                value = match.group(2)
                if command == "LC_ID_DYLIB":
                    install_id = value
                elif command in cls._LOADS:
                    loads.append(value)
                elif command == "LC_RPATH":
                    rpaths.append(value)
                continue
            found: tuple[int, ...] | None = None
            if command == "LC_BUILD_VERSION" and stripped.startswith("minos "):
                if platform in ("1", "MACOS"):
                    found = parse_version(stripped.split()[1])
            elif command == "LC_VERSION_MIN_MACOSX" and stripped.startswith("version "):
                found = parse_version(stripped.split()[1])
            if found is not None and (minos is None or found > minos):
                minos = found
        return MachO(path, install_id, tuple(loads), tuple(rpaths), minos)


# ------------------------------------------------------------------------- closure


class DylibClosure(DylibClosureInterface):
    """Implements `DylibClosureInterface`: follows every load command to a real file.

    `links` records, for each file walked, which of its references names which bundled
    library, so the bundler rewrites exactly those references and no others.
    """

    def __init__(
        self,
        reader: MachOReaderInterface,
        *,
        system_prefixes: Sequence[str],
        executable: Path,
    ) -> None:
        self._reader = reader
        self._system = tuple(system_prefixes)
        self._executable = executable
        self.links: dict[Path, dict[str, str]] = {}
        self.images: dict[Path, MachO] = {}

    def close(self, roots: Sequence[Path]) -> dict[Path, str]:
        bundled: dict[Path, str] = {}
        names: dict[str, Path] = {}
        executable_rpaths = self._reader.read(self._executable).rpaths
        queue: list[Path] = list(roots)
        while queue:
            loader = queue.pop(0)
            real = loader.resolve()
            if real in self.links:
                continue
            image = self._reader.read(real)
            self.images[real] = image
            self.links[real] = {}
            for reference in image.loads:
                found = self._resolve(reference, image, loader, executable_rpaths)
                if found is None:
                    continue
                target = found.resolve()
                name = bundled.get(target)
                if name is None:
                    library = self._reader.read(target)
                    name = Path(library.install_id or reference).name
                    clash = names.get(name)
                    if clash is not None and clash != target:
                        raise BundleError(
                            f"two libraries would be bundled as {name}: {clash}, {target}"
                        )
                    names[name] = target
                    bundled[target] = name
                    queue.append(found)
                self.links[real][reference] = name
        return bundled

    def _resolve(
        self,
        reference: str,
        image: MachO,
        loader: Path,
        executable_rpaths: Sequence[str],
    ) -> Path | None:
        if reference.startswith(self._system):
            return None
        candidates: list[Path] = []
        if reference.startswith("@rpath/"):
            tail = reference[len("@rpath/") :]
            for rpath in (*image.rpaths, *executable_rpaths):
                candidates.append(Path(self._expand(rpath, loader)) / tail)
        elif reference.startswith(("@loader_path/", "@executable_path/")):
            candidates.append(Path(self._expand(reference, loader)))
        else:
            candidates.append(Path(reference))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise BundleError(f"{loader} loads {reference}, which is on no path it searches")

    def _expand(self, text: str, loader: Path) -> str:
        return text.replace("@loader_path", str(loader.parent)).replace(
            "@executable_path", str(self._executable.parent)
        )


# ------------------------------------------------------------------------- identity


@dataclass(frozen=True)
class AppIdentity:
    """The app id, the name people see, and the version: read, never declared here."""

    app_id: str
    name: str
    version: str

    @classmethod
    def read(cls, prefix: Path, version: str) -> AppIdentity:
        entries = sorted((prefix / "share" / "applications").glob("*.desktop"))
        if len(entries) != 1:
            raise BundleError(
                f"{prefix}/share/applications holds {len(entries)} desktop entries, not one"
            )
        name = ""
        in_entry = False
        for line in entries[0].read_text(encoding="utf-8").splitlines():
            if line.startswith("["):
                in_entry = line.strip() == "[Desktop Entry]"
            elif in_entry and line.startswith("Name="):
                name = line.split("=", 1)[1].strip()
                break
        if not name:
            raise BundleError(f"{entries[0]} has no Name in [Desktop Entry]")
        return cls(app_id=entries[0].stem, name=name, version=version)


# ------------------------------------------------------------------------- bundling


def macho_files(root: Path, reader: MachOReaderInterface) -> list[Path]:
    """Every Mach-O file under `root`, deepest first, as codesign wants them. A module-level
    function: the signer, the verifier and the bundler all walk a bundle the same way."""
    found = [path for path in root.rglob("*") if reader.is_macho(path)]
    return sorted(found, key=lambda path: (-len(path.parts), str(path)))


class AppBundler(AppBundlerInterface):
    """Implements `AppBundlerInterface`."""

    def __init__(
        self,
        config: BundleConfig,
        runner: CommandRunnerInterface,
        reader: MachOReaderInterface,
        signer: SignerInterface,
    ) -> None:
        self._config = config
        self._runner = runner
        self._reader = reader
        self._signer = signer

    def bundle(self, *, prefix: Path, build_dir: Path, homebrew: Path, out: Path) -> Path:
        info = json.loads(
            self._runner.run(["meson", "introspect", "--projectinfo", str(build_dir)])
        )
        identity = AppIdentity.read(prefix, str(info["version"]))
        runtime = self._config.runtime
        app = out / f"{identity.name}.app"
        if app.exists():
            shutil.rmtree(app)
        contents = app / "Contents"
        macos, frameworks, resources = (
            contents / "MacOS",
            contents / "Frameworks",
            contents / "Resources",
        )
        for directory in (macos, frameworks, resources):
            directory.mkdir(parents=True)

        program = prefix / "bin" / self._config.program
        if not program.is_file():
            raise BundleError(f"{program} is not there: run `meson install` first")
        # What GTK loads at run time, beside what the program links.
        plugins: dict[Path, Path] = {}
        for directory, names in (
            (runtime["pixbuf_loader_dir"], runtime["pixbuf_loaders"]),
            (runtime["gio_module_dir"], runtime["gio_modules"]),
        ):
            for name in names:
                source = homebrew / directory / name
                if not source.is_file():
                    raise BundleError(f"{source} is not there: is its formula installed?")
                plugins[source] = resources / directory / name

        closure = DylibClosure(
            self._reader, system_prefixes=self._config.system_prefixes, executable=program
        )
        libraries = closure.close([program, *plugins])
        placed: dict[Path, Path] = {program.resolve(): macos / self._config.program}
        placed.update({source.resolve(): target for source, target in plugins.items()})
        placed.update({source: frameworks / name for source, name in libraries.items()})
        for source, target in placed.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(0o755)
        for source, target in placed.items():
            self._rewrite(target, closure.links.get(source, {}), frameworks, source in libraries)

        minimum = max(
            (image.minos for image in closure.images.values() if image.minos is not None),
            default=None,
        )
        if minimum is None:
            raise BundleError("no bundled file states the macOS it needs (LC_BUILD_VERSION)")
        minimum_text = ".".join(str(part) for part in minimum)

        template = self._pixbuf_template(homebrew, plugins, resources)
        self._schemas(homebrew, resources)
        self._icons(homebrew, prefix, resources)
        icon = f"{self._config.program}.icns"
        self._runner.run(
            ["iconutil", "-c", "icns", str(self._config.iconset), "-o", str(resources / icon)]
        )
        self._launcher(identity, macos, template, minimum_text)
        self._info_plist(identity, contents, icon, minimum_text)
        self._signer.sign(app, "-")
        return app

    def _rewrite(
        self, target: Path, links: Mapping[str, str], frameworks: Path, is_library: bool
    ) -> None:
        image = self._reader.read(target)
        if image.rpaths:
            deletes: list[str] = []
            for rpath in dict.fromkeys(image.rpaths):
                deletes += ["-delete_rpath", rpath]
            self._runner.run(["install_name_tool", *deletes, str(target)])
        relative = os.path.relpath(frameworks, target.parent)
        rpath = "@loader_path" if relative == "." else f"@loader_path/{relative}"
        args = ["-add_rpath", rpath]
        # A loader or module is a dylib too, with an id naming where Homebrew put it.
        if is_library or image.install_id is not None:
            args += ["-id", f"@rpath/{target.name}"]
        for reference, name in links.items():
            args += ["-change", reference, f"@rpath/{name}"]
        self._runner.run(["install_name_tool", *args, str(target)])

    def _pixbuf_template(
        self, homebrew: Path, plugins: Mapping[Path, Path], resources: Path
    ) -> str:
        """The loader cache, queried over Homebrew's own loaders (so the query runs in one
        consistent process), with every Homebrew loader path made the bundle's."""
        runtime = self._config.runtime
        loaders = [
            source for source in plugins if source.parent == homebrew / runtime["pixbuf_loader_dir"]
        ]
        text = self._runner.run([str(homebrew / runtime["pixbuf_query"]), *map(str, loaders)])
        for source in loaders:
            text = text.replace(
                f'"{source}"', f'"{PLACEHOLDER}/{runtime["pixbuf_loader_dir"]}/{source.name}"'
            )
        if str(homebrew) in text:
            raise BundleError("the loader cache still names Homebrew after rewriting")
        relative = f"{Path(runtime['pixbuf_loader_dir']).parent}/loaders.cache.in"
        (resources / relative).write_text(text, encoding="utf-8")
        return relative

    def _schemas(self, homebrew: Path, resources: Path) -> None:
        runtime = self._config.runtime
        source = homebrew / runtime["schema_dir"]
        target = resources / runtime["schema_dir"]
        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for path in sorted(source.iterdir()):
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in runtime["schemas"]):
                shutil.copyfile(path, target / path.name)
                copied += 1
        if copied == 0:
            raise BundleError(f"no schema in {source} matches {runtime['schemas']}")
        self._runner.run([str(homebrew / runtime["compile_schemas"]), str(target)])

    def _icons(self, homebrew: Path, prefix: Path, resources: Path) -> None:
        icon_dir = self._config.runtime["icon_dir"]
        for theme, patterns in self._config.icons.items():
            source = homebrew / icon_dir / theme
            copied = 0
            for pattern in patterns:
                for path in sorted(source.glob(pattern)):
                    if path.is_dir():
                        continue
                    target = resources / icon_dir / theme / path.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
                    copied += 1
            if copied == 0:
                raise BundleError(f"icon theme {theme}: nothing in {source} matches {patterns}")
        own = prefix / "share" / "icons"
        if own.is_dir():
            shutil.copytree(own, resources / icon_dir, dirs_exist_ok=True)

    def _launcher(self, identity: AppIdentity, macos: Path, template: str, minimum: str) -> None:
        runtime = self._config.runtime
        defines = {
            "KR_PROGRAM": self._config.program,
            "KR_APP_ID": identity.app_id,
            "KR_PIXBUF_TEMPLATE": template,
            "KR_PIXBUF_DIR": runtime["pixbuf_loader_dir"],
            "KR_GIO_MODULE_DIR": runtime["gio_module_dir"],
            "KR_SCHEMA_DIR": runtime["schema_dir"],
            "KR_PLACEHOLDER": PLACEHOLDER,
        }
        self._runner.run(
            [
                "cc",
                "-std=c17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-mmacosx-version-min={minimum}",
                *(f'-D{key}="{value}"' for key, value in defines.items()),
                str(self._config.launcher_source),
                "-o",
                str(macos / identity.name),
            ]
        )

    def _info_plist(self, identity: AppIdentity, contents: Path, icon: str, minimum: str) -> None:
        info = {
            "CFBundleDevelopmentRegion": "en",
            "CFBundleDisplayName": identity.name,
            "CFBundleExecutable": identity.name,
            "CFBundleIconFile": icon,
            "CFBundleIdentifier": identity.app_id,
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": identity.name,
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": identity.version,
            "CFBundleVersion": identity.version,
            "LSApplicationCategoryType": self._config.category,
            "LSMinimumSystemVersion": minimum,
            "NSBonjourServices": list(self._config.bonjour_services),
            "NSHighResolutionCapable": True,
            "NSLocalNetworkUsageDescription": self._config.local_network_usage,
            "NSPrincipalClass": "NSApplication",
            "NSSupportsAutomaticGraphicsSwitching": True,
        }
        with (contents / "Info.plist").open("wb") as handle:
            plistlib.dump(info, handle)
        (contents / "PkgInfo").write_text("APPL????", encoding="ascii")


# ------------------------------------------------------------------------- signing


class CodesignSigner(SignerInterface):
    """Implements `SignerInterface` with `codesign`."""

    def __init__(self, runner: CommandRunnerInterface, reader: MachOReaderInterface) -> None:
        self._runner = runner
        self._reader = reader

    def sign(self, app: Path, identity: str, *, keychain: Path | None = None) -> None:
        base = ["codesign", "--force", "--sign", identity]
        if identity == "-":
            base.append("--timestamp=none")
        else:
            base += ["--timestamp", "--options", "runtime"]
        if keychain is not None:
            base += ["--keychain", str(keychain)]
        main = self._main_executable(app)
        for path in macho_files(app / "Contents", self._reader):
            if path != main:
                self._runner.run([*base, str(path)])
        self._runner.run([*base, str(app)])
        self._runner.run(["codesign", "--verify", "--strict", "--deep", "--verbose=2", str(app)])

    @staticmethod
    def _main_executable(app: Path) -> Path:
        with (app / "Contents" / "Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        return app / "Contents" / "MacOS" / str(info["CFBundleExecutable"])


class SigningCredentials:
    """Which of the Developer ID credentials `[macos_bundle.signing]` names are present."""

    def __init__(self, signing: Mapping[str, Any], environ: Mapping[str, str]) -> None:
        self._signing = signing
        self._environ = environ

    def _set(self, name: str) -> bool:
        return bool(self._environ.get(name, "").strip())

    def names(self) -> list[str]:
        """Every variable named, in declaration order: the secrets the workflow maps."""
        s = self._signing
        return [
            s["certificate"],
            s["certificate_password"],
            s["team_id"],
            *s["notary_api_key"],
            *s["notary_apple_id"],
        ]

    def notary(self) -> str | None:
        """`api-key` or `apple-id`, whichever is complete (the API key first), else None."""
        if all(self._set(name) for name in self._signing["notary_api_key"]):
            return "api-key"
        if all(self._set(name) for name in self._signing["notary_apple_id"]):
            return "apple-id"
        return None

    def missing(self) -> list[str]:
        """What is absent, in words: empty when Developer ID signing can go ahead."""
        s = self._signing
        found = [
            name
            for name in (s["certificate"], s["certificate_password"], s["team_id"])
            if not self._set(name)
        ]
        if self.notary() is None:
            api = ", ".join(s["notary_api_key"])
            apple = ", ".join(s["notary_apple_id"])
            found.append(f"either {api} or {apple} (for notarisation)")
        return found

    def value(self, name: str) -> str:
        return self._environ.get(name, "").strip()


class KeychainImporter:
    """Puts the Developer ID certificate in a keychain of its own; returns the identity."""

    _IDENTITY = re.compile(r'^\s*\d+\)\s+([0-9A-F]{40})\s+"(.+)"$')

    def __init__(self, runner: CommandRunnerInterface) -> None:
        self._runner = runner

    def import_identity(
        self, *, p12_base64: str, password: str, keychain: Path, prefix: str, team_id: str
    ) -> str:
        secret = base64.b64encode(os.urandom(24)).decode()
        certificate = keychain.with_suffix(".p12")
        certificate.write_bytes(base64.b64decode(p12_base64))
        certificate.chmod(0o600)
        try:
            run = self._runner.run
            run(["security", "create-keychain", "-p", secret, str(keychain)])
            run(["security", "set-keychain-settings", "-lut", "21600", str(keychain)])
            run(["security", "unlock-keychain", "-p", secret, str(keychain)])
            run(["security", "import", str(certificate), "-k", str(keychain), "-P", password,
                 "-f", "pkcs12", "-T", "/usr/bin/codesign"])  # fmt: skip
            run(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:",
                 "-s", "-k", secret, str(keychain)])  # fmt: skip
            listed = run(["security", "list-keychains", "-d", "user"])
            existing = [line.strip().strip('"') for line in listed.splitlines() if line.strip()]
            run(["security", "list-keychains", "-d", "user", "-s", str(keychain), *existing])
            identities = run(
                ["security", "find-identity", "-v", "-p", "codesigning", str(keychain)]
            )
        finally:
            certificate.unlink(missing_ok=True)
        return self.pick(identities, prefix, team_id)

    @classmethod
    def pick(cls, listing: str, prefix: str, team_id: str) -> str:
        for line in listing.splitlines():
            match = cls._IDENTITY.match(line)
            if match and match.group(2).startswith(prefix) and f"({team_id})" in match.group(2):
                return match.group(1)
        raise BundleError(f"no valid '{prefix}' identity for team {team_id} in the certificate")


# ----------------------------------------------------------------------- verifying


class BundleVerifier(BundleVerifierInterface):
    """Implements `BundleVerifierInterface`."""

    #: Text files a bundle may carry a stray absolute path in.
    _TEXT = (".theme", ".in", ".plist", ".cache", ".xml", ".ini")

    def __init__(
        self,
        config: BundleConfig,
        runner: CommandRunnerInterface,
        reader: MachOReaderInterface,
    ) -> None:
        self._config = config
        self._runner = runner
        self._reader = reader

    def problems(self, app: Path) -> list[str]:
        found: list[str] = []
        info_path = app / "Contents" / "Info.plist"
        if not info_path.is_file():
            return [f"{app} has no Contents/Info.plist"]
        with info_path.open("rb") as handle:
            info = plistlib.load(handle)
        for key in REQUIRED_KEYS:
            if not info.get(key):
                found.append(f"Info.plist lacks {key}")
        macos = app / "Contents" / "MacOS"
        if not (macos / str(info.get("CFBundleExecutable", ""))).is_file():
            found.append("the CFBundleExecutable is not in Contents/MacOS")
        if not (app / "Contents" / "Resources" / str(info.get("CFBundleIconFile", ""))).is_file():
            found.append("the CFBundleIconFile is not in Contents/Resources")
        for path in macho_files(app / "Contents", self._reader):
            found += self._macho(app, macos, path)
        for path in sorted(app.rglob("*")):
            if path.is_file() and path.suffix in self._TEXT and not self._reader.is_macho(path):
                text = path.read_text(encoding="utf-8", errors="replace")
                for prefix in self._config.forbidden_prefixes:
                    if prefix in text:
                        found.append(f"{path.relative_to(app)} names {prefix}")
        try:
            self._runner.run(["codesign", "--verify", "--strict", "--deep", str(app)])
        except BundleError as error:
            found.append(f"the signature does not verify: {error}")
        return found

    def _macho(self, app: Path, macos: Path, path: Path) -> list[str]:
        found: list[str] = []
        image = self._reader.read(path)
        where = path.relative_to(app)
        for text in (image.install_id or "", *image.loads, *image.rpaths):
            for prefix in self._config.forbidden_prefixes:
                if prefix in text:
                    found.append(f"{where} names {text}")
        rpaths = [
            rpath.replace("@loader_path", str(path.parent)).replace("@executable_path", str(macos))
            for rpath in image.rpaths
        ]
        for reference in image.loads:
            if reference.startswith(self._config.system_prefixes):
                continue
            if reference.startswith("@rpath/"):
                tail = reference[len("@rpath/") :]
                hits = [Path(rpath) / tail for rpath in rpaths if (Path(rpath) / tail).is_file()]
                if not hits:
                    found.append(f"{where} loads {reference}, which no run path of it finds")
                elif not hits[0].resolve().is_relative_to(app.resolve()):
                    found.append(f"{where} loads {reference} from outside the bundle")
            else:
                found.append(f"{where} loads {reference} by a path the bundle does not control")
        return found


# -------------------------------------------------------------------------- smoke


class SmokeTest:
    """Runs the app with Homebrew unreadable; proves it lives, shows a window, maps only itself."""

    def __init__(self, config: BundleConfig, runner: CommandRunnerInterface) -> None:
        self._config = config
        self._runner = runner

    def profile(self) -> str:
        """A sandbox profile that allows everything but reading or writing any forbidden prefix."""
        lines = ["(version 1)", "(allow default)"]
        for prefix in self._config.forbidden_prefixes:
            lines.append(f'(deny file-read* file-write* (subpath "{prefix.rstrip("/")}"))')
        return "\n".join(lines) + "\n"

    @staticmethod
    def windows(listing: str) -> list[tuple[int, int, int, int, int]]:
        """The probe's lines as (layer, x, y, width, height), the visible ones only."""
        found = []
        for line in listing.splitlines():
            parts = line.split()
            if len(parts) == 5:
                layer, x, y, width, height = (int(part) for part in parts)
                if width > 0 and height > 0:
                    found.append((layer, x, y, width, height))
        return found

    @staticmethod
    def mapped(listing: str) -> list[str]:
        """The file names `lsof -Fn` lists."""
        return [line[1:] for line in listing.splitlines() if line.startswith("n/")]

    def run(self, app: Path, seconds: int, scratch: Path) -> dict[str, Any]:
        probe = scratch / "window_probe"
        self._runner.run(["swiftc", "-O", str(self._config.window_probe_source), "-o", str(probe)])
        with (app / "Contents" / "Info.plist").open("rb") as handle:
            executable = (
                app / "Contents" / "MacOS" / str(plistlib.load(handle)["CFBundleExecutable"])
            )
        env = {
            key: os.environ[key]
            for key in ("HOME", "USER", "LOGNAME", "TMPDIR")
            if key in os.environ
        }
        env.update(PATH="/usr/bin:/bin:/usr/sbin:/sbin", LANG="en_US.UTF-8")
        log_path = scratch / "smoke.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(  # noqa: S603 -- a fixed argv
                ["/usr/bin/sandbox-exec", "-p", self.profile(), str(executable)],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        started = time.monotonic()
        try:
            while time.monotonic() - started < seconds:
                if process.poll() is not None:
                    raise BundleError(
                        f"the app exited ({process.returncode}) after "
                        f"{time.monotonic() - started:.1f}s:\n{log_path.read_text(errors='replace')}"
                    )
                time.sleep(0.5)
            windows = self.windows(self._runner.run([str(probe), str(process.pid)]))
            files = self.mapped(
                self._runner.run(["lsof", "-n", "-P", "-p", str(process.pid), "-Fn"])
            )
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        inside = str(app.resolve())
        outside = [path for path in files if path.startswith(self._config.forbidden_prefixes)]
        result = {
            "alive_seconds": seconds,
            "windows": windows,
            "files_mapped_from_bundle": sum(1 for path in files if path.startswith(inside)),
            "files_mapped_from_forbidden_prefixes": outside,
            "log": log_path.read_text(errors="replace")[-4000:],
        }
        problems = []
        if not windows:
            problems.append("the app put no window on screen")
        if outside:
            problems.append(f"the app mapped files from outside the bundle: {outside}")
        if result["files_mapped_from_bundle"] == 0:
            problems.append("the app mapped nothing from the bundle")
        if problems:
            raise BundleError("; ".join(problems) + f"\n{result['log']}")
        return result


# --------------------------------------------------------------------- disk image


class DiskImager(DiskImagerInterface):
    """Implements `DiskImagerInterface` with `hdiutil`."""

    def __init__(
        self,
        config: BundleConfig,
        runner: CommandRunnerInterface,
        *,
        pause: Any = time.sleep,
    ) -> None:
        self._config = config
        self._runner = runner
        self._pause = pause

    def create(self, app: Path, out: Path, *, volume_name: str) -> Path:
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as staging_text:
            staging = Path(staging_text)
            self._runner.run(["ditto", str(app), str(staging / app.name)])
            (staging / "Applications").symlink_to("/Applications")
            command = [
                "hdiutil", "create", "-volname", volume_name, "-srcfolder", str(staging),
                "-fs", self._config.dmg_filesystem, "-format", self._config.dmg_format,
                "-ov", str(out),
            ]  # fmt: skip
            self._retry(command)
        self._runner.run(["hdiutil", "verify", str(out)])
        with tempfile.TemporaryDirectory() as mount_text:
            mount = Path(mount_text)
            self._runner.run(
                [
                    "hdiutil",
                    "attach",
                    str(out),
                    "-nobrowse",
                    "-readonly",
                    "-noautoopen",
                    "-mountpoint",
                    str(mount),
                ]  # fmt: skip
            )
            try:
                inside = mount / app.name
                if not inside.is_dir():
                    raise BundleError(f"{out} does not carry {app.name}")
                self._runner.run(["codesign", "--verify", "--strict", "--deep", str(inside)])
            finally:
                self._retry(["hdiutil", "detach", str(mount), "-force"])
        return out

    def _retry(self, command: Sequence[str]) -> None:
        for attempt in range(1, self._config.dmg_attempts + 1):
            try:
                self._runner.run(command)
                return
            except BundleError:
                if attempt == self._config.dmg_attempts:
                    raise
                self._pause(5 * attempt)


# ------------------------------------------------------------------- notarising


class Notariser(NotariserInterface):
    """Implements `NotariserInterface` with `xcrun notarytool` and `xcrun stapler`."""

    def __init__(self, runner: CommandRunnerInterface, scratch: Path) -> None:
        self._runner = runner
        self._scratch = scratch

    def notarise(self, path: Path, credentials: Mapping[str, str]) -> None:
        auth = self.auth(credentials, self._scratch)
        result = json.loads(
            self._runner.run(
                [
                    "xcrun",
                    "notarytool",
                    "submit",
                    str(path),
                    *auth,
                    "--wait",
                    "--output-format",
                    "json",
                ]
            )
        )
        if result.get("status") != "Accepted":
            submission = str(result.get("id", ""))
            log = (
                self._runner.run(["xcrun", "notarytool", "log", submission, *auth])
                if submission
                else ""
            )
            raise BundleError(f"notarisation of {path.name} ended {result.get('status')!r}:\n{log}")
        self._runner.run(["xcrun", "stapler", "staple", str(path)])
        self._runner.run(["xcrun", "stapler", "validate", str(path)])

    @staticmethod
    def auth(credentials: Mapping[str, str], scratch: Path) -> list[str]:
        """notarytool's authentication arguments: the API key when given, else the Apple ID."""
        if credentials.get("mode") == "api-key":
            key = credentials["key"]
            if not key.lstrip().startswith("-----BEGIN"):
                key = base64.b64decode(key).decode()
            key_path = scratch / "notary-key.p8"
            key_path.write_text(key, encoding="utf-8")
            key_path.chmod(0o600)
            return [
                "--key",
                str(key_path),
                "--key-id",
                credentials["key_id"],
                "--issuer",
                credentials["issuer"],
            ]
        if credentials.get("mode") == "apple-id":
            return [
                "--apple-id", credentials["apple_id"], "--password", credentials["password"],
                "--team-id", credentials["team_id"],
            ]  # fmt: skip
        raise BundleError(f"unknown notary mode {credentials.get('mode')!r}")


# -------------------------------------------------------------------------- package


class Packager:
    """The release's tail: sign (Developer ID when every credential is present), image, notarise."""

    def __init__(
        self,
        config: BundleConfig,
        runner: CommandRunnerInterface,
        signer: SignerInterface,
        imager: DiskImagerInterface,
        environ: Mapping[str, str],
    ) -> None:
        self._config = config
        self._runner = runner
        self._signer = signer
        self._imager = imager
        self._credentials = SigningCredentials(config.signing, environ)

    def package(self, app: Path, dmg: Path, scratch: Path) -> dict[str, Any]:
        missing = self._credentials.missing()
        volume = app.stem
        if missing:
            # The bundle is already ad-hoc signed by `bundle`; it is imaged as it stands.
            self._imager.create(app, dmg, volume_name=volume)
            return {"signing": "ad-hoc", "missing": missing, "dmg": str(dmg)}
        s = self._config.signing
        value = self._credentials.value
        keychain = scratch / "signing.keychain-db"
        identity = KeychainImporter(self._runner).import_identity(
            p12_base64=value(s["certificate"]),
            password=value(s["certificate_password"]),
            keychain=keychain,
            prefix=str(s["identity_prefix"]),
            team_id=value(s["team_id"]),
        )
        self._signer.sign(app, identity, keychain=keychain)
        self._imager.create(app, dmg, volume_name=volume)
        self._runner.run(
            [
                "codesign",
                "--force",
                "--sign",
                identity,
                "--timestamp",
                "--keychain",
                str(keychain),
                str(dmg),
            ]
        )
        notary = self._credentials.notary()
        if notary == "api-key":
            key, key_id, issuer = (value(name) for name in s["notary_api_key"])
            credentials = {"mode": notary, "key": key, "key_id": key_id, "issuer": issuer}
        else:
            apple_id, password = (value(name) for name in s["notary_apple_id"])
            credentials = {
                "mode": "apple-id",
                "apple_id": apple_id,
                "password": password,
                "team_id": value(s["team_id"]),
            }
        Notariser(self._runner, scratch).notarise(dmg, credentials)
        self._runner.run(
            [
                "spctl",
                "--assess",
                "--type",
                "open",
                "--context",
                "context:primary-signature",
                "-v",
                str(dmg),
            ]
        )
        return {"signing": "developer-id", "missing": [], "dmg": str(dmg)}


# ---------------------------------------------------------------------------- CLI


class Cli:
    """The command line: each subcommand is one of the classes above, wired to real I/O."""

    def __init__(self, config: Path = DEFAULT_CONFIG, root: Path = REPO) -> None:
        self._config_path = config
        self._root = root

    def run(self, argv: Sequence[str] | None = None) -> int:
        args = self._parser().parse_args(argv)
        try:
            result: int = args.func(args)
            return result
        except BundleError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog=SCRIPT, description=__doc__.split("\n")[0])
        parser.add_argument("--config", type=Path, default=self._config_path)
        parser.add_argument("--root", type=Path, default=self._root, help="the source tree")
        sub = parser.add_subparsers(required=True)
        sub.add_parser("brew-packages", help="the Homebrew formulae to install").set_defaults(
            func=self._brew
        )
        bundle = sub.add_parser("bundle", help="make the .app from a meson install")
        bundle.add_argument("--prefix", required=True, type=Path)
        bundle.add_argument("--build-dir", required=True, type=Path)
        bundle.add_argument("--homebrew", required=True, type=Path)
        bundle.add_argument("--out", required=True, type=Path)
        bundle.set_defaults(func=self._bundle)
        verify = sub.add_parser("verify", help="prove the .app names nothing outside itself")
        verify.add_argument("--app", required=True, type=Path)
        verify.set_defaults(func=self._verify)
        smoke = sub.add_parser("smoke", help="run the .app with Homebrew unreadable")
        smoke.add_argument("--app", required=True, type=Path)
        smoke.add_argument("--seconds", type=int)
        smoke.set_defaults(func=self._smoke)
        package = sub.add_parser("package", help="sign, image and (with credentials) notarise")
        package.add_argument("--app", required=True, type=Path)
        package.add_argument("--dmg", required=True, type=Path)
        package.add_argument("--github-output", type=Path)
        package.set_defaults(func=self._package)
        return parser

    @staticmethod
    def _config(args: argparse.Namespace) -> BundleConfig:
        return BundleConfig.load(args.config, args.root)

    def _brew(self, args: argparse.Namespace) -> int:
        print(" ".join(self._config(args).brew))
        return 0

    def _bundle(self, args: argparse.Namespace) -> int:
        config = self._config(args)
        runner = SubprocessRunner()
        reader = OtoolReader(runner)
        bundler = AppBundler(config, runner, reader, CodesignSigner(runner, reader))
        app = bundler.bundle(
            prefix=args.prefix.resolve(),
            build_dir=args.build_dir.resolve(),
            homebrew=args.homebrew.resolve(),
            out=args.out.resolve(),
        )
        print(app)
        return 0

    def _verify(self, args: argparse.Namespace) -> int:
        config = self._config(args)
        runner = SubprocessRunner()
        reader = OtoolReader(runner)
        app = args.app.resolve()
        program = app / "Contents" / "MacOS" / config.program
        print(runner.run(["otool", "-L", str(program)]), end="")
        problems = BundleVerifier(config, runner, reader).problems(app)
        files = macho_files(app / "Contents", reader)
        for problem in problems:
            print(f"problem: {problem}", file=sys.stderr)
        print(f"{len(files)} Mach-O files checked; {len(problems)} problems")
        return 1 if problems else 0

    def _smoke(self, args: argparse.Namespace) -> int:
        config = self._config(args)
        with tempfile.TemporaryDirectory() as scratch:
            result = SmokeTest(config, SubprocessRunner()).run(
                args.app.resolve(), args.seconds or config.smoke_seconds, Path(scratch)
            )
        print(json.dumps(result, indent=2))
        return 0

    def _package(self, args: argparse.Namespace) -> int:
        config = self._config(args)
        runner = SubprocessRunner()
        reader = OtoolReader(runner)
        with tempfile.TemporaryDirectory() as scratch:
            result = Packager(
                config,
                runner,
                CodesignSigner(runner, reader),
                DiskImager(config, runner),
                os.environ,
            ).package(args.app.resolve(), args.dmg.resolve(), Path(scratch))
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"signing={result['signing']}\n")
                handle.write(f"missing={'; '.join(result['missing'])}\n")
        print(json.dumps(result, indent=2))
        return 0


def credential_names(config: BundleConfig) -> list[str]:
    """The secrets Developer ID signing reads, as the workflow must map them. A module-level
    function so tests and the release check share one reading of the declaration."""
    return SigningCredentials(config.signing, {}).names()


if __name__ == "__main__":
    sys.exit(Cli().run())
