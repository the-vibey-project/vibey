// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The words about the hub's reachability, and how patiently to ask again. Declared by
 * `interfaces/hub-status-interface.ts`.
 *
 * Ruling 1 of #1186 (one hub per user) holds here without code: a phone never runs `vibey`, so
 * it cannot start a second hub. Nothing in this file starts or stops a hub, and the hub API has
 * no route that does (docs/reference/hub-api.json).
 */
import type { HubStatusInterface, HubStatusLine, HubWatchState, UnreachableView } from './interfaces/hub-status-interface';

export class HubStatus implements HubStatusInterface {
  /** What to run on the computer that hosts the hub. Idempotent: it does nothing if one runs. */
  static readonly START_COMMAND = 'vibey hub start';
  /** The first wait after an unanswered question; each unanswered one doubles it. */
  static readonly FIRST_RETRY_MS = 2_000;
  /** The longest wait while the hub is down: the cap that keeps a flat battery from this. */
  static readonly CAP_MS = 60_000;
  /** How often a hub that answers is asked again, to notice when it goes. */
  static readonly STEADY_MS = 30_000;

  unreachable(address: string): UnreachableView {
    return {
      headline: 'The hub on your computer is not running',
      body:
        `krypton talks to the hub at ${address}, and nothing answers there. Either the hub is not ` +
        'running, or this phone cannot reach that computer (check that it is on and on the same network).',
      command: HubStatus.START_COMMAND,
      copyLabel: 'Copy the command',
      notes: [
        'Run it on the computer that hosts the hub. If a hub is already running it says so and changes nothing.',
        'Closing a krypton app, on any device, never stops the hub.',
        'This phone asks again by itself and carries on the moment the hub answers.',
      ],
    };
  }

  line(state: HubWatchState, address: string, now: number): HubStatusLine {
    if (state.reachable === null) return { label: 'Checking', role: 'info', detail: address };
    const since = state.since === null ? '' : ` · since ${HubStatus.ago(now - state.since)}`;
    return state.reachable
      ? { label: 'Reachable', role: 'success', detail: `${address}${since}` }
      : { label: 'Not reachable', role: 'danger', detail: `${address}${since}` };
  }

  backoffMs(failures: number): number {
    const steps = Math.max(0, failures - 1);
    return Math.min(HubStatus.CAP_MS, HubStatus.FIRST_RETRY_MS * 2 ** Math.min(steps, 16));
  }

  /** "just now", "4 min ago", "3 h ago", "2 days ago". */
  private static ago(ms: number): string {
    const minutes = Math.floor(Math.max(0, ms) / 60_000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} h ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? '' : 's'} ago`;
  }
}
