// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What each screen shows. Pure, so the whole of it is tested. Declared by `interfaces/presenters-interface.ts`. */
import type { VibeyBudget, VibeyGate, VibeyProject } from '@vibey/core';
import type { HubDoctor, HubLane } from './interfaces/hub-client-interface';
import type {
  BudgetRow,
  DoctorRow,
  GateCard,
  HomeSummary,
  LaneRow,
  PresentersInterface,
  StatusRole,
} from './interfaces/presenters-interface';

export class Presenters implements PresentersInterface {
  /**
   * How each gate kind is answered, mirroring `ANSWER_RULES` in src/vibey/cli/gate_answers.py:
   * `{"verdict": …}` or `{"choice": …}` from a button; every other kind (the interview's
   * defaults, grants of money, attempts or rounds, free-form answers) is answered on the host.
   */
  static readonly ANSWER_KEYS: Readonly<Record<string, 'verdict' | 'choice'>> = {
    approval: 'verdict',
    deploy_demo_review: 'verdict',
    choice: 'choice',
    deploy_interview: 'choice',
    deploy_failure_triage: 'choice',
    deploy_acceptance: 'choice',
    bus_dead_lettered: 'choice',
  };

  static answerKey(kind: string): 'verdict' | 'choice' | 'host' {
    return Presenters.ANSWER_KEYS[kind] ?? 'host';
  }

  /** Gates that spend (hub-api.md, "Who may do what"): answering them needs `spend`. */
  static spends(kind: string): boolean {
    return kind === 'budget_exhausted' || kind.startsWith('deploy_');
  }

  /** `review_collect` → "Review collect". */
  static title(kind: string): string {
    const words = kind.replace(/[_-]+/g, ' ').trim();
    return words === '' ? 'Gate' : words.charAt(0).toUpperCase() + words.slice(1);
  }

  home(projects: readonly VibeyProject[]): HomeSummary {
    const cards = projects.map((project) => {
      const openGates = project.open_gates ?? 0;
      return {
        id: project.project_id,
        name: project.name,
        phase: project.phase,
        cycle:
          project.cycle === undefined
            ? ''
            : project.max_cycles === undefined
              ? `Cycle ${project.cycle}`
              : `Cycle ${project.cycle} of ${project.max_cycles}`,
        openGates,
        role: Presenters.phaseRole(project.phase, openGates),
      };
    });
    const needsYou = cards.reduce((sum, card) => sum + card.openGates, 0);
    const headline =
      needsYou === 0 ? 'Nothing needs you' : needsYou === 1 ? '1 gate needs you' : `${needsYou} gates need you`;
    return { headline, needsYou, cards };
  }

  gates(gates: readonly VibeyGate[], nowMs: number): readonly GateCard[] {
    return gates.map((gate) => ({
      id: gate.gate_id,
      projectId: gate.project_id,
      title: gate.project_name === undefined ? Presenters.title(gate.kind) : `${Presenters.title(gate.kind)} · ${gate.project_name}`,
      prompt: gate.prompt,
      options: gate.options,
      spends: Presenters.spends(gate.kind),
      answerKey: Presenters.answerKey(gate.kind),
      due: gate.timeout_at === null ? 'No deadline' : this.due(Date.parse(gate.timeout_at), nowMs),
    }));
  }

  lanes(lanes: readonly HubLane[], nowMs: number): readonly LaneRow[] {
    return lanes.map((lane) => ({
      id: lane.id,
      label: lane.label,
      state: lane.state,
      role: Presenters.laneRole(lane),
      written: `${this.bytes(lane.offset)} written`,
      when: this.ago(lane.last_event_at * 1000, nowMs),
    }));
  }

  budgets(budgets: readonly VibeyBudget[]): readonly BudgetRow[] {
    return budgets.map((budget) => {
      const cap = budget.caps.max_cycle_dollars;
      const turnCap = budget.caps.max_cycle_turns;
      const fraction = cap === null || cap <= 0 ? null : Math.min(1, budget.spend.dollars / cap);
      const role: StatusRole = budget.exhausted
        ? 'danger'
        : fraction !== null && fraction >= 0.8
          ? 'warning'
          : cap === null
            ? 'ultra'
            : 'success';
      return {
        projectId: budget.project_id,
        name: budget.name,
        dollars: `$${budget.spend.dollars.toFixed(2)} of ${cap === null ? 'no cap' : `$${cap.toFixed(2)}`}`,
        turns: `${budget.spend.turns} turns of ${turnCap === null ? 'no cap' : String(turnCap)}`,
        fraction,
        role,
      };
    });
  }

  doctor(doctor: HubDoctor): readonly DoctorRow[] {
    return doctor.checks.map((check) => ({
      name: check.name,
      detail: check.detail,
      role: check.mark === 'PASS' ? 'success' : check.mark === 'WARN' ? 'warning' : 'danger',
    }));
  }

  bytes(count: number): string {
    if (count < 1024) {
      return `${count} B`;
    }
    const units = ['KB', 'MB', 'GB'];
    let value = count / 1024;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return `${value.toFixed(1)} ${units[unit]}`;
  }

  ago(thenMs: number, nowMs: number): string {
    const seconds = Math.max(0, Math.round((nowMs - thenMs) / 1000));
    if (seconds < 45) {
      return 'just now';
    }
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) {
      return `${minutes} min ago`;
    }
    const hours = Math.round(minutes / 60);
    return hours < 24 ? `${hours} h ago` : `${Math.round(hours / 24)} d ago`;
  }

  private due(atMs: number, nowMs: number): string {
    if (Number.isNaN(atMs)) {
      return 'No deadline';
    }
    const minutes = Math.round((atMs - nowMs) / 60_000);
    if (minutes <= 0) {
      return 'Due now';
    }
    return minutes < 60 ? `Due in ${minutes} min` : `Due in ${Math.round(minutes / 60)} h`;
  }

  private static phaseRole(phase: string, openGates: number): StatusRole {
    if (openGates > 0) {
      return 'warning';
    }
    const upper = phase.toUpperCase();
    if (upper.startsWith('DONE')) {
      return 'success';
    }
    return upper === 'FAILED' || upper === 'ABANDONED' ? 'danger' : 'info';
  }

  private static laneRole(lane: HubLane): StatusRole {
    if (lane.state === 'running') {
      return 'info';
    }
    if (lane.state === 'quiet') {
      return 'warning';
    }
    if (lane.state === 'finished') {
      return lane.outcome === null || /^(ok|success|succeeded|done|pass)/i.test(lane.outcome) ? 'success' : 'danger';
    }
    return 'neutral';
  }
}
