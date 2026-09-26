<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# Motion

Motion in vibey and krypton explains. It shows where something came from, where it went, and
what just changed. It is quick, it is never the only way to learn a state, and it can always
be interrupted. It runs at 60 fps, and every animation respects reduced motion.

The source of truth is `design/tokens/motion.tokens.json`; the rest of the design system is
described in the [overview](README.md).

## Durations

`motion.duration.*`, with the reduced-motion twin from `motion.reduced.duration.*`:

| Token | Duration | Under reduced motion | For |
|---|---|---|---|
| `instant` | 80 ms | 0 | Presses, toggles, a checkbox's tick |
| `fast` | 140 ms | 0 | Hover, focus, small exits |
| `base` | 220 ms | 80 ms | Most entrances, a theme change's crossfade |
| `slow` | 360 ms | 80 ms | Panels, sheets, a gate's attention glow |
| `deliberate` | 560 ms | 120 ms | Celebrations: a run finished, a gate cleared |
| `ambient` | 2400 ms | 0 (the loop stops) | Slow background loops: a running lane's pulse, the ULTRA aura, the atom's shells |

## Easings

`motion.easing.*`, as cubic Béziers:

- **standard** `(0.2, 0, 0, 1)`: most movement. It settles firmly.
- **enter** `(0, 0, 0, 1)`: arriving things decelerate.
- **exit** `(0.3, 0, 1, 1)`: leaving things accelerate away.
- **emphasized** `(0.2, 0, 0, 1.25)`: a small overshoot, kept for moments of delight.
- **linear** `(0, 0, 1, 1)`: progress and ambient loops only.

The named transitions pair them: **hover** is fast and standard, **enter** is base and enter,
**exit** is fast and exit, and **celebrate** is deliberate and emphasized.

## Reduced motion

When the platform asks for less motion, movement becomes a short crossfade or nothing.
Examples are CSS `prefers-reduced-motion: reduce`, iOS and Android reduce motion, and GTK
`gtk-enable-animations` set false. Under reduced motion:

- durations fall to the `motion.reduced` values above;
- every easing becomes linear;
- ambient loops stop;
- nothing uses parallax, scaling or looping.

The CSS token layer swaps these values for you. Other platforms read `motion.reduced`
directly.

## Signature moments

- **A lane starts:** its card fades in and rises 8 px (base, enter).
- **A gate needs you:** the card's border glows once in the warning colour (slow, standard),
  together with the `gate-needs-you` sound.
- **A run finishes:** a single celebrate transition on the success colour.
- **ULTRA:** a slow aura in the ULTRA colour breathes around the effort control. It is
  ambient, so it stops under reduced motion.
- **The atom:** in animated contexts (the web, the apps, the splash screen) the mark's four
  shells turn at different speeds, the outer shells slower, as orbits do. One revolution
  takes a few ambient beats. Under reduced motion each electron rests where the static mark
  draws it, so the still and moving marks are the same picture.
- **A theme change:** colours crossfade (fast, standard); nothing moves.

## Rules

- Never animate layout on scroll.
- Never block input on an animation.
- Nothing flashes more than three times a second (WCAG 2.3.1).
- Sound and motion for the same event start together.

## Using the tokens

- **CSS:** `var(--v-motion-duration-base)`, `var(--v-motion-easing-standard)` from
  `design/dist/css/tokens.css`, already swapped under `prefers-reduced-motion`.
- **TypeScript:** `motionFor(reduced)` from `design/dist/ts/tokens.ts`.
- **C:** macros such as `VIBEY_MOTION_DURATION_BASE` and `VIBEY_MOTION_EASING_STANDARD` from
  `design/dist/c/vibey_tokens.h`.
- **SVG:** the `*-animated.svg` files in `design/identity/` carry their own CSS, and it honours
  reduced motion.
