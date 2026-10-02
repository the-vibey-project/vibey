# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/macos_app_bundle.py`: the macOS app bundle's every decision, without a Mac.

Each class runs over a fake command runner and a fake Mach-O reader, on files written into a
temporary directory, so the closure, the verifier's refusals, the signing decision and the
smoke test's reading of what it saw are all exercised on any platform. The real bundle is
built, verified and launched by CI's `desktop` (macos) cell and release-binaries.yml.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import base64
import json
import plistlib
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from scripts import macos_app_bundle as mb

REPO = Path(__file__).resolve().parents[2]


class FakeRunner:
    """Records each command; answers from a table keyed on the command's first words."""

    def __init__(self, answers: Mapping[str, str] | None = None, fail: Sequence[str] = ()) -> None:
        self.calls: list[list[str]] = []
        self._answers = dict(answers or {})
        self._fail = list(fail)

    def run(self, argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
        call = [str(arg) for arg in argv]
        self.calls.append(call)
        line = " ".join(call)
        for i, needle in enumerate(self._fail):
            if needle in line:
                self._fail.pop(i)
                raise mb.BundleError(f"{needle} failed")
        for needle, answer in self._answers.items():
            if needle in line:
                return answer
        return ""


class FakeReader:
    """A Mach-O reader over a table: path -> MachO."""

    def __init__(self, images: Mapping[Path, mb.MachO]) -> None:
        self.images = dict(images)

    def is_macho(self, path: Path) -> bool:
        return path in self.images

    def read(self, path: Path) -> mb.MachO:
        return self.images[path]


def _image(
    path: Path, *, loads: Sequence[str] = (), rpaths: Sequence[str] = (), id_: str | None = None
) -> mb.MachO:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xcf\xfa\xed\xfe")
    return mb.MachO(path, id_, tuple(loads), tuple(rpaths), (15, 0))


def _config(**override: Any) -> mb.BundleConfig:
    config = mb.BundleConfig.load()
    return mb.BundleConfig(**{**config.__dict__, **override})


# ------------------------------------------------------------------- configuration


def test_the_declared_configuration_loads_and_names_what_the_app_needs() -> None:
    config = mb.BundleConfig.load()
    assert {"gtk4", "libadwaita", "librsvg", "glib-networking"} <= set(config.brew)
    assert config.launcher_source.is_file() and config.window_probe_source.is_file()
    assert config.iconset.suffix == ".iconset", "the design system's iconset, never a copy"
    assert config.bonjour_services == ("_vibey._tcp",)
    assert "/opt/homebrew/" in config.forbidden_prefixes


def test_the_release_maps_exactly_the_secrets_the_bundler_reads() -> None:
    declared = tomllib.loads((REPO / "scripts/release_binaries.toml").read_text(encoding="utf-8"))
    macos = next(
        t
        for t in declared["release_binaries"]["targets"]
        if t.get("builder") == "desktop-macos" and t["status"] == "build"
    )
    assert macos["signing_credentials"] == mb.credential_names(mb.BundleConfig.load())
    workflow = (REPO / ".github/workflows/release-binaries.yml").read_text(encoding="utf-8")
    for name in macos["signing_credentials"]:
        assert f"{name}: ${{{{ secrets.{name} }}}}" in workflow


def test_a_configuration_without_its_table_or_a_key_is_refused(tmp_path: Path) -> None:
    (tmp_path / "empty.toml").write_text("", encoding="utf-8")
    with pytest.raises(mb.BundleError, match="declares no"):
        mb.BundleConfig.load(tmp_path / "empty.toml", tmp_path)
    (tmp_path / "half.toml").write_text("[macos_bundle]\nprogram = 'x'\n", encoding="utf-8")
    with pytest.raises(mb.BundleError, match="lacks"):
        mb.BundleConfig.load(tmp_path / "half.toml", tmp_path)


# ------------------------------------------------------------------------ otool


OTOOL = """\
/x/libfoo.dylib:
Load command 3
          cmd LC_ID_DYLIB
      cmdsize 56
         name /opt/homebrew/opt/foo/lib/libfoo.1.dylib (offset 24)
Load command 9
      cmd LC_BUILD_VERSION
  cmdsize 32
 platform 1
    minos 15.0
      sdk 15.5
Load command 12
          cmd LC_LOAD_DYLIB
      cmdsize 56
         name /opt/homebrew/opt/glib/lib/libglib-2.0.0.dylib (offset 24)
Load command 13
          cmd LC_LOAD_WEAK_DYLIB
         name @rpath/libbar.dylib (offset 24)
Load command 14
          cmd LC_RPATH
      cmdsize 32
         path @loader_path/../lib (offset 12)
Load command 15
      cmd LC_VERSION_MIN_MACOSX
  version 11.0
      sdk 12.0
"""


def test_otool_load_commands_are_read_into_id_loads_rpaths_and_minimum() -> None:
    image = mb.OtoolReader.parse(Path("/x/libfoo.dylib"), OTOOL)
    assert image.install_id == "/opt/homebrew/opt/foo/lib/libfoo.1.dylib"
    assert image.loads == ("/opt/homebrew/opt/glib/lib/libglib-2.0.0.dylib", "@rpath/libbar.dylib")
    assert image.rpaths == ("@loader_path/../lib",)
    assert image.minos == (15, 0), "the highest minimum any version command states"


def test_a_file_is_mach_o_by_its_magic_not_its_name(tmp_path: Path) -> None:
    reader = mb.OtoolReader(FakeRunner())
    (tmp_path / "lib.dylib").write_bytes(b"#!/bin/sh\n")
    (tmp_path / "plain").write_bytes(b"\xca\xfe\xba\xbe rest")
    assert not reader.is_macho(tmp_path / "lib.dylib")
    assert reader.is_macho(tmp_path / "plain")
    assert not reader.is_macho(tmp_path / "missing")


# ----------------------------------------------------------------------- closure


def test_the_closure_follows_absolute_rpath_and_loader_path_references(tmp_path: Path) -> None:
    brew = tmp_path / "brew"
    program = brew / "bin" / "app"
    glib = brew / "lib" / "libglib.dylib"
    gio = brew / "lib" / "libgio.dylib"
    ffi = brew / "lib" / "ffi" / "libffi.dylib"
    images = {
        program: _image(
            program, loads=[str(glib), "/usr/lib/libSystem.B.dylib"], rpaths=["@loader_path/../lib"]
        ),
        glib: _image(glib, loads=["@rpath/libgio.dylib"], id_=str(glib)),
        gio: _image(gio, loads=["@loader_path/ffi/libffi.dylib"], id_="@rpath/libgio.dylib"),
        ffi: _image(ffi, id_=str(ffi)),
    }
    closure = mb.DylibClosure(FakeReader(images), system_prefixes=["/usr/lib/"], executable=program)
    bundled = closure.close([program])
    assert bundled == {glib: "libglib.dylib", gio: "libgio.dylib", ffi: "libffi.dylib"}
    assert closure.links[program] == {str(glib): "libglib.dylib"}, "the system library stays"
    assert closure.links[glib] == {"@rpath/libgio.dylib": "libgio.dylib"}


def test_a_reference_found_nowhere_is_refused(tmp_path: Path) -> None:
    program = tmp_path / "app"
    images = {program: _image(program, loads=["@rpath/libgone.dylib"])}
    closure = mb.DylibClosure(FakeReader(images), system_prefixes=["/usr/lib/"], executable=program)
    with pytest.raises(mb.BundleError, match="on no path it searches"):
        closure.close([program])


def test_two_libraries_under_one_name_are_refused(tmp_path: Path) -> None:
    program = tmp_path / "app"
    one, two = tmp_path / "a" / "libx.dylib", tmp_path / "b" / "libx.dylib"
    images = {
        program: _image(program, loads=[str(one), str(two)]),
        one: _image(one, id_=str(one)),
        two: _image(two, id_=str(two)),
    }
    closure = mb.DylibClosure(FakeReader(images), system_prefixes=[], executable=program)
    with pytest.raises(mb.BundleError, match="two libraries would be bundled as libx.dylib"):
        closure.close([program])


# ---------------------------------------------------------------------- identity


def _desktop(prefix: Path, text: str, name: str = "io.example.app.desktop") -> None:
    apps = prefix / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / name).write_text(text, encoding="utf-8")


def test_the_identity_is_the_desktop_entry_meson_installed(tmp_path: Path) -> None:
    _desktop(
        tmp_path,
        "[Desktop Entry]\nType=Application\nName=krypton nightly\n[Desktop Action x]\nName=No\n",
    )
    identity = mb.AppIdentity.read(tmp_path, "0.1.0")
    assert identity == mb.AppIdentity("io.example.app", "krypton nightly", "0.1.0")


def test_an_identity_needs_exactly_one_entry_with_a_name(tmp_path: Path) -> None:
    with pytest.raises(mb.BundleError, match="0 desktop entries"):
        mb.AppIdentity.read(tmp_path, "1")
    _desktop(tmp_path, "[Desktop Entry]\nType=Application\n")
    with pytest.raises(mb.BundleError, match="has no Name"):
        mb.AppIdentity.read(tmp_path, "1")


# ------------------------------------------------------------------ the verifier


def _app(tmp_path: Path, info: Mapping[str, Any] | None = None) -> Path:
    app = tmp_path / "krypton.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Frameworks").mkdir()
    (contents / "Resources").mkdir()
    (contents / "Resources" / "k.icns").write_bytes(b"icns")
    (contents / "MacOS" / "krypton").write_bytes(b"\xcf\xfa\xed\xfe")
    values = {
        "CFBundleIdentifier": "io.example",
        "CFBundleName": "krypton",
        "CFBundleExecutable": "krypton",
        "CFBundleIconFile": "k.icns",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "15.0",
    }
    values.update(info or {})
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump(values, handle)
    return app


def test_a_bundle_that_names_only_itself_and_the_system_verifies(tmp_path: Path) -> None:
    app = _app(tmp_path)
    contents = app / "Contents"
    program = contents / "MacOS" / "krypton-desktop"
    glib = contents / "Frameworks" / "libglib.dylib"
    images = {
        contents / "MacOS" / "krypton": _image(
            contents / "MacOS" / "krypton", loads=["/usr/lib/libSystem.B.dylib"]
        ),
        program: _image(
            program, loads=["@rpath/libglib.dylib"], rpaths=["@loader_path/../Frameworks"]
        ),
        glib: _image(glib, id_="@rpath/libglib.dylib", rpaths=["@loader_path"]),
    }
    verifier = mb.BundleVerifier(_config(), FakeRunner(), FakeReader(images))
    assert verifier.problems(app) == []


def test_the_verifier_names_every_way_a_bundle_reaches_outside_itself(tmp_path: Path) -> None:
    app = _app(tmp_path, {"LSMinimumSystemVersion": ""})
    contents = app / "Contents"
    program = contents / "MacOS" / "krypton-desktop"
    outside = tmp_path / "outside" / "libout.dylib"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    images = {
        program: _image(
            program,
            loads=[
                "/opt/homebrew/lib/libglib.dylib",
                "@rpath/libnone.dylib",
                "@rpath/libout.dylib",
            ],
            rpaths=[str(outside.parent)],
            id_=None,
        ),
    }
    (contents / "Resources" / "loaders.cache.in").write_text(
        '"/opt/homebrew/lib/x.so"\n', encoding="utf-8"
    )
    runner = FakeRunner(fail=["codesign --verify"])
    problems = "\n".join(mb.BundleVerifier(_config(), runner, FakeReader(images)).problems(app))
    assert "Info.plist lacks LSMinimumSystemVersion" in problems
    assert "names /opt/homebrew/lib/libglib.dylib" in problems
    assert "@rpath/libnone.dylib, which no run path of it finds" in problems
    assert "libout.dylib from outside the bundle" in problems
    assert "by a path the bundle does not control" in problems
    assert "loaders.cache.in names /opt/homebrew/" in problems
    assert "the signature does not verify" in problems


def test_a_bundle_without_an_info_plist_is_one_problem(tmp_path: Path) -> None:
    (tmp_path / "x.app").mkdir()
    assert mb.BundleVerifier(_config(), FakeRunner(), FakeReader({})).problems(
        tmp_path / "x.app"
    ) == [f"{tmp_path / 'x.app'} has no Contents/Info.plist"]


# ------------------------------------------------------------------- signing


def test_signing_goes_innermost_first_then_the_bundle_then_verifies(tmp_path: Path) -> None:
    app = _app(tmp_path)
    contents = app / "Contents"
    deep = contents / "Resources" / "lib" / "gio" / "modules" / "libgiognutls.so"
    images = {
        contents / "MacOS" / "krypton": _image(contents / "MacOS" / "krypton"),
        contents / "MacOS" / "krypton-desktop": _image(contents / "MacOS" / "krypton-desktop"),
        deep: _image(deep),
    }
    runner = FakeRunner()
    mb.CodesignSigner(runner, FakeReader(images)).sign(app, "-")
    signed = [call[-1] for call in runner.calls if call[:2] == ["codesign", "--force"]]
    assert signed == [str(deep), str(contents / "MacOS" / "krypton-desktop"), str(app)]
    assert "--timestamp=none" in runner.calls[0] and "--options" not in runner.calls[0]
    assert runner.calls[-1][:2] == ["codesign", "--verify"]
    runner = FakeRunner()
    mb.CodesignSigner(runner, FakeReader(images)).sign(app, "ABC", keychain=tmp_path / "k")
    assert runner.calls[0][5:7] == ["--options", "runtime"], "Developer ID: hardened runtime"
    assert "--keychain" in runner.calls[0]


SIGNING = {
    "certificate": "CERT",
    "certificate_password": "PASS",
    "team_id": "TEAM",
    "notary_api_key": ["KEY", "KEY_ID", "ISSUER"],
    "notary_apple_id": ["APPLE_ID", "APP_PASSWORD"],
    "identity_prefix": "Developer ID Application",
}


def test_signing_credentials_are_complete_only_with_a_way_to_notarise() -> None:
    nothing = mb.SigningCredentials(SIGNING, {})
    assert nothing.missing()[:3] == ["CERT", "PASS", "TEAM"]
    assert "either KEY, KEY_ID, ISSUER or APPLE_ID, APP_PASSWORD" in nothing.missing()[3]
    base = {"CERT": "c", "PASS": "p", "TEAM": "t"}
    assert mb.SigningCredentials(SIGNING, base).notary() is None
    apple = mb.SigningCredentials(SIGNING, {**base, "APPLE_ID": "a", "APP_PASSWORD": "b"})
    assert (apple.notary(), apple.missing()) == ("apple-id", [])
    both = {**base, "APPLE_ID": "a", "APP_PASSWORD": "b", "KEY": "k", "KEY_ID": "i", "ISSUER": "s"}
    assert mb.SigningCredentials(SIGNING, both).notary() == "api-key", "the API key first"
    assert mb.SigningCredentials(SIGNING, {**base, "KEY": " "}).notary() is None, "blank is unset"


IDENTITIES = """\
  1) 0123456789ABCDEF0123456789ABCDEF01234567 "Apple Development: Someone (OTHER)"
  2) FEDCBA9876543210FEDCBA9876543210FEDCBA98 "Developer ID Application: The Project (TEAM)"
     2 valid identities found
"""


def test_the_developer_id_identity_of_the_team_is_picked() -> None:
    assert mb.KeychainImporter.pick(IDENTITIES, "Developer ID Application", "TEAM") == (
        "FEDCBA9876543210FEDCBA9876543210FEDCBA98"
    )
    with pytest.raises(mb.BundleError, match="no valid 'Developer ID Application' identity"):
        mb.KeychainImporter.pick(IDENTITIES, "Developer ID Application", "ELSE")


def test_notarytool_authenticates_with_the_api_key_or_the_apple_id(tmp_path: Path) -> None:
    pem = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"
    encoded = base64.b64encode(pem.encode()).decode()
    args = mb.Notariser.auth(
        {"mode": "api-key", "key": encoded, "key_id": "I", "issuer": "S"}, tmp_path
    )
    assert args[2:] == ["--key-id", "I", "--issuer", "S"]
    assert Path(args[1]).read_text(encoding="utf-8") == pem, "a base64 key is decoded"
    assert Path(args[1]).stat().st_mode & 0o777 == 0o600
    apple = mb.Notariser.auth(
        {"mode": "apple-id", "apple_id": "a@b", "password": "p", "team_id": "T"}, tmp_path
    )
    assert apple == ["--apple-id", "a@b", "--password", "p", "--team-id", "T"]
    with pytest.raises(mb.BundleError, match="unknown notary mode"):
        mb.Notariser.auth({"mode": "fax"}, tmp_path)


def test_a_rejected_notarisation_fails_loudly_with_its_log(tmp_path: Path) -> None:
    runner = FakeRunner(
        {
            "notarytool submit": json.dumps({"id": "42", "status": "Invalid"}),
            "notarytool log": "why",
        }
    )
    creds = {"mode": "apple-id", "apple_id": "a", "password": "p", "team_id": "T"}
    with pytest.raises(mb.BundleError, match="ended 'Invalid'"):
        mb.Notariser(runner, tmp_path).notarise(tmp_path / "x.dmg", creds)
    runner = FakeRunner({"notarytool submit": json.dumps({"id": "42", "status": "Accepted"})})
    mb.Notariser(runner, tmp_path).notarise(tmp_path / "x.dmg", creds)
    assert [call[1:3] for call in runner.calls[1:]] == [
        ["stapler", "staple"],
        ["stapler", "validate"],
    ]


# ----------------------------------------------------------------- packaging


class FakeSigner:
    def __init__(self) -> None:
        self.identities: list[str] = []

    def sign(self, app: Path, identity: str, *, keychain: Path | None = None) -> None:
        self.identities.append(identity)


class FakeImager:
    def __init__(self) -> None:
        self.created: list[tuple[Path, str]] = []

    def create(self, app: Path, out: Path, *, volume_name: str) -> Path:
        self.created.append((out, volume_name))
        return out


def _signing_config() -> mb.BundleConfig:
    return _config(signing=SIGNING)


def test_without_every_credential_the_app_is_imaged_ad_hoc_and_says_what_is_missing(
    tmp_path: Path,
) -> None:
    signer, imager, runner = FakeSigner(), FakeImager(), FakeRunner()
    result = mb.Packager(_signing_config(), runner, signer, imager, {"CERT": "c"}).package(
        tmp_path / "krypton.app", tmp_path / "k.dmg", tmp_path
    )
    assert result["signing"] == "ad-hoc" and "PASS" in result["missing"]
    assert signer.identities == [], "the bundle is already ad-hoc signed by `bundle`"
    assert imager.created == [(tmp_path / "k.dmg", "krypton")]
    assert runner.calls == [], "no keychain, no notary: nothing is attempted half-way"


def test_with_every_credential_it_is_signed_imaged_signed_notarised_and_assessed(
    tmp_path: Path,
) -> None:
    env = {
        "CERT": base64.b64encode(b"p12").decode(),
        "PASS": "p",
        "TEAM": "TEAM",
        "APPLE_ID": "a",
        "APP_PASSWORD": "b",
    }
    runner = FakeRunner(
        {
            "find-identity": IDENTITIES,
            "notarytool submit": json.dumps({"id": "1", "status": "Accepted"}),
        }
    )
    signer, imager = FakeSigner(), FakeImager()
    result = mb.Packager(_signing_config(), runner, signer, imager, env).package(
        tmp_path / "krypton.app", tmp_path / "k.dmg", tmp_path
    )
    assert result["signing"] == "developer-id"
    assert signer.identities == ["FEDCBA9876543210FEDCBA9876543210FEDCBA98"]
    order = [" ".join(call[:2]) for call in runner.calls]
    assert (
        order.index("codesign --force")
        < order.index("xcrun notarytool")
        < order.index("spctl --assess")
    )
    assert not (tmp_path / "signing.keychain-db.p12").exists(), "the certificate file is removed"


def test_a_busy_disk_is_retried_and_the_image_is_mounted_and_checked(tmp_path: Path) -> None:
    app = tmp_path / "krypton.app"
    app.mkdir()
    pauses: list[float] = []
    runner = FakeRunner(fail=["hdiutil create"])

    def attach(argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> str:
        if argv[:2] == ["hdiutil", "attach"]:
            (Path(argv[-1]) / "krypton.app").mkdir()
        return FakeRunner.run(runner, argv, env=env)

    runner.run = attach  # type: ignore[method-assign]
    mb.DiskImager(_config(), runner, pause=pauses.append).create(
        app, tmp_path / "k.dmg", volume_name="krypton"
    )
    verbs = [" ".join(call[:2]) for call in runner.calls]
    assert verbs.count("hdiutil create") == 2 and pauses == [5]
    assert verbs[-4:] == ["hdiutil verify", "hdiutil attach", "codesign --verify", "hdiutil detach"]


# ----------------------------------------------------------------------- smoke


def test_the_smoke_profile_denies_every_forbidden_prefix() -> None:
    profile = mb.SmokeTest(
        _config(forbidden_prefixes=("/opt/homebrew/", "/usr/local/")), FakeRunner()
    ).profile()
    assert profile.startswith("(version 1)\n(allow default)\n")
    assert '(deny file-read* file-write* (subpath "/opt/homebrew"))' in profile
    assert '(deny file-read* file-write* (subpath "/usr/local"))' in profile


def test_the_smoke_test_reads_windows_and_mapped_files() -> None:
    assert mb.SmokeTest.windows("0 216 110 1080 720\n3 0 0 0 0\nnoise\n") == [
        (0, 216, 110, 1080, 720)
    ]
    listing = (
        "p123\nfcwd\nn/Applications/krypton.app/Contents/MacOS/krypton-desktop\nn/dev/null\nfmem\n"
    )
    assert mb.SmokeTest.mapped(listing) == [
        "/Applications/krypton.app/Contents/MacOS/krypton-desktop",
        "/dev/null",
    ]


# --------------------------------------------------------------------------- CLI


def test_the_cli_prints_the_formulae_and_reports_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert mb.Cli().run(["brew-packages"]) == 0
    assert "gtk4" in capsys.readouterr().out.split()
    (tmp_path / "bad.toml").write_text("", encoding="utf-8")
    assert mb.Cli().run(["--config", str(tmp_path / "bad.toml"), "brew-packages"]) == 1
    assert "declares no [macos_bundle]" in capsys.readouterr().err
