// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Following a running project: what changed, in words, until it needs you or is finished. */
import type { VibeyGate } from './vibey-cli-interface';
import type { TimerInterface } from './workflows-interface';

/** One look at a project: its phase, its queue, and the questions waiting on a person. */
export interface ProjectSnapshot {
  readonly name: string;
  /** vibey's phase value, lower case: `design`, `build`, `done`... */
  readonly phase: string;
  readonly cycle?: number;
  readonly maxCycles?: number;
  /** Job counts by state (`ready`, `leased`, `failed`...). */
  readonly queue: Readonly<Record<string, number>>;
  readonly gates: readonly VibeyGate[];
}

/** A change worth telling a person about. */
export type ProjectEvent =
  | { readonly kind: 'phase'; readonly name: string; readonly from: string | undefined; readonly to: string; readonly cycle?: number; readonly maxCycles?: number }
  | { readonly kind: 'gate'; readonly gate: VibeyGate }
  | { readonly kind: 'failed'; readonly name: string; readonly count: number }
  | { readonly kind: 'stalled'; readonly name: string; readonly seconds: number }
  | { readonly kind: 'working'; readonly name: string; readonly phase: string; readonly ready: number; readonly running: number }
  | { readonly kind: 'finished'; readonly name: string; readonly phase: 'done' | 'abandoned' };

/** Why a follow handed back. */
export type FollowEnd = 'needs-you' | 'finished' | 'timeout' | 'cancelled';

export interface FollowOptions {
  readonly pollMs: number;
  /** How long to watch before handing back. */
  readonly maxMs: number;
  /** Say something after this long with nothing else to say, so silence never looks like a hang. */
  readonly heartbeatMs: number;
  /** Work is queued and nothing is running it for this long: say so. */
  readonly stallMs: number;
  readonly onEvent: (event: ProjectEvent) => void;
}

/** What a follower reads: a project's status and its open gates. */
export interface ProjectReaderInterface {
  status(projectId?: string): Promise<{
    readonly name: string;
    readonly phase: string;
    readonly cycle?: number;
    readonly max_cycles?: number;
    readonly queue_depth: Readonly<Record<string, number>>;
  }>;
  gates(projectId?: string): Promise<readonly VibeyGate[]>;
}

export interface ProjectFollowerInterface {
  /** One look at a project. */
  snapshot(projectId: string): Promise<ProjectSnapshot>;
  /** What changed between two looks (`undefined` before the first). Pure. */
  diff(before: ProjectSnapshot | undefined, after: ProjectSnapshot): readonly ProjectEvent[];
  /** An event as a sentence a person can act on; a gate is described by the driver, not here. */
  describe(event: ProjectEvent): string;
  /** Watch a project, telling `onEvent` what changes, until it needs a person, is finished, `maxMs` runs out or `cancelled` says so. */
  follow(projectId: string, options: FollowOptions, cancelled: () => boolean): Promise<FollowEnd>;
}

export type { TimerInterface };
