// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What is worth telling a person who is not looking at the app: a question, a project finished. */
import type { VibeyGate, VibeyProject } from '@vibey/core';
import type { NotificationClass } from './settings-interface';

/** One look at the hub: the open gates, and each project's phase. */
export interface NotificationSnapshot {
  readonly gates: readonly { readonly id: string; readonly kind: string; readonly projectName: string; readonly prompt: string }[];
  readonly phases: Readonly<Record<string, { readonly name: string; readonly phase: string }>>;
}

/** A notification to show, and where tapping it goes. */
export interface PlannedNotification {
  /** Stable for what it is about, so showing it twice replaces rather than stacks. */
  readonly id: string;
  readonly kind: NotificationClass;
  readonly title: string;
  readonly body: string;
  readonly route: '/gates' | '/';
}

export interface NotificationPlannerInterface {
  snapshot(projects: readonly VibeyProject[], gates: readonly VibeyGate[]): NotificationSnapshot;
  /** What changed between two looks that the person asked to hear about. Nothing before the first look: what was already waiting when the app opened is on its screen. */
  plan(
    before: NotificationSnapshot | undefined,
    after: NotificationSnapshot,
    enabled: Readonly<Record<NotificationClass, boolean>>,
  ): readonly PlannedNotification[];
}
