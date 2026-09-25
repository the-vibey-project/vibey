// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The device's own refusals, checked before any request leaves it. The hub refuses the same
 * things (it offers no route for them), so this is the second lock, not the only one.
 * Declared by `interfaces/device-policy-interface.ts`.
 */
import { Efforts } from '@vibey/core';
import type { Effort } from '@vibey/core';
import type {
  DeviceAction,
  DeviceDecision,
  DeviceEffortOption,
  DevicePolicyInterface,
} from './interfaces/device-policy-interface';

export class DevicePolicy implements DevicePolicyInterface {
  /** Actions only the host may take, each with the reason a person is shown. */
  static readonly HOST_ONLY: Readonly<Partial<Record<DeviceAction, string>>> = {
    'declare-paid-use': 'Paid use is declared on the host computer, never from a device.',
    'ultra-no-cap': 'ULTRA without a cap is chosen on the host computer, behind its warnings, never from a device.',
    'set-cap': 'Budget caps are set on the host computer, never from a device.',
    'clear-cap': 'Budget caps are lifted on the host computer, never from a device.',
    'change-dsn': "vibey's database is configured on the host computer, never from a device.",
    'run-migrations': 'Migrations run on the host computer, never from a device.',
    'touch-canon': 'The canon changes only by the operator, never from a device.',
  };

  decide(action: DeviceAction): DeviceDecision {
    const refusal = DevicePolicy.HOST_ONLY[action];
    if (refusal !== undefined) {
      return { allowed: false, reason: refusal };
    }
    // Spending is re-verified on the device (Face ID, Touch ID or the passcode) every time.
    return { allowed: true, confirm: action === 'answer-spend' };
  }

  effortOptions(capDeclared: boolean): readonly DeviceEffortOption[] {
    return Efforts.ALL.map((effort: Effort) => {
      if (effort !== Efforts.ULTRA) {
        return { effort, label: effort, detail: `Every attempt at ${effort}.`, selectable: true };
      }
      return capDeclared
        ? {
            effort,
            label: 'ULTRA',
            detail: 'No turn limit: pass after pass until you stop it or the declared cap binds.',
            selectable: true,
          }
        : {
            effort,
            label: 'ULTRA',
            detail: 'Needs a cap declared on the host first. A device never chooses ULTRA without one.',
            selectable: false,
          };
    });
  }
}
