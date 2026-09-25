// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Every screen of the app, and which row of the plan's parity matrix it carries. */

/** The parity matrix every Krypton client answers to. */
export type ParityFeature =
  | 'projects-and-phases'
  | 'gates'
  | 'lanes-live'
  | 'loop-engine-effort'
  | 'budgets-and-spend'
  | 'doctor'
  | 'command-palette'
  | 'notifications'
  | 'devices-and-pairing'
  | 'themes'
  | 'onboarding';

export interface ScreenSpec {
  /** The Expo Router path. */
  readonly route: string;
  readonly title: string;
  /** An icon name the tab bar draws. */
  readonly icon: string;
  readonly tab: boolean;
  readonly features: readonly ParityFeature[];
  /** What is not there yet, said plainly; empty when nothing is missing. */
  readonly gaps: readonly string[];
}

export interface ScreensInterface {
  readonly all: readonly ScreenSpec[];
  readonly tabs: readonly ScreenSpec[];
  /** The parity features no screen carries. */
  missing(): readonly ParityFeature[];
}
