---
description: The ready-built files attached to every vibey release, for each user interface and platform, with what is signed and how to install each.
---

# Downloads

> **Bottom Line Up Front (BLUF) — Which file to download for your device and how to install it in seconds:**
>
> Every release on [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (and the daily [`krypton-nightly`](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly) build) attaches ready-to-install files for every krypton interface. Pick your platform below:
>
> | Your device / app | File to download from [Releases](https://github.com/the-vibey-project/vibey/releases) | Exact install steps (no coding experience required) |
> |---|---|---|
> | **One-line installer (macOS & Linux)** | *(None — runs directly from Terminal)* | Open **Terminal** and run:<br>`curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh \| sh -s -- --with-krypton`<br>Then run `vibey connect --yes` to plug into Claude Code, Codex, Cursor, VS Code, Claude Desktop & Gemini CLI. |
> | **Mac (Apple silicon M1/M2/M3/M4/M5, macOS 15+)** — *krypton desktop* | `krypton-desktop-<version>-macos-arm64.dmg` | 1. Double-click the `.dmg` and drag **krypton** to **Applications**.<br>2. Open **Terminal** and run: `xattr -dr com.apple.quarantine /Applications/krypton.app` (or double-click **krypton**, then click **Open Anyway** in **System Settings → Privacy & Security**).<br>3. Open **krypton** from **Applications**. |
> | **Linux (Any distro: Ubuntu, Fedora, Arch, Mint)** — *krypton desktop (Flatpak)* | `krypton-desktop-<version>-linux-x86_64.flatpak` *(Intel/AMD)* or `...-aarch64.flatpak` *(ARM64)* | In Terminal, run:<br>`flatpak install --user ~/Downloads/krypton-desktop-*-linux-*.flatpak`<br>Launch with: `flatpak run io.github.the_vibey_project.krypton` |
> | **Linux (Ubuntu 24.04+ native)** — *krypton desktop (tarball)* | `krypton-desktop-<version>-linux-x86_64.tar.gz` *(Intel/AMD)* or `...-aarch64.tar.gz` *(ARM64)* | In Terminal, run:<br>`sudo apt update && sudo apt install -y libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 libavahi-client3 libavahi-glib1 glib-networking`<br>`sudo tar -xzf ~/Downloads/krypton-desktop-*-linux-*.tar.gz -C /`<br>Launch with: `krypton-desktop` |
> | **VS Code, VSCodium & Cursor (macOS & Linux)** — *krypton extension* | `krypton-vscode-<version>.vsix` *(or install from Open VSX)* | **No Terminal:** In VS Code / Cursor / VSCodium, open **Extensions** (`Cmd+Shift+X` / `Ctrl+Shift+X`) → click **`…`** at top right → **Install from VSIX…** → pick the `.vsix` file.<br>**With Terminal:** `code --install-extension ~/Downloads/krypton-vscode-*.vsix` (or `codium --install-extension the-vibey-project.krypton`). |
> | **Web Browser (Safari, Chrome, Firefox, Edge)** — *krypton web app* | `krypton-web-<version>.tar.gz` | In Terminal, run:<br>`mkdir -p ~/krypton-web && tar -xzf ~/Downloads/krypton-web-*.tar.gz -C ~/krypton-web && python3 -m http.server 8000 -d ~/krypton-web`<br>Then open `http://localhost:8000` in your browser. |
> | **Android Phone or Tablet** — *krypton mobile app* | `krypton-android-<version>.apk` | Download the `.apk` on your Android device, tap it in **Downloads**, allow **Install unknown apps** if prompted, and tap **Install** (or from a computer: `adb install krypton-android-<version>.apk`). |
> | **iPhone or iPad (iOS)** — *krypton mobile app* | `krypton-ios-<version>.ipa` *(or Expo Go)* | Distributed via Apple **TestFlight / App Store** from the signed `.ipa` when `EXPO_TOKEN` is set; or run immediately on any iPhone with **Expo Go** (`cd clients/app && npm ci && npx expo start`). |
> | **Browser Launcher (`krypton` CLI)** | `krypton_app-<version>-py3-none-any.whl` *(or PyPI)* | `uv tool install krypton-app` (or `uv tool install ./krypton_app-<version>-py3-none-any.whl`), then run `krypton`. |
> | **Engine, Runners & TUI (`vibey` CLI)** | `vibey_engine-<version>-py3-none-any.whl` *(or PyPI)* | `uv tool install vibey-engine` (or `uv tool install ./vibey_engine-<version>-py3-none-any.whl`), then run `vibey doctor`. |
>
> Need even more detail? Read the complete beginner walkthrough in [Install, copy, reinstall, uninstall](install.md).

Every vibey release on GitHub carries ready-built files for each user interface, on each
platform the project supports. They are attached to the release's page under
[Releases](https://github.com/the-vibey-project/vibey/releases), beside the source archives.
Each file is built from the released commit by
[`release-binaries.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/release-binaries.yml)
after the release has been published to PyPI.

PyPI stays the main way to install vibey itself (see the
[README's install section](https://github.com/the-vibey-project/vibey#install)). The Python files
here are the same bytes PyPI serves, attached so that one release page has everything.

Windows is not a supported platform, so nothing here is built for it.

As declared for 3.4.0, a release carries thirteen files and `SHA256SUMS`: four Linux
builds of the desktop client and its macOS `.dmg`, the web bundle, the Android and iOS
packages, the VS Code extension, and the wheel and source distribution of each Python
package. The iOS package is built only while its credential is set, so without it there are
twelve. 3.3.0, the first release to attach any, carried eleven; the macOS and iOS builds are
new in 3.4.0. The table below is the declaration, and it is generated, so it is the one to
trust if this paragraph ever disagrees with it.

## What each release carries

<!-- BEGIN GENERATED release:downloads — regenerated by scripts/release_binaries.py -->
*Generated from [`scripts/release_binaries.toml`](https://github.com/the-vibey-project/vibey/blob/develop/scripts/release_binaries.toml) by `scripts/release_binaries.py render`; do not edit inside these markers. `<version>` is each interface's own version.*

| Interface | Platform | Architecture | File | Signing |
|---|---|---|---|---|
| krypton desktop | Linux: any distribution with Flatpak (Ubuntu, Arch, Fedora) | x86_64 | `krypton-desktop-<version>-linux-x86_64.flatpak` | Unsigned |
| krypton desktop | Linux: any distribution with Flatpak (Ubuntu, Arch, Fedora) | aarch64 | `krypton-desktop-<version>-linux-aarch64.flatpak` | Unsigned |
| krypton desktop | Linux: Ubuntu 24.04 LTS and newer | x86_64 | `krypton-desktop-<version>-linux-x86_64.tar.gz` | Unsigned |
| krypton desktop | Linux: Ubuntu 24.04 LTS and newer | aarch64 | `krypton-desktop-<version>-linux-aarch64.tar.gz` | Unsigned |
| krypton desktop | macOS 15 Sequoia and newer, Apple silicon | arm64 | `krypton-desktop-<version>-macos-arm64.dmg` | Ad-hoc signed, not notarised: macOS asks you to confirm the first launch |
| krypton app | Web: any current browser, served as static files | any | `krypton-web-<version>.tar.gz` | Unsigned |
| krypton app | Android | any | `krypton-android-<version>.apk` | Android debug key: sideload only, not a store build |
| krypton app | iOS | any | `krypton-ios-<version>.ipa` | Apple Distribution certificate and an App Store profile: it installs through TestFlight or the App Store, not by opening the file (built only while `EXPO_TOKEN` is set) |
| krypton for VS Code | VS Code 1.90 or newer, on Linux and macOS | any | `krypton-vscode-<version>.vsix` | Unsigned |
| krypton launcher | Linux and macOS, any architecture (Python 3.12+) | any | `krypton_app-<version>-py3-none-any.whl`<br>`krypton_app-<version>.tar.gz` | The bytes PyPI serves, SHA-256 checked against PyPI |
| vibey CLI and TUI | Linux and macOS, any architecture (Python 3.12+) | any | `vibey_engine-<version>-py3-none-any.whl`<br>`vibey_engine-<version>.tar.gz` | The bytes PyPI serves, SHA-256 checked against PyPI |

Every file is listed in `SHA256SUMS` beside it, with its SHA-256, and carries a GitHub build-provenance attestation.

### Installing each

- **krypton desktop, Linux: any distribution with Flatpak (Ubuntu, Arch, Fedora), x86_64**: A single-file Flatpak bundle of the declared manifest (clients/desktop/packaging/flatpak), built from the released commit. It needs the GNOME runtime from Flathub, which `flatpak install` fetches. The GNOME runtime carries no Avahi, so this build cannot find hubs on the network by itself: pair by pasting the vibey-pair:// address the host shows beside its code (`vibey hub pair` prints it), which names the hub and the certificate to trust. `flatpak install --user krypton-desktop-<version>-linux-x86_64.flatpak`
- **krypton desktop, Linux: any distribution with Flatpak (Ubuntu, Arch, Fedora), aarch64**: A single-file Flatpak bundle of the declared manifest (clients/desktop/packaging/flatpak), built from the released commit. It needs the GNOME runtime from Flathub, which `flatpak install` fetches. The GNOME runtime carries no Avahi, so this build cannot find hubs on the network by itself: pair by pasting the vibey-pair:// address the host shows beside its code (`vibey hub pair` prints it), which names the hub and the certificate to trust. `flatpak install --user krypton-desktop-<version>-linux-aarch64.flatpak`
- **krypton desktop, Linux: Ubuntu 24.04 LTS and newer, x86_64**: `meson install` of the app into /usr, built on Ubuntu 24.04. It links against the system's GTK 4, libadwaita, libsoup 3, json-glib and Avahi, so it needs those installed; on another distribution, prefer the Flatpak. `sudo tar -xzf krypton-desktop-<version>-linux-x86_64.tar.gz -C /`
- **krypton desktop, Linux: Ubuntu 24.04 LTS and newer, aarch64**: `meson install` of the app into /usr, built on Ubuntu 24.04. It links against the system's GTK 4, libadwaita, libsoup 3, json-glib and Avahi, so it needs those installed; on another distribution, prefer the Flatpak. `sudo tar -xzf krypton-desktop-<version>-linux-aarch64.tar.gz -C /`
- **krypton desktop, macOS 15 Sequoia and newer, Apple silicon, arm64**: An app bundle that carries its own GTK 4, libadwaita and every library they load, so it needs nothing else installed (no Homebrew). Open the .dmg and drag krypton to Applications. It is not notarised yet, so macOS refuses the first launch: open it once, then choose Open Anyway in System Settings, Privacy & Security; or clear the download's quarantine flag with the command here. It finds hubs on the network over Bonjour, and macOS asks once for permission to look on the local network. `xattr -dr com.apple.quarantine /Applications/krypton.app`
- **krypton app, Web: any current browser, served as static files**: The `expo export --platform web` bundle (react-native-web), the same build CI proves bundles: static files any web server can serve. `mkdir krypton-web && tar -xzf krypton-web-<version>.tar.gz -C krypton-web && python3 -m http.server -d krypton-web`
- **krypton app, Android**: `expo prebuild` and Gradle `assembleRelease`, signed with the Android debug key because the repository holds no release keystore: for sideloading and testing, not a Play Store build. On the device itself, allow installs from unknown sources and open the file. `adb install krypton-android-<version>.apk`
- **krypton app, iOS**: Built on the runner by EAS (`eas build --local`, the `stable` profile) and signed with the project's Apple Distribution certificate and an App Store provisioning profile, which EAS holds. It is the file App Store Connect takes for TestFlight and the App Store; it does not install on a phone by opening it, and the release workflow does not submit it anywhere.
- **krypton for VS Code, VS Code 1.90 or newer, on Linux and macOS**: The same `vsce package` CI builds and smoke-tests in a real VS Code. `code --install-extension krypton-vscode-<version>.vsix`
- **krypton launcher, Linux and macOS, any architecture (Python 3.12+)**: The wheel and sdist PyPI serves, fetched and checked against PyPI's own SHA-256 digests. A pure-Python package: one wheel is every platform. `uv tool install ./krypton_app-<version>-py3-none-any.whl`
- **vibey CLI and TUI, Linux and macOS, any architecture (Python 3.12+)**: The wheel and sdist PyPI serves, fetched and checked against PyPI's own SHA-256 digests. `vibey` and its TUI, every engine and every tool are in this one wheel (ADR-0037). `uv tool install ./vibey_engine-<version>-py3-none-any.whl`

### Signing that waits for a credential

- **krypton desktop, macOS 15 Sequoia and newer, Apple silicon**: built and attached on every release, ad-hoc signed, not notarised: macOS asks you to confirm the first launch. Signing it with a Developer ID and having Apple notarise it needs an Apple Developer Program membership and these repository secrets: `MACOS_SIGNING_CERTIFICATE_P12` (the Developer ID Application certificate and its key, as a base64 .p12), `MACOS_SIGNING_CERTIFICATE_PASSWORD` and `APPLE_TEAM_ID`; and, for notarytool, either an App Store Connect API key (`APPLE_NOTARY_API_KEY_P8`, `APPLE_NOTARY_API_KEY_ID`, `APPLE_NOTARY_API_ISSUER_ID`) or an Apple ID with an app-specific password (`APPLE_NOTARY_APPLE_ID`, `APPLE_NOTARY_APP_PASSWORD`). Until every one of them is set, it is ad-hoc signed, and the release itself is unaffected. The release workflow keeps one tracking issue open until they are set (`release-binaries-macos-signing`).

### Built only while a credential is set

- **krypton app, iOS**: built and attached by a release only while `EXPO_TOKEN` is set. An iOS build that installs on a device must be signed by an Apple Developer Program member. It needs the `EXPO_TOKEN` repository secret, the project registered with EAS (its id is in clients/app/src/core/identities.json, owned by the Expo organisation `the-vibey-project`), and the Apple signing credentials stored in EAS (`npx eas-cli credentials`). EAS keeps the build number (`appVersionSource: "remote"` in clients/app/eas.json). An unsigned simulator build would run on nobody's phone, so none is produced. Without it nothing is built for this target, the release says so and keeps one tracking issue open (`release-binaries-ios`), and the release itself is unaffected.

### Not supported

- **krypton desktop, macOS, Intel**: Homebrew no longer publishes Intel macOS bottles of the GTK 4 stack: gtk4 4.24, glib 2.90, libadwaita 1.10, librsvg, cairo and pango offer Apple-silicon bottles only. An Intel build would compile all of it from source, on a platform Homebrew no longer supports, and GitHub's last Intel macOS runner (`macos-15-intel`) retires in August 2027. Apple-silicon Macs run the arm64 build; Intel Macs cannot, because Rosetta translates Intel code to Apple silicon and not the other way.
<!-- END GENERATED release:downloads -->

## The nightly

Every night something the interfaces ship from has changed on `develop` (anything under
`clients/`, `packages/vibey-core/` or the root npm manifests), the same builders run on the
integration branch and publish the files above to one rolling prerelease,
[`krypton-nightly`](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly).
Its tag moves to the commit it was built from. It is a prerelease and never the latest release,
it reaches no store, PyPI or Open VSX, and it carries the same `SHA256SUMS` and
build-provenance attestation as a versioned release, so it is checked the same way, and each
file is signed exactly as a release's is, by whichever credentials the repository holds. A
target that needs a credential the repository lacks is left out of the nightly without opening
a tracking issue; the versioned release keeps that issue. A night when nothing changed builds
nothing. To build one now, run
**Release binaries** from the Actions tab on `develop` with *nightly* ticked (ADR-0084).

## Checking a download

Each release carries `SHA256SUMS`, which lists every file with its SHA-256. In the folder you
downloaded into, run:

```bash
sha256sum --check --ignore-missing SHA256SUMS      # Linux
shasum -a 256 --check --ignore-missing SHA256SUMS  # macOS
```

Each file also carries a GitHub build-provenance attestation. It records which workflow run,
from which commit, produced the file. To check one with the GitHub CLI:

```bash
gh attestation verify krypton-desktop-<version>-linux-x86_64.flatpak --repo the-vibey-project/vibey
```

An attestation shows where a file came from. It is not a code signature. The Signing column
above says which files are signed and with what.

## Where the list comes from

The table above is generated from
[`scripts/release_binaries.toml`](https://github.com/the-vibey-project/vibey/blob/develop/scripts/release_binaries.toml).
That file declares each target as one of three kinds:

- **built** on every release;
- **built only while a credential is set**: a release made without it builds nothing for
  that target, says so, and keeps one tracking issue open;
- **not supported**, with the reason.

The release workflow builds from the same file. `python scripts/release_binaries.py check`
fails when the workflow, this page and the file disagree.
