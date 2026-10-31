// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Deciding what to notify, with no notification API in sight: a new question, a spending
 * question (its own class, so it can be silenced apart), a project that finished or was
 * unwound. The glue (`src/ui/notifications.tsx`) shows what this returns through
 * expo-notifications; this is the part held to 100% coverage. Declared by
 * `interfaces/notifications-interface.ts`.
 */
import type { GateAnswer, VibeyGate, VibeyProject } from '@vibey/core';
import type {
  NotificationAction,
  NotificationPlannerInterface,
  NotificationSnapshot,
  PlannedNotification,
} from './interfaces/notifications-interface';
import { Presenters } from './presenters';
import type { NotificationClass } from './interfaces/settings-interface';

export class NotificationPlanner implements NotificationPlannerInterface {
  /** The longest a notification's body runs before it is cut; the whole question is on the Gates screen. */
  static readonly BODY_CHARS = 140;

  /** The id of the design interview's one button, which is not an option the gate lists. */
  static readonly DEFAULTS_ACTION = 'defaults';

  /** A phone shows at most three buttons on a notification; more options are answered in the app. */
  static readonly MAX_ACTIONS = 3;

  snapshot(projects: readonly VibeyProject[], gates: readonly VibeyGate[]): NotificationSnapshot {
    return {
      gates: gates.map((gate) => ({ id: gate.gate_id, kind: gate.kind, projectName: gate.project_name ?? gate.project_id, prompt: gate.prompt, options: gate.options })),
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
          gateId: gate.id,
          gateKind: gate.kind,
          actions: this.actionsFor(gate.kind, gate.options),
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
          actions: [],
        });
      }
    }
    return planned.filter((notification) => enabled[notification.kind]);
  }

  actionsFor(kind: string, options: readonly string[]): readonly NotificationAction[] {
    if (Presenters.spends(kind)) {
      return [];
    }
    const key = Presenters.answerKey(kind);
    if (key === 'interview') {
      return [{ id: NotificationPlanner.DEFAULTS_ACTION, title: 'Accept the suggested answers' }];
    }
    if ((key === 'verdict' || key === 'choice') && options.length >= 1 && options.length <= NotificationPlanner.MAX_ACTIONS) {
      return options.map((option) => ({ id: option, title: option }));
    }
    return [];
  }

  categoryFor(actions: readonly NotificationAction[]): string {
    return `krypton-gate:${actions.map((action) => action.id).join('|')}`;
  }

  answerFor(kind: string, options: readonly string[], actionId: string): GateAnswer | undefined {
    if (!this.actionsFor(kind, options).some((action) => action.id === actionId)) {
      return undefined;
    }
    if (Presenters.answerKey(kind) === 'interview') {
      return { mode: 'defaults' };
    }
    return { mode: Presenters.answerKey(kind) as 'verdict' | 'choice', value: actionId };
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
