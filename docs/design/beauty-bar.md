# The Beauty Bar

**What this is.** The checkable bar that sub-doctrine **12.k** (*beauty is the first
measure*) cites. It turns the operator's ruling into items a test or a reviewer can check.
The ruling, in the operator's words:

> "ALWAYS FULLY COMPREHENSIVE, FULLY UP TO DATE, INSANELY BEAUTIFUL, INSANELY
> SOPHISTICATED, INSANELY GORGEOUS, INSANELY WOW-FACTOR PRODUCING and INSANELY POWERFUL
> AND FUN FOREVER AMEN!"

**Where it applies.** Every surface a person touches:

- every client app: the desktop app, the mobile apps and the web app;
- the VS Code extension;
- the documentation site;
- notifications and sounds.

**How it is held.** Each item below has an **ID** (`BB-n`), a **rule**, and a **check**.
The check says how you know the rule is met: by an automated test (*machine*), by a person
(*reviewer*), or both. An item whose automated check does not exist yet is not met; it is
*unchecked*, and the release gate says so (sub-doctrine 10.f). A surface fails the bar if it
fails any item.

**Who decides.** The machine runs every check it can and gathers the evidence. The
judgement of beauty stays with a person (12.e): the operator's sign-off of the release
gallery (BB-8) closes the gate, and nothing else does.

The design rationale is in
[ADR-0062](../architecture/decisions/0062-the-beauty-law-and-its-bar.md).

---

## BB-1 — One design system

**Rule.** All colour, type, spacing, radius, elevation, motion and sound on every surface
come from one set of shared design tokens, in W3C Design Tokens format. No surface defines
a value of its own.

**Check.**

- *Machine:* the generated outputs (CSS custom properties, the TypeScript module, GTK CSS
  and the C header, the paper's colours) match what the generators emit from the tokens
  today. A drift test fails on any difference.
- *Machine:* no hard-coded colour, font size, spacing, duration or easing appears in a
  client's styles or components outside the generated token files. A lint rule or meta test
  scans for literals.
- *Reviewer:* a new visual or sonic value arrives as a token change, not as a literal.

## BB-2 — Dark and light themes, and three theme modes

**Rule.** Every surface ships a dark theme and a light theme, both designed on purpose.
Every GUI platform (the desktop app, the mobile apps, the web app, the VS Code extension's
own views and the docs site) offers **three theme modes: Light, Dark and System.**

- **System is the default.** It follows the operating system's appearance and switches
  live when the operating system switches, with no restart and no reload.
- **The choice persists per device.** A choice made on one device is kept on that device
  across restarts, and does not change any other device.
- **The choice is in each client's settings,** under the same name on every client.

**Check.**

- *Machine:* every colour token has a value in both themes. A test fails on a token with
  only one.
- *Machine:* on each GUI platform, a test confirms that the three modes exist, that a fresh
  install starts in System, that switching the emulated operating-system appearance while
  in System re-themes the open screen live, and that a chosen mode survives a restart.
- *Machine:* the parity meta test (BB-7) finds the theme setting on every client.
- *Machine:* screenshot tests capture every screen in both themes (BB-8).
- *Reviewer:* neither theme is an automatic inversion of the other.

## BB-3 — Accessibility

**Rule.** Every surface meets all of these:

- **WCAG 2.2 level AA**, including contrast of at least 4.5:1 for text and 3:1 for large
  text and interface components, in both themes;
- **screen readers:** every control has an accessible name and role, and every image a text
  alternative or a decorative mark;
- **keyboard:** every action is reachable and operable by keyboard alone, with a visible
  focus indicator and no focus trap;
- **reduced motion:** when the system asks for reduced motion, non-essential animation stops
  and essential motion becomes a cross-fade or a cut;
- **dynamic type:** text follows the system text size up to at least 200% without clipping
  or overlap.

**Check.**

- *Machine:* automated audits pass on every screen: axe for the web app and the docs site,
  and the platform accessibility checks for iOS, Android and GTK.
- *Machine:* a contrast test computes every text and background token pair in both themes.
- *Machine:* keyboard-only end-to-end flows complete the parity-matrix actions (BB-7).
- *Reviewer:* a screen-reader walk-through of the first-run flow, recorded per release.

## BB-4 — First run in under 60 seconds

**Rule.** A new person gets from installing a client to their first result in **under 60
seconds**, measured, and a guided first run leads them there.

**Check.**

- *Machine:* an end-to-end test times install-complete to first-result on a clean machine or
  simulator. It fails at 60 s or more, and it records the figure as evidence.
- *Machine:* the guided first run exists (the extension's walkthrough, each app's
  onboarding flow) and the test drives it.
- *Reviewer:* the first run is reviewed as a delight moment in the release gallery.

## BB-5 — Purposeful motion at 60 fps

**Rule.** Motion shows where something came from, where it went, or what changed.
Decoration alone is not a reason. Every animation holds **60 frames per second** on the
reference devices, and respects reduced motion (BB-3).

**Check.**

- *Machine:* every duration and easing is a motion token (BB-1).
- *Machine:* frame-timing traces for each signature animation (the lane orbit, ULTRA's aura,
  spend flows) show no dropped frames beyond the declared budget on the reference devices.
  The frame budget and the reference devices are declared in configuration (12.c, 12.h);
  until they are, this check is reported as unchecked.
- *Machine:* a test with reduced motion on confirms that non-essential animation is off.
- *Reviewer:* each animation's purpose is named in the design system's motion language.

## BB-6 — Every state designed

**Rule.** Every screen has a designed **empty** state, **error** state and **loading**
state. An empty state says what belongs there and how to get it. An error says what
happened, in plain words, and what to do next. Loading shows progress without a layout
jump.

**Check.**

- *Machine:* each screen has a test or a snapshot for each of its three states.
- *Machine:* no raw exception, stack trace, error code without explanation, or blank panel
  reaches a person. A test drives each error path.
- *Reviewer:* the three states of every screen appear in the release gallery (BB-8).

## BB-7 — Feature parity

**Rule.** Every client offers the same features. The parity matrix:

| Feature | Desktop | Mobile | Web | VS Code |
|---|---|---|---|---|
| Projects and phases | ✓ | ✓ | ✓ | ✓ |
| Gates (answer) | ✓ | ✓ | ✓ | ✓ |
| Lanes live (watch, stop, wind-down, prompt) | ✓ | ✓ | ✓ | ✓ |
| Loop, engine and effort picker, including ULTRA | ✓ | ✓ | ✓ | ✓ |
| Budgets and spend | ✓ | ✓ | ✓ | ✓ |
| Doctor | ✓ | ✓ | ✓ | ✓ |
| Command palette and slash commands | ✓ | ✓ | ✓ | ✓ |
| Notifications | ✓ | ✓ | ✓ | ✓ |
| Devices and pairing | ✓ | ✓ | ✓ | ✓ |
| Themes | ✓ | ✓ | ✓ | ✓ |
| Onboarding | ✓ | ✓ | ✓ | ✓ |

One exception is the law's, not the design's: the unlimited budget (no cap) can be
switched **on** only from the host, never from a phone or the web app (sub-doctrine 8.b).
Every client can show it and switch it **off**.

**Check.**

- *Machine:* a meta test reads the shared command table in `@vibey/core` and fails when a
  client lacks a command, or has one the table does not list.
- *Reviewer:* the release gallery shows each feature on each client.

## BB-8 — The release gallery, signed off by the operator

**Rule.** Each release produces a gallery: a screenshot of every screen, in dark and light,
on every platform, and a short recording of every signature flow (first run, pairing,
answering a gate, a live lane, the ULTRA warnings). The operator reviews it and signs it
off. Without that sign-off, the release does not ship.

**Check.**

- *Machine:* the gallery is generated by the release pipeline, not assembled by hand, and it
  is published for review.
- *Machine:* the release gate reads the recorded sign-off for the exact release commit. A
  sign-off for another commit does not count.
- *Reviewer:* the operator. This is the judgement 12.e keeps with a human.

## BB-9 — Fully up to date

**Rule.** Every surface runs on current dependencies and current platform APIs: current
toolkits, SDKs, target OS versions and libraries, and no deprecated API where a supported
replacement exists. "Current" means within the declared currency window below.

**Check.**

- *Machine:* CI reports every outdated dependency and every deprecated platform API a
  client uses, and fails when one is older than the declared currency window. The window is
  declared in configuration (12.c, 12.h), not written into the check.
- *Machine:* a dependency update that breaks a client fails that client's CI job, so an
  update is never held back to avoid finding out.
- *Reviewer:* an exception names its reason and its expiry.

## BB-10 — Notifications and sounds

**Rule.** Notifications and sounds are one system, delivered natively by whichever client
is installed:

- **event classes:** a gate needs you; a run or an ULTRA pass finished; a run failed or was
  parked; a budget step; an unlimited-spend reminder; a device paired;
- **delivery:** the desktop app on macOS and Linux, push on mobile, and VS Code's
  notifications, with the platform's own path as the fallback;
- **manners:** bursts are coalesced; Focus and Do Not Disturb are respected; each class is
  opt-in; there is a volume control and a silent mode; nothing is sent per turn;
- **actions:** each notification offers the next step (Open, Answer, Stop);
- **sounds:** vibey's own cues, original, under one second each, loudness-normalised to
  −18 LUFS short-term, with provenance and licence recorded.

**Check.**

- *Machine:* a test maps every event class to its delivery on each client, and fails on an
  event with no class.
- *Machine:* a burst test confirms coalescing, and a test confirms that silent mode and each
  class's opt-out suppress delivery.
- *Machine:* each sound file is measured for length and loudness, and has a provenance
  record.
- *Reviewer:* the sounds are reviewed by ear, and the notifications appear in the release
  gallery.

## BB-11 — Stable and nightly channels, side by side

**Rule.** Every GUI platform (the desktop app, the mobile apps, the web app and the VS Code
extension) ships two channels:

- **stable,** built from `main`;
- **nightly** (the dev channel), built from `develop`.

**Stable is always the default:** every install link, store listing, package-manager
command and guide leads to stable unless a person asks for nightly by name. The two
channels install **side by side** on the same device, with distinct application IDs (bundle
ID, package name, extension ID, desktop file ID) and distinct icons: nightly's icon carries a
nightly badge. Installing, updating or removing one never touches the other.

**Check.**

- *Machine:* the release pipeline builds stable only from `main` and nightly only from
  `develop`, and fails on a build from any other ref.
- *Machine:* a test reads each platform's packaging and confirms that the two channels'
  application IDs differ, that nightly's icon set carries the badge, and that every default
  install path (links, listings, package-manager commands, the docs' install steps) names
  stable.
- *Machine:* an install test puts both channels on one machine or simulator, launches each,
  and confirms that removing one leaves the other working.
- *Reviewer:* both icons appear in the release gallery (BB-8), and a person can tell them
  apart at a glance.
