---
description: The ready-built files attached to every vibey release, for each krypton app and platform, how to check a download, what is signed, and how to install each.
---

# Download a krypton app and check it

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Every vibey release on
> [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) attaches a ready-built
> file for each krypton app (desktop, editor extension, phone, browser) plus `SHA256SUMS` and a
> build-provenance attestation. Find your file in [the table](#what-each-release-carries),
> download it, check it with one command, then install it. A few minutes, plus the download.
> vibey itself installs with the one command on [Install](install.md).

This page is for anyone choosing which file to download. The step-by-step install for each
platform, and what each app needs on the computer that runs the hub, is on
[Install](install.md#the-krypton-apps-platform-by-platform). Windows is not a supported platform,
so nothing here is built for it.

## The lesson

Daniel had two files in his Downloads folder with nearly the same name and was not sure which
one he had clicked.

**Daniel:** Professor, the release page has a file called `SHA256SUMS`, and the download page
talks about attestations and signatures. Are those three names for one thing?

**Professor Feynman:** Three different things. Think of a parcel. The checksum is a list, sent
separately, of exactly what should be in the box. You unpack and compare. If one item differs,
you know the parcel was damaged or swapped on the way.

**Daniel:** And the attestation?

**Professor Feynman:** That is the delivery note from the factory, stamped by the carrier: this
box was packed by this machine, from this order, on this day. It tells you where the file came
from. GitHub stamps it, so you can check it with GitHub's own tool.

**Daniel:** Then a signature is the same as the delivery note?

**Professor Feynman:** No, and that is the gap worth closing. A signature is the maker's own
seal, which your computer itself checks before it opens the box: Apple's for a Mac app, Google's
or a store's for a phone app. An attestation says where a file came from; it does not make your
Mac trust it. That is why the macOS app, which carries only an ad-hoc seal today, still needs you
to say "open anyway" once.

**Daniel:** So the checksum says the file is unchanged, the attestation says which build made
it, and the signature is what my computer checks before it runs it.

**Professor Feynman:** Exactly. And the table on this page says, for every file, which seal it
has, so nothing is promised that is not there. The picture stops in one place: a parcel's list
travels in a separate envelope, and `SHA256SUMS` sits on the same release page, so it proves the
download is intact, not that the page itself is honest. The attestation covers that.

## Do it

1. **Find your file** in [the table below](#what-each-release-carries). `<version>` is that
   app's own version (0.4.0 at the time of writing).

2. **Download it and `SHA256SUMS`** from the same release on
   [GitHub Releases](https://github.com/the-vibey-project/vibey/releases), into one folder.

3. **Check it.** In that folder:

   ```bash
   shasum -a 256 --check --ignore-missing SHA256SUMS   # macOS
   sha256sum --check --ignore-missing SHA256SUMS       # Linux
   ```

   You should see your file's name followed by `OK`. Anything else means the file is damaged or
   not the release's: download it again.

4. **Optionally, check where it came from**, with the GitHub CLI:

   ```bash
   gh attestation verify krypton-desktop-<version>-linux-x86_64.flatpak --repo the-vibey-project/vibey
   ```

   You should see that the attestation verified against the `the-vibey-project/vibey` repository.

5. **Install it** with the steps on [Install](install.md#the-krypton-apps-platform-by-platform),
   or the one-line install in the table's last column.

## Daniel's teach-back

**Daniel:** Each release carries one file per app and platform, plus `SHA256SUMS`. I check my
download against `SHA256SUMS` and look for `OK`. If I want to know which build made it, I verify
its attestation with `gh attestation verify`. And the Signing column tells me whether my computer
will trust the file by itself, or whether I have to confirm it once, as with the Mac app.

**Professor Feynman:** Right. One more: the iOS file is in the table but cannot be installed by
opening it, and the web bundle cannot reach a hub today. The notes under the table say why.

## The details

Every vibey release on GitHub carries ready-built files for each user interface, on each
platform the project supports. They are attached to the release's page under
[Releases](https://github.com/the-vibey-project/vibey/releases), beside the source archives.
Each file is built from the released commit by
[`release-binaries.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/release-binaries.yml)
after the release has been published to PyPI.

The Python files here (the `vibey-engine` and `krypton-app` wheels and source distributions) are
the same bytes PyPI serves, attached so that one release page has everything. The usual way to
install vibey is the one command on [Install](install.md), which installs from PyPI.

A release carries thirteen files and `SHA256SUMS`: four Linux builds of the desktop client and
its macOS `.dmg`, the web bundle, the Android and iOS packages, the VS Code extension, and the
wheel and source distribution of each of the two Python packages. The iOS package is built only
while its credential is set, so without it there are twelve. `vibey-v0.4.0`, the latest release,
carries all thirteen. The version numbers were reset to 0.x in November 2026 (#1898); under the
retired 3.x numbering, 3.3.0 was the first release to attach any files (eleven), and 3.4.0 added
the macOS and iOS builds. The table below is the declaration, and it is generated, so it is the
one to trust if this paragraph ever disagrees with it.

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

### Two notes on the generated table

- **The web bundle cannot reach a hub as the table installs it.** Served by
  `python3 -m http.server` on its own address, the page cannot read the hub's answers: the hub
  sends no cross-origin (CORS) headers, by design (`src/vibey/infrastructure/hub/app.py`), and
  it does not serve the web app from its own address. We have not run it end to end; this is
  what the code says. Use krypton desktop or the VS Code extension instead
  ([Install: the web app](install.md#the-web-app)). The install line above comes from
  `scripts/release_binaries.toml`, which is where it will change.
- **The iOS file cannot be installed from the release.** The release workflow submits it to no
  store, so there is no TestFlight or App Store listing. Running the app on an iPhone today means
  Expo Go from a copy of the repository ([Install](install.md#the-krypton-apps-platform-by-platform)).
  The phone app also cannot pair with a code yet; see
  [Install: phone and tablet](install.md#phone-and-tablet).

### The nightly

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
nothing. To build one now, run **Release binaries** from the Actions tab on `develop` with
*nightly* ticked
([ADR-0084](../architecture/decisions/0084-krypton-nightly.md)).

### An attestation is not a signature

An attestation records which workflow run, from which commit, produced the file. It shows where
a file came from; it is not a code signature, and it does not make your operating system trust
the file. The Signing column says which files are signed and with what.

### Where the list comes from

The table above is generated from
[`scripts/release_binaries.toml`](https://github.com/the-vibey-project/vibey/blob/develop/scripts/release_binaries.toml).
That file declares each target as one of three kinds:

- **built** on every release;
- **built only while a credential is set**: a release made without it builds nothing for
  that target, says so, and keeps one tracking issue open;
- **not supported**, with the reason.

The release workflow builds from the same file. `python scripts/release_binaries.py check`
fails when the workflow, this page and the file disagree
(`tests/meta/test_release_binaries.py` runs it in CI).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `shasum` or `sha256sum` prints `FAILED` for your file | The download is damaged, incomplete, or not the release's file. | Delete it and download it again from the release page. |
| `SHA256SUMS: No such file or directory` | `SHA256SUMS` is not in the folder you ran the command in. | Download `SHA256SUMS` from the same release into the same folder. |
| `no file was verified`, or nothing at all about your file | Your file's name differs from the release's (a browser may add ` (1)`), so the list does not name it. | Rename it to the exact name in the release, or download it again into an empty folder. |
| macOS says krypton "cannot be opened" or is damaged | Gatekeeper's quarantine flag on an app that is not notarised. | `xattr -dr com.apple.quarantine /Applications/krypton.app`, or **Open Anyway** in **System Settings → Privacy & Security**. |
| The iOS file will not open on an iPhone | An `.ipa` is not installed by opening it, and this one is listed in no store. | Use Expo Go from a copy of the repository ([Install](install.md#the-krypton-apps-platform-by-platform)). |
| The web app loads but never shows your projects | The hub refuses cross-origin pages. | Use krypton desktop or the VS Code extension ([Install: the web app](install.md#the-web-app)). |
| A file for your platform is missing from a release | It needs a credential the repository did not hold, or the platform is not supported. | See the two lists under the table; the nightly may carry it. |

## Where next

- [Install](install.md): the one command for vibey itself, and every app's install steps.
- [Let another LLM drive vibey](drive-from-an-llm.md): use Claude Code or another chat tool
  instead of an app.
- [VS Code extension](vscode-extension.md): what the editor extension does once installed.

## Say it in one line

Each vibey release attaches a file per krypton app plus SHA256SUMS; check your download for OK,
and the Signing column tells you what your computer will trust by itself.
