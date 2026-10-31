// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What is worth telling a person who is not looking at the app: a question, a project finished. */
import type { GateAnswer, VibeyGate, VibeyProject } from '@vibey/core';
import type { NotificationClass } from './settings-interface';

/** One look at the hub: the open gates, and each project's phase. */
export interface NotificationSnapshot {
  readonly gates: readonly {
    readonly id: string;
    readonly kind: string;
    readonly projectName: string;
    readonly prompt: string;
    readonly options: readonly string[];
  }[];
  readonly phases: Readonly<Record<string, { readonly name: string; readonly phase: string }>>;
}

/** A button on a notification: the answer a person can give without opening the app. */
export interface NotificationAction {
  /** What comes back when it is pressed: an option the gate offers, or `DEFAULTS_ACTION`. */
  readonly id: string;
  readonly title: string;
}

/** A notification to show, and where tapping it goes. */
export interface PlannedNotification {
  /** Stable for what it is about, so showing it twice replaces rather than stacks. */
  readonly id: string;
  readonly kind: NotificationClass;
  readonly title: string;
  readonly body: string;
  readonly route: '/gates' | '/';
  /** The gate this is about, when it is about one. */
  readonly gateId?: string;
  readonly gateKind?: string;
  /** Answer buttons; empty for a gate that spends, one only the host answers, or one with too many options. */
  readonly actions: readonly NotificationAction[];
}

export interface NotificationPlannerInterface {
  /**
   * The buttons a gate's notification may carry. Never any for a gate that spends (an answer to
   * one is re-checked on the device, in the app: ADR-0068), nor for one only the host answers.
   */
  actionsFor(kind: string, options: readonly string[]): readonly NotificationAction[];
  /** The name of the button set, so one registration serves every gate that offers the same buttons. */
  categoryFor(actions: readonly NotificationAction[]): string;
  /**
   * What pressing a button means for a gate of this kind, or `undefined` when it means nothing:
   * a gate that spends, one only the host answers, or a button the gate does not offer. This is
   * the last check before an answer is sent, whatever the notification said.
   */
  answerFor(kind: string, options: readonly string[], actionId: string): GateAnswer | undefined;
  snapshot(projects: readonly VibeyProject[], gates: readonly VibeyGate[]): NotificationSnapshot;
  /** What changed between two looks that the person asked to hear about. Nothing before the first look: what was already waiting when the app opened is on its screen. */
  plan(
    before: NotificationSnapshot | undefined,
    after: NotificationSnapshot,
    enabled: Readonly<Record<NotificationClass, boolean>>,
  ): readonly PlannedNotification[];
}
