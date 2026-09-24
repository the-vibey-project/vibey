// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Budgets for the lanes this machine starts itself (contract: budgets.md, scope 2). vibey's
 * projects have their own brake; these lanes are not vibey projects, so the same rule is
 * applied here, never a second one: vibey's `BudgetLedger` says a cap is used up when what
 * was spent reaches it, and an escalation is refused when what was spent plus its projection
 * would pass it.
 *
 * Three files under `<storm home>/.vibey-vscode`, read by the editor and the headless CLI
 * alike: `budgets.json` (the budgets now), `budget-journal.jsonl` (every add, edit, remove
 * and paid declaration, fsynced, never rewritten) and `spend.jsonl` (what each run spent, as
 * its events arrived). Totals are folded from a byte-offset watermark, never a timestamp
 * (10.g). Declared by `interfaces/budgets-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
  Budget,
  BudgetBreach,
  BudgetCaps,
  BudgetGuardInterface,
  BudgetStoreInterface,
  PaidDeclaration,
  SpendEntry,
  SpendLedgerInterface,
  SpendTotals,
} from './interfaces/budgets-interface';
import type { JsonlJournalInterface, JsonlTailInterface } from './interfaces/jsonl-interface';
import type { ClockInterface, IdSourceInterface } from './interfaces/support-interface';

export class BudgetError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BudgetError';
  }
}

export class BudgetStore implements BudgetStoreInterface {
  static readonly FILE = 'budgets.json';

  constructor(
    private readonly directory: string,
    private readonly journal: JsonlJournalInterface,
    private readonly clock: ClockInterface,
    private readonly ids: IdSourceInterface,
    /** Who changes a budget: a label for the record, not an authority. */
    private readonly actor: string,
  ) {}

  list(): readonly Budget[] {
    return this.read().budgets;
  }

  paid(): PaidDeclaration | undefined {
    return this.read().paid;
  }

  add(budget: Omit<Budget, 'id'>): Budget {
    const added: Budget = { id: this.ids.uuid().slice(0, 8), ...BudgetStore.checked(budget) };
    const state = this.read();
    this.write({ ...state, budgets: [...state.budgets, added] });
    this.note('add', null, added);
    return added;
  }

  edit(id: string, change: Partial<Omit<Budget, 'id'>>): Budget {
    const state = this.read();
    const old = BudgetStore.find(state.budgets, id);
    const edited: Budget = { ...BudgetStore.checked({ ...old, ...change }), id };
    this.write({ ...state, budgets: state.budgets.map((budget) => (budget.id === id ? edited : budget)) });
    this.note('edit', old, edited);
    return edited;
  }

  remove(id: string): Budget {
    const state = this.read();
    const old = BudgetStore.find(state.budgets, id);
    this.write({ ...state, budgets: state.budgets.filter((budget) => budget.id !== id) });
    this.note('remove', old, null);
    return old;
  }

  declarePaid(
    cap: { readonly scope: 'day' | 'month'; readonly dollars: number } | { readonly noCap: true; readonly confirmed: boolean },
  ): PaidDeclaration {
    let declaration: PaidDeclaration;
    if ('noCap' in cap) {
      if (!cap.confirmed) {
        throw new BudgetError('Declaring the paid loop with no dollar cap needs a second, explicit confirmation.');
      }
      declaration = { declared_at: this.clock.now().toISOString(), no_cap_confirmed: true };
    } else {
      const budget = this.add({ scope: cap.scope, loop: 'paidloop', caps: { dollars: cap.dollars }, label: `paid ${cap.scope} cap` });
      declaration = { declared_at: this.clock.now().toISOString(), budget_id: budget.id };
    }
    this.write({ ...this.read(), paid: declaration });
    this.note('paid.declared', null, declaration);
    return declaration;
  }

  private note(action: string, old: unknown, next: unknown): void {
    this.journal.append({ at: this.clock.now().toISOString(), actor: this.actor, action, old, new: next });
  }

  private read(): { budgets: readonly Budget[]; paid?: PaidDeclaration } {
    let parsed: unknown;
    try {
      parsed = JSON.parse(fs.readFileSync(path.join(this.directory, BudgetStore.FILE), 'utf8'));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return { budgets: [] };
      }
      throw new BudgetError(`${path.join(this.directory, BudgetStore.FILE)} cannot be read: ${(error as Error).message}`);
    }
    const file = parsed as { budgets?: unknown; paid?: unknown };
    return {
      budgets: Array.isArray(file.budgets) ? (file.budgets as Budget[]) : [],
      ...(typeof file.paid === 'object' && file.paid !== null ? { paid: file.paid as PaidDeclaration } : {}),
    };
  }

  /** Written whole to a temporary name and renamed over, so a crash leaves the old file or the new one. */
  private write(state: { budgets: readonly Budget[]; paid?: PaidDeclaration }): void {
    fs.mkdirSync(this.directory, { recursive: true });
    const target = path.join(this.directory, BudgetStore.FILE);
    const temporary = `${target}.writing`;
    const descriptor = fs.openSync(temporary, 'w');
    try {
      fs.writeSync(descriptor, `${JSON.stringify({ version: 1, ...state }, null, 2)}\n`);
      fs.fsyncSync(descriptor);
    } finally {
      fs.closeSync(descriptor);
    }
    fs.renameSync(temporary, target);
  }

  private static find(budgets: readonly Budget[], id: string): Budget {
    const found = budgets.find((budget) => budget.id === id);
    if (found === undefined) {
      throw new BudgetError(`There is no budget ${id}.`);
    }
    return found;
  }

  /** Positive numbers only, at least one cap, and a scope and loop the rules know. */
  private static checked(budget: Omit<Budget, 'id'>): Omit<Budget, 'id'> {
    if (!['run', 'day', 'month'].includes(budget.scope)) {
      throw new BudgetError(`A budget's scope is run, day or month, not ${String(budget.scope)}.`);
    }
    if (!['sovereignloop', 'paidloop', 'any'].includes(budget.loop)) {
      throw new BudgetError(`A budget's loop is sovereignloop, paidloop or any, not ${String(budget.loop)}.`);
    }
    const caps: Record<string, number> = {};
    for (const key of ['dollars', 'turns', 'minutes'] as const) {
      const value = budget.caps[key];
      if (value === undefined) {
        continue;
      }
      if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0 || (key !== 'dollars' && !Number.isInteger(value))) {
        throw new BudgetError(`${key} must be a positive ${key === 'dollars' ? 'number' : 'whole number'}, not ${String(value)}.`);
      }
      caps[key] = value;
    }
    if (Object.keys(caps).length === 0) {
      throw new BudgetError('A budget needs at least one cap: dollars, turns or minutes.');
    }
    return { ...budget, caps };
  }
}

/** What runs spent, appended as it happens and summed from a byte-offset watermark. */
export class SpendLedger implements SpendLedgerInterface {
  private offset = 0;
  private readonly entries: SpendEntry[] = [];

  constructor(
    private readonly journal: JsonlJournalInterface,
    private readonly tail: JsonlTailInterface,
  ) {}

  record(entry: SpendEntry): void {
    this.journal.append({ ...entry });
  }

  totals(filter: { readonly runId?: string; readonly loop?: string; readonly engineId?: string; readonly since?: Date }): SpendTotals {
    this.catchUp();
    const totals = { dollars: 0, turns: 0, minutes: 0, input_tokens: 0, output_tokens: 0, runs: 0 };
    const runs = new Set<string>();
    for (const entry of this.entries) {
      if (
        (filter.runId !== undefined && entry.run_id !== filter.runId) ||
        (filter.loop !== undefined && filter.loop !== 'any' && entry.loop !== filter.loop) ||
        (filter.engineId !== undefined && entry.engine_id !== filter.engineId) ||
        (filter.since !== undefined && Date.parse(entry.at) < filter.since.getTime())
      ) {
        continue;
      }
      totals.dollars += entry.dollars;
      totals.turns += entry.turns;
      totals.minutes += entry.minutes;
      totals.input_tokens += entry.input_tokens;
      totals.output_tokens += entry.output_tokens;
      runs.add(entry.run_id);
    }
    return { ...totals, runs: runs.size };
  }

  perTurn(engineId: string): { readonly input: number; readonly output: number } | undefined {
    const totals = this.totals({ engineId });
    if (totals.turns === 0) {
      return undefined;
    }
    return { input: totals.input_tokens / totals.turns, output: totals.output_tokens / totals.turns };
  }

  /** Every line written since the last read: the watermark is a byte offset. */
  private catchUp(): void {
    const chunk = this.tail.read(this.journal.file, this.offset);
    if (chunk.restarted) {
      this.entries.length = 0;
    }
    this.offset = chunk.nextOffset;
    for (const record of chunk.records) {
      const entry = record as Partial<SpendEntry>;
      if (typeof entry.run_id === 'string' && typeof entry.at === 'string') {
        this.entries.push({
          run_id: entry.run_id,
          at: entry.at,
          loop: String(entry.loop),
          engine_id: String(entry.engine_id),
          turns: Number(entry.turns) || 0,
          input_tokens: Number(entry.input_tokens) || 0,
          output_tokens: Number(entry.output_tokens) || 0,
          dollars: Number(entry.dollars) || 0,
          minutes: Number(entry.minutes) || 0,
        });
      }
    }
  }
}

/** vibey's BudgetLedger rule, applied to every budget that matches a lane. */
export class BudgetGuard implements BudgetGuardInterface {
  constructor(
    private readonly store: BudgetStoreInterface,
    private readonly spend: SpendLedgerInterface,
    private readonly clock: ClockInterface,
  ) {}

  wouldExceed(context: { readonly loop: string; readonly engineId: string; readonly runId: string; readonly projected: BudgetCaps }): BudgetBreach | undefined {
    for (const budget of this.matching(context.loop, context.engineId)) {
      const spent = this.spent(budget, context.runId, context.engineId);
      for (const cap of ['dollars', 'turns', 'minutes'] as const) {
        const limit = budget.caps[cap];
        const projected = context.projected[cap];
        if (limit !== undefined && projected !== undefined && spent[cap] + projected > limit) {
          return {
            budget,
            cap,
            limit,
            spent: spent[cap],
            projected,
            message: `${BudgetGuard.name(budget)} allows ${BudgetGuard.amount(cap, limit)}; ${BudgetGuard.amount(cap, spent[cap])} is spent and this run could take ${BudgetGuard.amount(cap, projected)} more.`,
          };
        }
      }
    }
    return undefined;
  }

  exhausted(context: { readonly loop: string; readonly engineId: string; readonly runId: string }): BudgetBreach | undefined {
    for (const budget of this.matching(context.loop, context.engineId)) {
      const spent = this.spent(budget, context.runId, context.engineId);
      for (const cap of ['dollars', 'turns', 'minutes'] as const) {
        const limit = budget.caps[cap];
        if (limit !== undefined && spent[cap] >= limit) {
          return {
            budget,
            cap,
            limit,
            spent: spent[cap],
            message: `${BudgetGuard.name(budget)} is used up: ${BudgetGuard.amount(cap, spent[cap])} of ${BudgetGuard.amount(cap, limit)}.`,
          };
        }
      }
    }
    return undefined;
  }

  private matching(loop: string, engineId: string): readonly Budget[] {
    return this.store
      .list()
      .filter((budget) => (budget.loop === 'any' || budget.loop === loop) && (budget.engine_id === undefined || budget.engine_id === engineId));
  }

  private spent(budget: Budget, runId: string, engineId: string): Readonly<Record<keyof BudgetCaps, number>> {
    const now = this.clock.now();
    const since =
      budget.scope === 'day'
        ? new Date(now.getFullYear(), now.getMonth(), now.getDate())
        : budget.scope === 'month'
          ? new Date(now.getFullYear(), now.getMonth(), 1)
          : undefined;
    const totals = this.spend.totals({
      ...(budget.scope === 'run' ? { runId } : {}),
      loop: budget.loop,
      ...(budget.engine_id === undefined ? {} : { engineId }),
      ...(since === undefined ? {} : { since }),
    });
    return { dollars: totals.dollars, turns: totals.turns, minutes: totals.minutes };
  }

  private static name(budget: Budget): string {
    return `The ${budget.scope === 'run' ? 'per-run' : budget.scope === 'day' ? 'daily' : 'monthly'} budget ${budget.label ?? budget.id}`;
  }

  private static amount(cap: keyof BudgetCaps, value: number): string {
    return cap === 'dollars' ? `$${value.toFixed(2)}` : `${Math.round(value * 100) / 100} ${cap}`;
  }
}
