// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Deciding what to notify, with no notification API in sight: a new question, a spending
 * question (its own class, so it can be silenced apart), a project that finished or was
 * unwound. The glue (`src/ui/notifications.tsx`) shows what this returns through
 * expo-notifications; this is the part held to 100% coverage. Declared by
 * `interfaces/notifications-interface.ts`.
 */
import type { VibeyGate, VibeyProject } from '@vibey/core';
import type {
  NotificationPlannerInterface,
  NotificationSnapshot,
  PlannedNotification,
} from './interfaces/notifications-interface';
import type { NotificationClass } from './interfaces/settings-interface';

export class NotificationPlanner implements NotificationPlannerInterface {
  /** The longest a notification's body runs before it is cut; the whole question is on the Gates screen. */
  static readonly BODY_CHARS = 140;

  snapshot(projects: readonly VibeyProject[], gates: readonly VibeyGate[]): NotificationSnapshot {
    return {
      gates: gates.map((gate) => ({ id: gate.gate_id, kind: gate.kind, projectName: gate.project_name ?? gate.project_id, prompt: gate.prompt })),
      phases: Object.fromEntries(projects.map((project) => [project.project_id, { name: project.name, phase: project.phase.toLowerCase() }])),
    };
  }

  plan(
    before: NotificationSnapshot | undefined,
    after: NotificationSnapshot,
    enabled: Readonly<Record<NotificationClass, boolean>>,
  ): readonly PlannedNotification[] {
    if (before === undefined) {
      return [];
    }
    const planned: PlannedNotification[] = [];
    const known = new Set(before.gates.map((gate) => gate.id));
    for (const gate of after.gates) {
      if (!known.has(gate.id)) {
        planned.push({
          id: `gate-${gate.id}`,
          kind: gate.kind === 'budget_exhausted' ? 'budget' : 'gate',
          title: `${gate.projectName} needs you`,
          body: NotificationPlanner.body(gate.prompt),
          route: '/gates',
        });
      }
    }
    for (const [id, project] of Object.entries(after.phases)) {
      const was = before.phases[id]?.phase;
      if (was !== undefined && was !== project.phase && (project.phase === 'done' || project.phase === 'abandoned')) {
        planned.push({
          id: `finished-${id}`,
          kind: 'finished',
          title: project.phase === 'done' ? `${project.name} is done` : `${project.name} was unwound`,
          body: project.phase === 'done' ? 'Open krypton to see what it built.' : 'It was ended and nothing more will run.',
          route: '/',
        });
      }
    }
    return planned.filter((notification) => enabled[notification.kind]);
  }

  private static body(prompt: string): string {
    // The first line only: everything after the first line break goes.
    const first = prompt.trim().replace(/\n[\s\S]*$/, '').trim();
    if (first === '') {
      return 'Open krypton to answer.';
    }
    return first.length > NotificationPlanner.BODY_CHARS ? `${first.slice(0, NotificationPlanner.BODY_CHARS - 1)}…` : first;
  }
}
