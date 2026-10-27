// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * What a phone says about the hub it is paired with (#1186). A phone never runs a hub and the
 * hub has no route to start or stop itself, so the words here send a person to the computer
 * that runs it, and promise only what the app really does: it keeps asking, and it carries on
 * by itself when the hub answers.
 */
import type { StatusRole } from './presenters-interface';

/** Whether the hub answers, and since when. `reachable` is null until the first answer. */
export interface HubWatchState {
  readonly reachable: boolean | null;
  /** Milliseconds since the epoch: when `reachable` last changed. Null before the first answer. */
  readonly since: number | null;
  /** Consecutive questions that went unanswered. */
  readonly failures: number;
}

/** The card shown in place of a screen the hub cannot be asked for. */
export interface UnreachableView {
  readonly headline: string;
  readonly body: string;
  /** What to run on the computer that hosts the hub. */
  readonly command: string;
  readonly copyLabel: string;
  /** Closing a krypton app never stops the hub; the phone reconnects on its own. */
  readonly notes: readonly string[];
}

/** One line of status: "Reachable", "Not reachable", "Checking". */
export interface HubStatusLine {
  readonly label: string;
  readonly role: StatusRole;
  /** The address, and since when. */
  readonly detail: string;
}

export interface HubStatusInterface {
  unreachable(address: string): UnreachableView;
  line(state: HubWatchState, address: string, now: number): HubStatusLine;
  /** Milliseconds to wait before asking again after `failures` unanswered questions. */
  backoffMs(failures: number): number;
}
