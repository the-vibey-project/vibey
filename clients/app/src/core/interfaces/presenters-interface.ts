// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What each screen shows, worked out from the hub's documents, with no React in it. */
import type { VibeyBudget, VibeyGate, VibeyProject } from '@vibey/core';
import type { HubDoctor, HubLane } from './hub-client-interface';

/** Which status colour of the design tokens a row takes (`color.status.*`). */
export type StatusRole = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'ultra';

export interface ProjectCard {
  readonly id: string;
  readonly name: string;
  readonly phase: string;
  /** "Cycle 2 of 5", or empty. */
  readonly cycle: string;
  readonly openGates: number;
  readonly role: StatusRole;
}

export interface HomeSummary {
  /** One line on top: "2 gates need you" or "Nothing needs you". */
  readonly headline: string;
  readonly needsYou: number;
  readonly cards: readonly ProjectCard[];
}

export interface GateCard {
  readonly id: string;
  readonly projectId: string;
  readonly title: string;
  readonly prompt: string;
  readonly options: readonly string[];
  /** A gate that spends money: answering it asks for Face ID, Touch ID or the passcode. */
  readonly spends: boolean;
  /** Which key a device answers with, or `host` when only the host can answer it. */
  readonly answerKey: 'verdict' | 'choice' | 'host';
  readonly due: string;
}

export interface LaneRow {
  readonly id: string;
  readonly label: string;
  readonly state: string;
  readonly role: StatusRole;
  /** "12.4 KB written". */
  readonly written: string;
  /** "3 min ago". */
  readonly when: string;
}

export interface BudgetRow {
  readonly projectId: string;
  readonly name: string;
  readonly dollars: string;
  readonly turns: string;
  /** 0 to 1 of the dollar cap, or null when there is none. */
  readonly fraction: number | null;
  readonly role: StatusRole;
}

export interface DoctorRow {
  readonly name: string;
  readonly detail: string;
  readonly role: StatusRole;
}

export interface PresentersInterface {
  home(projects: readonly VibeyProject[]): HomeSummary;
  gates(gates: readonly VibeyGate[], nowMs: number): readonly GateCard[];
  lanes(lanes: readonly HubLane[], nowMs: number): readonly LaneRow[];
  budgets(budgets: readonly VibeyBudget[]): readonly BudgetRow[];
  doctor(doctor: HubDoctor): readonly DoctorRow[];
  bytes(count: number): string;
  ago(thenMs: number, nowMs: number): string;
}
