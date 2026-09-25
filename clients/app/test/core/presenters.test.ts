// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import type { VibeyBudget, VibeyGate } from '@vibey/core';
import { Presenters } from '../../src/core/presenters';

const present = new Presenters();
const NOW = Date.parse('2026-09-25T12:00:00Z');

function gate(overrides: Partial<VibeyGate>): VibeyGate {
  return {
    gate_id: 'g',
    project_id: 'p',
    job_id: null,
    kind: 'review_collect',
    prompt: 'Accept?',
    options: [],
    default_answer: null,
    timeout_at: null,
    ...overrides,
  };
}

function budget(overrides: Partial<VibeyBudget>): VibeyBudget {
  return {
    project_id: 'p',
    name: 'P',
    caps: { max_cycle_dollars: 10, max_cycle_turns: 40 },
    spend: { dollars: 1, turns: 2 },
    exhausted: false,
    history: [],
    ...overrides,
  };
}

describe('Presenters', () => {
  it('sums the gates that need you on Home', () => {
    expect(present.home([]).headline).toBe('Nothing needs you');
    const one = present.home([{ project_id: 'a', name: 'A', phase: 'BUILD', open_gates: 1, cycle: 2 }]);
    expect(one).toMatchObject({ headline: '1 gate needs you', needsYou: 1 });
    expect(one.cards[0]).toMatchObject({ cycle: 'Cycle 2', role: 'warning' });
    const many = present.home([
      { project_id: 'a', name: 'A', phase: 'DESIGN', open_gates: 2, cycle: 1, max_cycles: 3 },
      { project_id: 'b', name: 'B', phase: 'DONE_LOCAL' },
      { project_id: 'c', name: 'C', phase: 'FAILED' },
      { project_id: 'd', name: 'D', phase: 'BUILD' },
    ]);
    expect(many.headline).toBe('2 gates need you');
    expect(many.cards.map((card) => [card.cycle, card.role])).toEqual([
      ['Cycle 1 of 3', 'warning'],
      ['', 'success'],
      ['', 'danger'],
      ['', 'info'],
    ]);
  });

  it('marks gates that spend and says when each is due', () => {
    const cards = present.gates(
      [
        gate({ kind: 'budget_exhausted', project_name: 'Greeter', timeout_at: '2026-09-25T12:30:00Z' }),
        gate({ kind: 'deploy_confirm', timeout_at: '2026-09-25T15:00:00Z' }),
        gate({ kind: '__', timeout_at: '2026-09-25T11:00:00Z' }),
        gate({ timeout_at: 'whenever' }),
        gate({}),
      ],
      NOW,
    );
    expect(cards.map((card) => [card.title, card.spends, card.due])).toEqual([
      ['Budget exhausted · Greeter', true, 'Due in 30 min'],
      ['Deploy confirm', true, 'Due in 3 h'],
      ['Gate', false, 'Due now'],
      ['Review collect', false, 'No deadline'],
      ['Review collect', false, 'No deadline'],
    ]);
  });

  it('shows how far each lane has written and how long ago', () => {
    const rows = present.lanes(
      [
        { id: 'a', engine: 'e', label: 'A', state: 'running', outcome: null, offset: 12_700, last_event_at: NOW / 1000 - 10 },
        { id: 'b', engine: 'e', label: 'B', state: 'quiet', outcome: null, offset: 10, last_event_at: NOW / 1000 - 600 },
        { id: 'c', engine: 'e', label: 'C', state: 'finished', outcome: null, offset: 0, last_event_at: NOW / 1000 - 7200 },
        { id: 'd', engine: 'e', label: 'D', state: 'finished', outcome: 'succeeded', offset: 0, last_event_at: 0 },
        { id: 'e', engine: 'e', label: 'E', state: 'finished', outcome: 'crashed', offset: 0, last_event_at: 0 },
        { id: 'f', engine: 'e', label: 'F', state: 'odd', outcome: null, offset: 0, last_event_at: 0 },
      ],
      NOW,
    );
    expect(rows.map((row) => [row.role, row.written, row.when])).toEqual([
      ['info', '12.4 KB written', 'just now'],
      ['warning', '10 B written', '10 min ago'],
      ['success', '0 B written', '2 h ago'],
      ['success', '0 B written', `${Math.round(NOW / 86_400_000)} d ago`],
      ['danger', '0 B written', `${Math.round(NOW / 86_400_000)} d ago`],
      ['neutral', '0 B written', `${Math.round(NOW / 86_400_000)} d ago`],
    ]);
    expect(present.ago(NOW + 5000, NOW)).toBe('just now');
  });

  it('counts bytes up to gigabytes and no further', () => {
    expect(present.bytes(3 * 1024 * 1024)).toBe('3.0 MB');
    expect(present.bytes(5 * 1024 ** 4)).toBe('5120.0 GB');
  });

  it('shows spend against the caps, and no cap as ULTRA-coloured', () => {
    const rows = present.budgets([
      budget({}),
      budget({ spend: { dollars: 9, turns: 2 } }),
      budget({ exhausted: true }),
      budget({ caps: { max_cycle_dollars: null, max_cycle_turns: null } }),
      budget({ caps: { max_cycle_dollars: 0, max_cycle_turns: 1 }, spend: { dollars: 0, turns: 0 } }),
    ]);
    expect(rows.map((row) => [row.dollars, row.turns, row.fraction, row.role])).toEqual([
      ['$1.00 of $10.00', '2 turns of 40', 0.1, 'success'],
      ['$9.00 of $10.00', '2 turns of 40', 0.9, 'warning'],
      ['$1.00 of $10.00', '2 turns of 40', 0.1, 'danger'],
      ['$1.00 of no cap', '2 turns of no cap', null, 'ultra'],
      ['$0.00 of $0.00', '0 turns of 1', null, 'success'],
    ]);
  });

  it('colours the doctor by mark', () => {
    const rows = present.doctor({
      scope: 'hub',
      checks: [
        { name: 'a', mark: 'PASS', detail: '' },
        { name: 'b', mark: 'WARN', detail: '' },
        { name: 'c', mark: 'FAIL', detail: 'down' },
      ],
    });
    expect(rows.map((row) => row.role)).toEqual(['success', 'warning', 'danger']);
  });

  it('knows which gates spend', () => {
    expect(Presenters.spends('budget_exhausted')).toBe(true);
    expect(Presenters.spends('deploy_design')).toBe(true);
    expect(Presenters.spends('review_collect')).toBe(false);
  });
});
