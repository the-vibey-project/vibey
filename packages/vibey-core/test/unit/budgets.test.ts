// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The budget rules, the spend ledger and the guard, with no file: the journal and the tail are
// in memory here, and the extension's suite exercises them again over real files.
import { describe, expect, it } from 'vitest';
import { BudgetError, BudgetGuard, BudgetRules, SpendLedger } from '../../src/budgets';
import type { Budget, BudgetStoreInterface, PaidDeclaration } from '../../src/interfaces/budgets-interface';
import type { JournalContents, JsonlJournalInterface, JsonlTailInterface, TailChunk } from '../../src/interfaces/jsonl-interface';
import { FakeClock } from './helpers';

/** Lines in memory; the "offset" is a line count, which is all the ledger needs of it. */
class MemoryJournal implements JsonlJournalInterface, JsonlTailInterface {
  readonly file = 'spend.jsonl';
  lines: unknown[] = [];

  append(record: Readonly<Record<string, unknown>>): void {
    this.lines.push({ ...record });
  }

  readAll(): JournalContents {
    return { records: this.lines as Record<string, unknown>[], malformed: 0 };
  }

  read(_file: string, offset: number): TailChunk {
    const restarted = this.lines.length < offset;
    const start = restarted ? 0 : offset;
    return { records: this.lines.slice(start), malformed: 0, nextOffset: this.lines.length, missing: false, restarted };
  }
}

class MemoryStore implements BudgetStoreInterface {
  private budgets: Budget[] = [];
  private next = 0;

  list(): readonly Budget[] {
    return this.budgets;
  }

  add(budget: Omit<Budget, 'id'>): Budget {
    this.next += 1;
    const added: Budget = { id: `b${this.next}`, ...BudgetRules.checked(budget) };
    this.budgets.push(added);
    return added;
  }

  edit(id: string, change: Partial<Omit<Budget, 'id'>>): Budget {
    const edited: Budget = { ...BudgetRules.checked({ ...BudgetRules.find(this.budgets, id), ...change }), id };
    this.budgets = this.budgets.map((budget) => (budget.id === id ? edited : budget));
    return edited;
  }

  remove(id: string): Budget {
    const old = BudgetRules.find(this.budgets, id);
    this.budgets = this.budgets.filter((budget) => budget.id !== id);
    return old;
  }

  paid(): PaidDeclaration | undefined {
    return undefined;
  }

  declarePaid(): PaidDeclaration {
    return { declared_at: '2026-09-24T12:00:00.000Z', no_cap_confirmed: true };
  }
}

const entry = (overrides: Record<string, unknown> = {}) =>
  ({
    run_id: 'r1',
    at: '2026-09-24T12:00:00.000Z',
    loop: 'paidloop',
    engine_id: 'claudeloop',
    turns: 1,
    input_tokens: 1000,
    output_tokens: 100,
    dollars: 1.5,
    minutes: 2,
    ...overrides,
  }) as Parameters<SpendLedger['record']>[0];

describe('BudgetRules', () => {
  it('accepts positive caps, keeps only the caps given, and finds a budget by id', () => {
    expect(BudgetRules.checked({ scope: 'run', loop: 'any', caps: { dollars: 0.25, minutes: 30 } }).caps).toEqual({ dollars: 0.25, minutes: 30 });
    const budgets: Budget[] = [{ id: 'a', scope: 'day', loop: 'any', caps: { turns: 3 } }];
    expect(BudgetRules.find(budgets, 'a')).toBe(budgets[0]);
  });

  it('refuses a budget that is not one, and an id that does not exist', () => {
    expect(() => BudgetRules.checked({ scope: 'week' as 'day', loop: 'any', caps: { dollars: 1 } })).toThrow("A budget's scope is run, day or month, not week.");
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'cheap' as 'any', caps: { dollars: 1 } })).toThrow(
      "A budget's loop is sovereignloop, paidloop or any, not cheap.",
    );
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'any', caps: {} })).toThrow('A budget needs at least one cap: dollars, turns or minutes.');
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'any', caps: { dollars: -1 } })).toThrow('dollars must be a positive number, not -1.');
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'any', caps: { dollars: Number.POSITIVE_INFINITY } })).toThrow('dollars must be a positive number');
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'any', caps: { turns: 1.5 } })).toThrow('turns must be a positive whole number, not 1.5.');
    expect(() => BudgetRules.checked({ scope: 'day', loop: 'any', caps: { minutes: 'x' as unknown as number } })).toThrow(BudgetError);
    expect(() => BudgetRules.find([], 'nope')).toThrow('There is no budget nope.');
    expect(new BudgetError('x').name).toBe('BudgetError');
  });
});

describe('SpendLedger', () => {
  it('sums spend from its watermark, and knows tokens per turn', () => {
    const journal = new MemoryJournal();
    const spend = new SpendLedger(journal, journal);
    expect(spend.perTurn('claudeloop')).toBeUndefined();
    spend.record(entry());
    spend.record(entry({ run_id: 'r2', engine_id: 'codexloop', dollars: 0.5 }));
    expect(spend.totals({})).toEqual({ dollars: 2, turns: 2, minutes: 4, input_tokens: 2000, output_tokens: 200, runs: 2 });
    journal.lines.push({ no: 'run' }, { run_id: 'r5' });
    spend.record(entry({ turns: 'x', input_tokens: null, output_tokens: 0, dollars: 'free', minutes: undefined, at: '2026-09-25T00:00:00.000Z' }));
    expect(spend.totals({ runId: 'r1' })).toEqual({ dollars: 1.5, turns: 1, minutes: 2, input_tokens: 1000, output_tokens: 100, runs: 1 });
    expect(spend.totals({ engineId: 'codexloop' }).dollars).toBe(0.5);
    expect(spend.totals({ loop: 'sovereignloop' }).runs).toBe(0);
    expect(spend.totals({ loop: 'any' }).runs).toBe(2);
    expect(spend.totals({ loop: 'paidloop', since: new Date('2026-09-24T18:00:00Z') })).toMatchObject({ runs: 1, turns: 0, dollars: 0 });
    expect(spend.perTurn('claudeloop')).toEqual({ input: 1000, output: 100 });
  });

  it('starts over when the record is replaced by a shorter one', () => {
    const journal = new MemoryJournal();
    const spend = new SpendLedger(journal, journal);
    spend.record(entry({ dollars: 9 }));
    spend.record(entry({ run_id: 'r2', dollars: 9 }));
    expect(spend.totals({}).dollars).toBe(18);
    journal.lines = [entry({ dollars: 1 })];
    expect(spend.totals({})).toMatchObject({ dollars: 1, runs: 1 });
  });
});

describe('BudgetGuard', () => {
  it("applies vibey's BudgetLedger rule: exhausted at the cap, refused when the projection passes it", () => {
    const store = new MemoryStore();
    const journal = new MemoryJournal();
    const spend = new SpendLedger(journal, journal);
    const guard = new BudgetGuard(store, spend, new FakeClock());
    const run = store.add({ scope: 'run', loop: 'any', caps: { turns: 3 } });
    const day = store.add({ scope: 'day', loop: 'paidloop', engine_id: 'claudeloop', caps: { dollars: 2 }, label: 'claude day' });
    const month = store.add({ scope: 'month', loop: 'sovereignloop', caps: { minutes: 1000 } });
    const context = { loop: 'paidloop', engineId: 'claudeloop', runId: 'r1' };
    expect(guard.usage(month)).toEqual({ spent: { dollars: 0, turns: 0, minutes: 0 } });
    expect(guard.exhausted(context)).toBeUndefined();
    expect(guard.wouldExceed({ ...context, projected: { dollars: 1.9 } })).toBeUndefined();
    expect(guard.wouldExceed({ ...context, projected: { dollars: 2.5, turns: 1 } })).toEqual({
      budget: day,
      cap: 'dollars',
      limit: 2,
      spent: 0,
      projected: 2.5,
      message: 'The daily budget claude day allows $2.00; $0.00 is spent and this run could take $2.50 more.',
    });
    spend.record(entry({ turns: 3 }));
    expect(guard.exhausted(context)).toEqual({
      budget: run,
      cap: 'turns',
      limit: 3,
      spent: 3,
      message: 'The per-run budget b1 is used up: 3 turns of 3 turns.',
    });
    expect(guard.exhausted({ ...context, engineId: 'cursorloop', runId: 'r9' })).toBeUndefined();
    expect(guard.usage(run)).toBeUndefined();
    expect(guard.usage(day)).toEqual({ spent: { dollars: 1.5, turns: 3, minutes: 2 } });
    spend.record(entry({ turns: 0, dollars: 1 }));
    expect(guard.usage(day)).toEqual({ spent: { dollars: 2.5, turns: 3, minutes: 4 }, exhausted: 'dollars' });
    expect(guard.wouldExceed({ loop: 'sovereignloop', engineId: 'qwenloop', runId: 'r9', projected: { minutes: 2000 } })?.message).toBe(
      'The monthly budget b3 allows 1000 minutes; 0 minutes is spent and this run could take 2000 minutes more.',
    );
    store.edit(month.id, { caps: { minutes: 1 } });
    expect(store.remove(month.id).caps).toEqual({ minutes: 1 });
    expect(store.paid()).toBeUndefined();
    expect(store.declarePaid().no_cap_confirmed).toBe(true);
  });
});
