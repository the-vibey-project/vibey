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
 * (10.g). Declared by `interfaces/budgets-interface.ts`. The rules, the spend ledger and the guard live
 * here, with no file access; the extension's `BudgetStore` keeps the file.
 */
import type {
  Budget,
  BudgetBreach,
  BudgetCaps,
  BudgetGuardInterface,
  BudgetStoreInterface,
  BudgetUsage,
  SpendEntry,
  SpendLedgerInterface,
  SpendTotals,
} from './interfaces/budgets-interface';
import type { JsonlJournalInterface, JsonlTailInterface } from './interfaces/jsonl-interface';
import type { ClockInterface } from './interfaces/support-interface';

export class BudgetError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BudgetError';
  }
}

/** The rules every budget store applies, whatever keeps the file: lookup by id, and what a valid budget is. */
export class BudgetRules {
  static find(budgets: readonly Budget[], id: string): Budget {
    const found = budgets.find((budget) => budget.id === id);
    if (found === undefined) {
      throw new BudgetError(`There is no budget ${id}.`);
    }
    return found;
  }

  /** Positive numbers only, at least one cap, and a scope and loop the rules know. */
  static checked(budget: Omit<Budget, 'id'>): Omit<Budget, 'id'> {
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

  usage(budget: Budget): BudgetUsage | undefined {
    if (budget.scope === 'run') {
      return undefined;
    }
    const spent = this.spent(budget, '', budget.engine_id ?? '');
    const exhausted = (['dollars', 'turns', 'minutes'] as const).find((cap) => {
      const limit = budget.caps[cap];
      return limit !== undefined && spent[cap] >= limit;
    });
    return { spent, ...(exhausted === undefined ? {} : { exhausted }) };
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
