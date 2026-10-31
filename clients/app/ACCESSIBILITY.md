<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# krypton app: screen readers

What the phone app does for a person using VoiceOver or TalkBack, what a test proves about it,
and what only a person with a device can say. An unrun check is unknown, never passed
(ADR-0040).

## What the code does

- Every button, text input and switch is named. Buttons are named by their label, inputs and
  switches by an explicit `accessibilityLabel`; every pressable has an `accessibilityRole`.
- Each screen's title is a header, notices are alerts, and a disabled button says it is disabled.
- A screen that is still loading says "Loading" instead of showing a silent spinner.
- The tab bar's glyphs are hidden from the screen reader; each tab is named by its title.
- A pairing code, the hub address, the host token, a project name, what to build, the unwind
  reason and the command line each have a label of their own, not just a placeholder.

## What is checked automatically, and how far that goes

`test/ui/accessibility.test.tsx` renders every screen with data that makes it show its controls
(Home with a project card and its actions, Gates with a verdict, a question and a spending
gate, Effort, Budgets, Doctor, Settings, Start, Pairing, Devices, Run on GitHub, Lanes) and
reads the rendered tree. It fails when a pressable, an input or a switch has no name, or a
pressable has no role. It also fails if a screen shows fewer controls than it should, so a screen
that stops rendering its controls cannot pass by having none. The checker is itself tested on
trees built to be wrong.

**It does not prove** that a name is a good one, that the reading order is sensible, that focus
moves well after an action, that a change is announced, or that anything works with VoiceOver
or TalkBack on a device. It reads a test renderer's tree, not what a platform's accessibility
service builds from it. The tab bar (expo-router) is outside the screens it renders.

## What a person has checked

Run this with the screen reader on a real device and fill in the table. A row left "not run"
means nobody has looked.

1. Swipe through each screen: every control is announced with a name and what it is.
2. Home: a project card reads as its name, phase and cycle; its actions can be reached and used.
3. Gates: a gate's question, its options and its warning are read; an answer can be given; a
   gate that spends asks you to confirm it is you, and that prompt is readable.
4. Settings: each switch is announced with its state.
5. Pairing: the code and address fields say what they are; the camera scan can be avoided.
6. A new gate notification is announced when it arrives, and opening it lands on Gates.
7. Text still reads at the largest system text size.

| Platform | Assistive technology and version | Device | Date | Run by | Items passed | Items failed | Notes |
|---|---|---|---|---|---|---|---|
| iOS | VoiceOver | not run | | | | | |
| Android | TalkBack | not run | | | | | |

## Not done

- The Share action, the home-screen widget and notification answer actions of the same issue
  (#1698) are separate slices and are not built here.
- Whether a status's colour alone carries meaning anywhere is not audited; the text of each
  status is always present.
