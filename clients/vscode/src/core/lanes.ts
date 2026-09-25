// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Every lane running on this computer, found where the loops write them: `<state_dir>/runs/
 * <run id>/events.jsonl` in each worktree under the storm home, in the storm home itself,
 * and in the open folders. Lanes the editor started are among them, and so are a storm's
 * and a terminal's.
 *
 * Each lane is read by byte offset (sub-doctrine 10.g) and folded into what a person wants
 * at a glance: running, quiet or finished, its turn, the tool it is running, its tokens and
 * how long it has run. A lane with no event for a while is quiet; nothing here ever stops
 * one. The local runner's final snapshot (gptossloop's or qwenloop's) says how a lane ended
 * when its events do not. Declared by `interfaces/lanes-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import type { JsonlTailInterface } from './interfaces/jsonl-interface';
import type { Lane, LaneEngine, LaneTrackerInterface } from './interfaces/lanes-interface';
import type { RunItem } from './interfaces/run-events-interface';
import { RunTranscript } from './run-events';

interface Followed {
  readonly engine: LaneEngine;
  readonly cwd: string;
  readonly id: string;
  readonly transcript: RunTranscript;
  offset: number;
  startedAt: number;
  lastEventAt: number;
  tool?: string;
  outcome?: string;
}

export class LaneTracker implements LaneTrackerInterface {
  private readonly followed = new Map<string, Followed>();
  private current: readonly Lane[] = [];

  constructor(
    private readonly engines: readonly LaneEngine[],
    /** Directories to look in: each is searched, and so is every directory directly inside it. */
    private readonly roots: () => readonly string[],
    private readonly tail: JsonlTailInterface,
    private readonly now: () => number,
    /** Silence longer than this makes a running lane quiet. */
    private readonly quietMs: number,
    /** A lane whose last event is older than this is no longer listed. */
    private readonly recentMs: number,
  ) {}

  lanes(): readonly Lane[] {
    return this.current;
  }

  items(eventsPath: string): readonly RunItem[] {
    return this.followed.get(eventsPath)?.transcript.items() ?? [];
  }

  refresh(): readonly Lane[] {
    for (const [eventsPath, engine, cwd, id] of this.discover()) {
      if (!this.followed.has(eventsPath)) {
        this.followed.set(eventsPath, {
          engine,
          cwd,
          id,
          transcript: new RunTranscript(),
          offset: 0,
          startedAt: LaneTracker.born(fs.statSync(eventsPath)),
          lastEventAt: 0,
        });
      }
    }
    const now = this.now();
    const lanes: Lane[] = [];
    for (const [eventsPath, lane] of this.followed) {
      let modified: number;
      try {
        modified = fs.statSync(eventsPath).mtimeMs;
      } catch {
        this.followed.delete(eventsPath);
        continue;
      }
      lane.lastEventAt = modified;
      this.read(eventsPath, lane);
      if (now - lane.lastEventAt > this.recentMs) {
        continue;
      }
      const finished = lane.outcome !== undefined;
      lanes.push({
        id: lane.id,
        engine: lane.engine.engineId,
        cwd: lane.cwd,
        eventsPath,
        label: `${path.basename(lane.cwd)} · ${lane.engine.engineId}`,
        state: finished ? 'finished' : now - lane.lastEventAt > this.quietMs ? 'quiet' : 'running',
        ...(lane.outcome === undefined ? {} : { outcome: lane.outcome }),
        turn: lane.transcript.turns,
        ...(lane.tool === undefined || finished ? {} : { tool: lane.tool }),
        startedAt: lane.startedAt,
        lastEventAt: lane.lastEventAt,
        inputTokens: lane.transcript.inputTokens,
        outputTokens: lane.transcript.outputTokens,
      });
    }
    this.current = lanes.sort((left, right) => right.startedAt - left.startedAt);
    return this.current;
  }

  private read(eventsPath: string, lane: Followed): void {
    const chunk = this.tail.read(eventsPath, lane.offset);
    lane.offset = chunk.nextOffset;
    for (const event of chunk.records) {
      for (const patch of lane.transcript.accept(event, lane.engine.envelope)) {
        if (patch.op === 'add' && patch.item.kind === 'tool-call') {
          lane.tool = patch.item.name;
        } else if (patch.op === 'add' && patch.item.kind === 'tool-result') {
          lane.tool = undefined;
        }
      }
    }
    if (lane.transcript.completed) {
      lane.outcome = 'completed';
    } else if (lane.transcript.failure !== undefined) {
      lane.outcome = 'failed';
    }
    lane.outcome ??= LaneTracker.snapshot(path.dirname(eventsPath));
  }

  /** Every events file under the roots, with its engine, worktree and run id. */
  private discover(): [string, LaneEngine, string, string][] {
    const found: [string, LaneEngine, string, string][] = [];
    const seen = new Set<string>();
    for (const root of this.roots()) {
      for (const cwd of [root, ...LaneTracker.children(root)]) {
        for (const engine of this.engines) {
          const runs = path.join(cwd, engine.stateDir, 'runs');
          for (const id of LaneTracker.children(runs).map((directory) => path.basename(directory))) {
            const eventsPath = path.join(runs, id, 'events.jsonl');
            if (!seen.has(eventsPath) && fs.existsSync(eventsPath)) {
              seen.add(eventsPath);
              found.push([eventsPath, engine, cwd, id]);
            }
          }
        }
      }
    }
    return found;
  }

  /** The directories directly inside `directory`; none when it cannot be read. */
  private static children(directory: string): string[] {
    try {
      return fs
        .readdirSync(directory, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.'))
        .map((entry) => path.join(directory, entry.name));
    } catch {
      return [];
    }
  }

  /** The local runner writes its last snapshot when a run ends; its status says how. */
  private static snapshot(runDirectory: string): string | undefined {
    try {
      const snapshot: unknown = JSON.parse(fs.readFileSync(path.join(runDirectory, 'snapshots', 'latest.json'), 'utf8'));
      const status = (snapshot as { status?: unknown }).status;
      return status === 'completed' || status === 'failed'
        ? status
        : status === 'winding_down'
          ? 'stopped'
          : undefined;
    } catch {
      return undefined;
    }
  }

  /** When the events file was made, the lane's start: its birth time where the filesystem keeps one. */
  static born(stat: { readonly birthtimeMs: number; readonly ctimeMs: number }): number {
    return stat.birthtimeMs > 0 ? stat.birthtimeMs : stat.ctimeMs;
  }
}
