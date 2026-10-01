* **release:** every GitHub Release now carries ready-built files for each user interface
  on each supported platform: krypton desktop as a Flatpak bundle and an Ubuntu 24.04 build
  (x86_64 and arm64), the krypton app as a web bundle and an Android APK (debug-signed, for
  sideloading), krypton for VS Code as a `.vsix`, and the krypton launcher and vibey's CLI
  and TUI as the wheels and sdists PyPI serves, checked against PyPI's digests. A
  `SHA256SUMS` file and a GitHub build-provenance attestation cover them all.
  `release-binaries.yml` runs after a successful Release on main and attaches to the Release
  `github-release.yml` creates, refusing a tag that names another commit; a failed build
  fails that workflow, never the release. The targets are declared in
  `scripts/release_binaries.toml` (one per interface and platform: built, waiting for a
  credential, or unsupported with the reason), the matrix is planned from it at run time,
  and `scripts/release_binaries.py check` fails when the workflow, that file and the new
  downloads page (`docs/guides/downloads.md`) disagree. iOS waits for `EXPO_TOKEN` and EAS
  signing credentials, with one tracking issue open until then; the desktop app is not built
  for macOS, for the reason the page gives. A pull request that changes how binaries are
  built runs every builder as a dry run that writes nothing.
