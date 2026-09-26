# Packaging Krypton desktop: the plan

Nothing here is published yet. Every recipe below is **declared only**: it is written down
and versioned, but no store, repository or signing identity is touched until the operator
decides. Publishing needs secrets this repository does not hold, and an act that cannot
easily be undone, such as a Flathub submission, an AUR upload or a notarised release,
waits for a human (sub-doctrine 12.d).

## Identities: two channels, side by side

| | Stable (default) | Nightly |
|---|---|---|
| Built from | `main` | `develop` |
| App id | `io.github.the_vibey_project.Krypton` | `io.github.the_vibey_project.Krypton.Nightly` |
| Name people see | Krypton | Krypton Nightly |
| Settings | `~/.config/krypton/` | `~/.config/krypton-nightly/` |
| Meson | `-Dchannel=stable` | `-Dchannel=nightly` |

This mirrors PyPI `vibey` and TestPyPI `vibey-dev` (ADR-0028). Stable is always the
default.

## Per platform

| Platform | Artefact | Recipe | Status |
|---|---|---|---|
| Arch | `PKGBUILD` | [`packaging/arch/PKGBUILD`](packaging/arch/PKGBUILD) | Declared. It goes to the AUR on the operator's word. |
| Flatpak (any Linux) | flatpak-builder manifest | [`packaging/flatpak/io.github.the_vibey_project.Krypton.yml`](packaging/flatpak/io.github.the_vibey_project.Krypton.yml) | Declared. It goes to Flathub on the operator's word. |
| Ubuntu (24.04, and 26.04 per #1116) | `.deb` | `meson install` into a `debian/` tree | Planned. |
| macOS | signed `.app` in a `.dmg`, with the GTK runtime | gtk-mac-bundler | Planned. Signing and notarisation sit behind secrets. |

CI already proves the parts every recipe relies on, on Ubuntu and on Arch (the CI job `desktop`):

- the build;
- the tests;
- the nightly channel;
- `desktop-file-validate`;
- `appstreamcli validate`.

## Order of work

1. **Release tag.** `krypton-desktop-vX.Y.Z` tags, cut from `main`, name the source the
   recipes fetch. `release.yml` gains a desktop step that builds the Flatpak bundle and
   the Arch package as release assets. That is still not a store upload.
2. **Nightly.** The same workflow on `develop` builds `-Dchannel=nightly` and attaches it
   to a rolling pre-release.
3. **Stores**, each as its own pull request the operator merges:
   - a Flathub submission;
   - an AUR `krypton-desktop` and `krypton-desktop-nightly`;
   - a macOS Developer ID with notarisation.
4. **Ubuntu `.deb`.** Built in CI from the same `meson install`, for 24.04 and 26.04.
