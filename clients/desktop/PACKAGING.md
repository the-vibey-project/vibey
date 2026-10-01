# Packaging krypton desktop: the plan

No store or package repository carries krypton desktop yet. Every store recipe below is
**declared only**: it is written down and versioned, but no store, repository or signing
identity is touched until the operator decides. What every release does carry, attached to
its GitHub Release by `.github/workflows/release-binaries.yml`, is an unsigned Flatpak bundle
of the manifest below and an Ubuntu 24.04 build, each for x86_64 and arm64
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
| Meson | `-Dchannel=stable` | `-Dchannel=nightly` |

This mirrors PyPI `vibey` and TestPyPI `vibey-dev` (ADR-0028). Stable is always the
default.

## Per platform

| Platform | Artefact | Recipe | Status |
|---|---|---|---|
| Arch | `PKGBUILD` | [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD) | Declared. It goes to the AUR on the operator's word. |
| Flatpak (any Linux) | flatpak-builder manifest | [`packaging/flatpak/io.github.the_vibey_project.krypton.yml`](packaging/flatpak/io.github.the_vibey_project.krypton.yml) | A bundle of it, built from the released commit, is attached to every GitHub Release. It goes to Flathub on the operator's word. |
| Ubuntu (24.04, and 26.04 per #1116) | `.deb` | `meson install` into a `debian/` tree | Planned. A `meson install` tarball built on 24.04 is attached to every GitHub Release meanwhile. |
| macOS | signed `.app` in a `.dmg`, with the GTK runtime | gtk-mac-bundler | Planned. Signing and notarisation sit behind secrets. |

CI already proves the parts every recipe relies on, on Ubuntu and on Arch (the CI job `desktop`):

- the build;
- the tests;
- the nightly channel;
- `desktop-file-validate`;
- `appstreamcli validate`.

## Order of work

1. **Release assets.** Done for the Flatpak bundle and the Ubuntu tarball:
   `release-binaries.yml` builds both from the released commit and attaches them to the
   vibey GitHub Release. Still to come: `krypton-desktop-vX.Y.Z` tags for the recipes to
   fetch, and the Arch package as an asset. None of this is a store upload.
2. **Nightly.** The same workflow on `develop` builds `-Dchannel=nightly` and attaches it
   to a rolling pre-release.
3. **Stores**, each as its own pull request the operator merges:
   - a Flathub submission;
   - an AUR `krypton-desktop` and `krypton-desktop-nightly`;
   - a macOS Developer ID with notarisation.
4. **Ubuntu `.deb`.** Built in CI from the same `meson install`, for 24.04 and 26.04.
