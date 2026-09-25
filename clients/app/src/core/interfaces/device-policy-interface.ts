// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * What a device may ask of vibey. A phone or a browser never enables paid use, never lifts a
 * cap and never chooses ULTRA without one: those are the host's alone (ADR-0063, ADR-0068).
 */
import type { Effort } from '@vibey/core';

/** Everything a Krypton device could be asked to do. */
export type DeviceAction =
  | 'view'
  | 'answer'
  | 'answer-spend'
  | 'bump'
  | 'choose-effort'
  | 'declare-paid-use'
  | 'ultra-no-cap'
  | 'set-cap'
  | 'clear-cap'
  | 'change-dsn'
  | 'run-migrations'
  | 'touch-canon';

export type DeviceDecision =
  | { readonly allowed: true; readonly confirm: boolean }
  | { readonly allowed: false; readonly reason: string };

/** One line of the effort picker on a device. */
export interface DeviceEffortOption {
  readonly effort: Effort;
  readonly label: string;
  readonly detail: string;
  /** False when this device may show it but not choose it. */
  readonly selectable: boolean;
}

export interface DevicePolicyInterface {
  decide(action: DeviceAction): DeviceDecision;
  /** Every effort, ULTRA included; ULTRA is choosable only under a cap the host declared. */
  effortOptions(capDeclared: boolean): readonly DeviceEffortOption[];
}
