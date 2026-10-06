# Changelog: krypton desktop

krypton desktop carries its own version. The Python wheel stays one distribution
(ADR-0037).

## 0.1.0 (unreleased)

- **The first krypton desktop.** It is C17 on GTK 4 and libadwaita, with an
  `AdwNavigationSplitView` that folds on narrow windows. It covers Projects, Gates (with
  answering), Lanes, Loops and effort (to ULTRA), Budgets, Doctor, Devices and Settings.
- **The core, libkryptondesktop**, is pure C with no GTK:
  - hub documents are parsed with json-glib;
  - the hub client runs over libsoup 3: the host's bearer token or a paired device's
    signature, no redirects, and every refusal said in words;
  - the answer shapes mirror `vibey answer`;
  - new gates are announced once;
  - money, durations and phases are formatted in words;
  - themes (Light, Dark, System) and channels (stable, nightly);
  - pairing with a hub, as ADR-0068 defines it: the host's 6-digit code or its
    `vibey-pair://` address is claimed from `/api/v1/pairing/claim`, the hub's certificate
    fingerprint is pinned (any other certificate is refused before the code is sent), the
    device key is kept owner-only beside the settings, and every later request is signed
    with it;
  - mDNS discovery of `_vibey._tcp` with Avahi and dns_sd;
  - commands run on the repository's GitHub-hosted runners through the hub, as `vibey -w`
    runs them (ADR-0085): the typed command line split into words (double quotes keep
    spaces), `POST /api/v1/workflows/runs`, and a poller over
    `GET /api/v1/workflows/runs/{request_id}` every 10 s that stops after 60 minutes with
    where the run still is, waits out a hub that does not answer, 429 and 502, and is
    cancellable.
- **Run on GitHub**, a page for the above: the command, a Run button, the run's state, a link
  to its GitHub run, its exit code and what it printed, in a selectable monospace view. A
  403 (the device lacks the `workflows` scope, the scopes of what the command does, or the
  command is one the hub never runs) and a 503 (the workflows are off on that hub) are said
  in words. The paired device needs the `workflows` scope, and the Devices page now says
  what each scope it holds lets it do.
- **Colours come from the design tokens**, ADR-0066. The Kr-84 mark is drawn live, stands
  still under reduced motion, and glows while a lane runs.
- **Desktop notifications**, through `GNotification`, when a gate needs you.
- **GLib tests over the core**, under ASan and UBSan, with coverage gated in CI (the
  `desktop` job, on Ubuntu and Arch).
- **Packaging, declared only**: a PKGBUILD, a Flatpak manifest, the desktop entry and the
  AppStream metadata.
