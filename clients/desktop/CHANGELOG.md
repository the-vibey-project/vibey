# Changelog: Krypton desktop

Krypton desktop carries its own version. The Python wheel stays one distribution
(ADR-0037).

## 0.1.0 (unreleased)

- **The first Krypton desktop.** It is C17 on GTK 4 and libadwaita, with an
  `AdwNavigationSplitView` that folds on narrow windows. It covers Projects, Gates (with
  answering), Lanes, Loops and effort (to ULTRA), Budgets, Doctor, Devices and Settings.
- **The core, libkryptondesktop**, is pure C with no GTK:
  - hub documents are parsed with json-glib;
  - the hub client runs over libsoup 3: a bearer token, no redirects, and every refusal
    said in words;
  - the answer shapes mirror `vibey answer`;
  - new gates are announced once;
  - money, durations and phases are formatted in words;
  - themes (Light, Dark, System) and channels (stable, nightly);
  - pairing codes and offers, with the offer provisional until the hub's pairing change
    lands;
  - mDNS discovery of `_vibey._tcp` with Avahi and dns_sd.
- **Colours come from the design tokens**, ADR-0066. The Kr-84 mark is drawn live, stands
  still under reduced motion, and glows while a lane runs.
- **Desktop notifications**, through `GNotification`, when a gate needs you.
- **GLib tests over the core**, under ASan and UBSan, with coverage gated in CI (the
  `desktop` job, on Ubuntu and Arch).
- **Packaging, declared only**: a PKGBUILD, a Flatpak manifest, the desktop entry and the
  AppStream metadata.
