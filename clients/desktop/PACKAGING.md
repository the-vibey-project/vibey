# Packaging krypton desktop: the plan

No store or package repository carries krypton desktop yet. Every store recipe below is
**declared only**: it is written down and versioned, but no store, repository or signing
identity is touched until the operator decides. What every release does carry, attached to
its GitHub Release by `.github/workflows/release-binaries.yml`, is an unsigned Flatpak bundle
of the manifest below and an Ubuntu 24.04 build, each for x86_64 and arm64, and a macOS app
in a `.dmg` for Apple silicon, ad-hoc signed until the Developer ID credentials exist
([downloads](../../docs/guides/downloads.md); the targets are declared in
`scripts/release_binaries.toml`). Publishing needs secrets this repository does not hold, and an act that cannot
easily be undone, such as a Flathub submission, an AUR upload or a notarised release,
waits for a human (sub-doctrine 12.d).

## Identities: two channels, side by side

| | Stable (default) | Nightly |
|---|---|---|
| Built from | `main` | `develop` |
| App id | `io.github.the_vibey_project.krypton` | `io.github.the_vibey_project.krypton.nightly` |
| Name people see | krypton | krypton nightly |
| Settings | `~/.config/krypton/` | `~/.config/krypton-nightly/` |
| macOS app | `krypton.app` | `krypton nightly.app` |
| Meson | `-Dchannel=stable` | `-Dchannel=nightly` |

This mirrors `vibey-engine` on PyPI (from `main`) and its development builds on TestPyPI
(from `develop`) (ADR-0028, ADR-0069). Stable is always the
default. On macOS too, the settings live in `~/.config/` (GLib's configuration directory
there), and the hub's token is read from `~/Library/Application Support/vibey/hub/token`,
where the hub keeps it. The macOS app's bundle identifier and name are the app id and name
above: the bundler reads them from the desktop entry `meson install` writes.

## Per platform

| Platform | Artefact | Recipe | Status |
|---|---|---|---|
| Arch | `PKGBUILD` | [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD) | Declared. It goes to the AUR on the operator's word. |
| Flatpak (any Linux) | flatpak-builder manifest | [`packaging/flatpak/io.github.the_vibey_project.krypton.yml`](packaging/flatpak/io.github.the_vibey_project.krypton.yml) | A bundle of it, built from the released commit, is attached to every GitHub Release. It goes to Flathub on the operator's word. |
| Ubuntu (24.04, and 26.04 per #1116) | `.deb` | `meson install` into a `debian/` tree | Planned. A `meson install` tarball built on 24.04 is attached to every GitHub Release meanwhile. |
| macOS (Apple silicon) | `.app` in a `.dmg`, carrying its GTK runtime | [`scripts/macos_app_bundle.py`](../../scripts/macos_app_bundle.py), declared in [`scripts/macos_app_bundle.toml`](../../scripts/macos_app_bundle.toml) | Attached to every GitHub Release, ad-hoc signed. Developer ID signing and notarisation run as soon as their secrets are set (below). |
| macOS (Intel) | | | Not built: Homebrew no longer bottles the GTK 4 stack for Intel macOS, and GitHub's last Intel runner retires in August 2027. |

CI already proves the parts every recipe relies on, on Ubuntu, on Arch and on macOS (the CI job `desktop`):

- the build;
- the tests;
- the nightly channel;
- `desktop-file-validate` and `appstreamcli validate` (on Linux, where those files ship);
- on macOS, the app bundle: built, verified to name nothing outside itself, run with every
  Homebrew prefix unreadable, and put in a `.dmg`.

## Order of work

1. **Release assets.** Done for the Flatpak bundle, the Ubuntu tarball and, from 3.4.0,
   the macOS `.dmg`: `release-binaries.yml` builds each from the released commit and
   attaches it to the vibey GitHub Release (3.3.0 was the first to carry the Linux files). Still to come: `krypton-desktop-vX.Y.Z` tags for the recipes to
   fetch, and the Arch package as an asset. None of this is a store upload.
2. **Nightly.** The same workflow on `develop` builds `-Dchannel=nightly` and attaches it
   to a rolling pre-release.
3. **Stores**, each as its own pull request the operator merges:
   - a Flathub submission;
   - an AUR `krypton-desktop` and `krypton-desktop-nightly`;
   - the macOS Developer ID secrets. The release workflow already signs and notarises
     the app once all of them are set.
4. **Ubuntu `.deb`.** Built in CI from the same `meson install`, for 24.04 and 26.04.

## macOS

The macOS app is built on GitHub's `macos-15` runner (Apple silicon) against Homebrew's GTK 4,
then made self-contained by `scripts/macos_app_bundle.py`. The scripted equivalent of
gtk-mac-bundler (unmaintained for GTK 4), it does this:

- **`bundle`** takes the `meson install` and writes `krypton.app`. It carries:
  - the program, and a small C launcher ([`packaging/macos/launcher.c`](packaging/macos/launcher.c))
    as the main executable, which points GLib, GTK and gdk-pixbuf at the bundle and then
    execs the program;
  - every library the program loads that macOS does not provide, found by walking the
    load commands, copied into `Contents/Frameworks` and rewritten to `@rpath`;
  - gdk-pixbuf's SVG loader and GIO's TLS module (an `https://` hub works);
  - GTK's GSettings schemas and Adwaita's symbolic icons;
  - the design system's `vibey.iconset` as the `.icns`;
  - an Info.plist whose identifier and name come from the desktop entry. Its oldest macOS
    is the highest any bundled library states (macOS 15 on that runner).
- **`verify`** fails on any load command, run path or text file that names a Homebrew
  prefix, and on any library that no run path finds inside the bundle.
- **`smoke`** runs the app for ten seconds with `/opt/homebrew`, `/usr/local` and
  `/opt/local` unreadable (a `sandbox-exec` profile). It then checks that the app is still
  alive, has a window on screen, and maps no file from those prefixes.
- **`package`** puts it in a `.dmg` with an Applications link, then mounts the image and
  checks the signature inside.

To build it yourself on an Apple-silicon Mac:

```bash
brew install $(python3 scripts/macos_app_bundle.py brew-packages)
meson setup build-app clients/desktop --prefix="$PWD/build-app/prefix" \
  -Dgui=enabled -Dc_link_args=-Wl,-headerpad_max_install_names
meson compile -C build-app && meson install -C build-app
app=$(python3 scripts/macos_app_bundle.py bundle --prefix build-app/prefix \
  --build-dir build-app --homebrew "$(brew --prefix)" --out build-app/out)
python3 scripts/macos_app_bundle.py verify --app "$app"
python3 scripts/macos_app_bundle.py smoke --app "$app"
python3 scripts/macos_app_bundle.py package --app "$app" --dmg build-app/krypton.dmg
```

**Discovery** uses Bonjour (`dns_sd.h`, the `kr-discovery-dnssd.c` backend behind the same
interface as Avahi on Linux), so a macOS build finds hubs on the network by itself. The
Info.plist declares `_vibey._tcp` in `NSBonjourServices`, with a reason in
`NSLocalNetworkUsageDescription`, because macOS asks once before an app browses the local
network.

**Signing.** Without credentials, the app is ad-hoc signed and not notarised, and the
downloads guide says so: macOS refuses the first launch until a person chooses Open Anyway
in System Settings, Privacy & Security, or clears the quarantine flag. Once the repository
holds every secret below, `release-binaries.yml` does four things:

1. imports the certificate into a keychain of its own;
2. signs every Mach-O file and the bundle with the hardened runtime;
3. signs the `.dmg`, has `notarytool` notarise it, and staples the ticket;
4. closes the tracking issue (`release-binaries-macos-signing`) that it keeps open until
   then.

A failure then fails the job loudly. The release itself is never affected.

| Secret | What it is |
|---|---|
| `MACOS_SIGNING_CERTIFICATE_P12` | The Developer ID Application certificate and its private key, exported as a `.p12` and base64-encoded |
| `MACOS_SIGNING_CERTIFICATE_PASSWORD` | The `.p12`'s password |
| `APPLE_TEAM_ID` | The Apple Developer team the certificate belongs to |
| `APPLE_NOTARY_API_KEY_P8`, `APPLE_NOTARY_API_KEY_ID`, `APPLE_NOTARY_API_ISSUER_ID` | An App Store Connect API key for `notarytool` (preferred) |
| `APPLE_NOTARY_APPLE_ID`, `APPLE_NOTARY_APP_PASSWORD` | Or an Apple ID and an app-specific password |
