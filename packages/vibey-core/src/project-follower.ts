// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Following a project as it runs, so a conversation can drive it to the end: the follower looks
 * at `vibey status` and `vibey gates` every few seconds, turns what changed into plain events, and
 * hands back the moment a person is needed, the project is finished, the time is up, or the
 * person cancels. It starts and stops nothing; it only reads. Declared by
 * `interfaces/project-follower-interface.ts`.
 */
import type {
  FollowEnd,
  FollowOptions,
  ProjectEvent,
  ProjectFollowerInterface,
  ProjectReaderInterface,
  ProjectSnapshot,
  TimerInterface,
} from './interfaces/project-follower-interface';

export class ProjectFollower implements ProjectFollowerInterface {
  /** What each phase is, said so a person who has never seen the word knows what is happening. */
  static readonly PHASES: Readonly<Record<string, string>> = {
    intake: 'taking in the request',
    design: 'designing: it interviews you and writes the design',
    visual_design: 'settling the visual design',
    build: 'building: it writes the code on its own and stops only for decisions that are yours',
    review: 'reviewing the work',
    deploy_design: 'planning the deployment',
    deploy_execute: 'deploying',
    deploy_review: 'reviewing the deployment',
    deploy: 'deploying',
  };

  static readonly FINISHED: readonly string[] = ['done', 'abandoned'];

  constructor(
    private readonly reader: ProjectReaderInterface,
    private readonly timer: TimerInterface,
  ) {}

  async snapshot(projectId: string): Promise<ProjectSnapshot> {
    const [status, gates] = await Promise.all([this.reader.status(projectId), this.reader.gates(projectId)]);
    return {
      name: status.name,
      phase: status.phase.toLowerCase(),
      ...(status.cycle === undefined ? {} : { cycle: status.cycle }),
      ...(status.max_cycles === undefined ? {} : { maxCycles: status.max_cycles }),
      queue: Object.fromEntries(Object.entries(status.queue_depth).map(([state, count]) => [state.toLowerCase(), count])),
      gates,
    };
  }

  diff(before: ProjectSnapshot | undefined, after: ProjectSnapshot): readonly ProjectEvent[] {
    const events: ProjectEvent[] = [];
    if (before === undefined || before.phase !== after.phase) {
      if (ProjectFollower.FINISHED.includes(after.phase)) {
        events.push({ kind: 'finished', name: after.name, phase: after.phase as 'done' | 'abandoned' });
        return events;
      }
      events.push({
        kind: 'phase',
        name: after.name,
        from: before?.phase,
        to: after.phase,
        ...(after.cycle === undefined ? {} : { cycle: after.cycle }),
        ...(after.maxCycles === undefined ? {} : { maxCycles: after.maxCycles }),
      });
    }
    const known = new Set((before?.gates ?? []).map((gate) => gate.gate_id));
    for (const gate of after.gates) {
      if (!known.has(gate.gate_id)) {
        events.push({ kind: 'gate', gate });
      }
    }
    const failedBefore = before?.queue.failed ?? 0;
    const failedAfter = after.queue.failed ?? 0;
    if (before !== undefined && failedAfter > failedBefore) {
      events.push({ kind: 'failed', name: after.name, count: failedAfter - failedBefore });
    }
    return events;
  }

  describe(event: ProjectEvent): string {
    switch (event.kind) {
      case 'phase': {
        const meaning = ProjectFollower.PHASES[event.to] ?? event.to;
        const cycle = event.cycle === undefined ? '' : event.maxCycles === undefined ? ` (cycle ${event.cycle})` : ` (cycle ${event.cycle} of ${event.maxCycles})`;
        return event.from === undefined ? `"${event.name}" is ${meaning}${cycle}.` : `"${event.name}" moved on: now ${meaning}${cycle}.`;
      }
      case 'gate':
        return `"${event.gate.project_name ?? event.gate.project_id}" needs you (${event.gate.kind}).`;
      case 'failed':
        return `${event.count} ${event.count === 1 ? 'job' : 'jobs'} failed in "${event.name}". It retries on its own; if it runs out of attempts it asks you, and /resume grants more.`;
      case 'stalled':
        return `Work is queued for "${event.name}" but nothing has been running it for ${Math.round(event.seconds)} seconds, so no worker is running. /resume starts one.`;
      case 'working': {
        const parts = [event.running > 0 ? `${event.running} running` : '', event.ready > 0 ? `${event.ready} waiting` : ''].filter((part) => part !== '');
        return `Still working on "${event.name}" (${ProjectFollower.PHASES[event.phase]?.split(':')[0] ?? event.phase}${parts.length === 0 ? '' : `; ${parts.join(', ')}`}).`;
      }
      case 'finished':
        return event.phase === 'done' ? `"${event.name}" is done.` : `"${event.name}" was unwound.`;
    }
  }

  async follow(projectId: string, options: FollowOptions, cancelled: () => boolean): Promise<FollowEnd> {
    const started = this.timer.monotonic();
    let before: ProjectSnapshot | undefined;
    let lastSaid = started;
    let stalledSince: number | undefined;
    let stalledSaid = false;
    for (;;) {
      if (cancelled()) {
        return 'cancelled';
      }
      const after = await this.snapshot(projectId);
      const events = this.diff(before, after);
      before = after;
      const now = this.timer.monotonic();
      for (const event of events) {
        options.onEvent(event);
      }
      if (events.some((event) => event.kind === 'finished')) {
        return 'finished';
      }
      if (events.some((event) => event.kind === 'gate')) {
        return 'needs-you';
      }
      const waiting = (after.queue.ready ?? 0) > 0 && (after.queue.leased ?? 0) === 0;
      if (!waiting) {
        stalledSince = undefined;
        stalledSaid = false;
      } else {
        stalledSince ??= now;
        if (!stalledSaid && now - stalledSince >= options.stallMs) {
          options.onEvent({ kind: 'stalled', name: after.name, seconds: (now - stalledSince) / 1000 });
          stalledSaid = true;
          lastSaid = now;
        }
      }
      if (events.length > 0) {
        lastSaid = now;
      } else if (now - lastSaid >= options.heartbeatMs) {
        options.onEvent({ kind: 'working', name: after.name, phase: after.phase, ready: after.queue.ready ?? 0, running: after.queue.leased ?? 0 });
        lastSaid = now;
      }
      if (now - started >= options.maxMs) {
        return 'timeout';
      }
      await this.timer.sleep(options.pollMs);
    }
  }
}
