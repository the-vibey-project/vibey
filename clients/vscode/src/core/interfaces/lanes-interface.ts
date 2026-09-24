// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Every lane on this computer, whoever started it, read from the loops' own run stores. */
import type { RunItem } from './run-events-interface';

export type LaneState = 'running' | 'quiet' | 'finished';

export interface Lane {
  /** The engine's run id: the run directory's name. */
  readonly id: string;
  readonly engine: string;
  /** The worktree (or folder) the lane works in. */
  readonly cwd: string;
  readonly eventsPath: string;
  readonly label: string;
  readonly state: LaneState;
  /** completed, failed, or stopped, once the lane has said so. */
  readonly outcome?: string;
  readonly turn: number;
  /** The tool the lane is running now: called and not yet answered. */
  readonly tool?: string;
  readonly startedAt: number;
  readonly lastEventAt: number;
  readonly inputTokens: number;
  readonly outputTokens: number;
}

export interface LaneEngine {
  readonly engineId: string;
  readonly stateDir: string;
  readonly envelope: 'type' | 'event_type+payload';
}

export interface LaneTrackerInterface {
  /** Look for lanes again and read every lane's new events; lanes newest first. */
  refresh(): readonly Lane[];
  lanes(): readonly Lane[];
  /** A lane's items so far, for a live view of it. */
  items(eventsPath: string): readonly RunItem[];
}
