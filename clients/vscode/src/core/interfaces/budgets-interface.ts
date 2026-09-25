// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Budgets for the lanes this machine starts: caps, their history, spend, and the brake. */

export type BudgetScope = 'run' | 'day' | 'month';
export type BudgetLoop = 'sovereignloop' | 'paidloop' | 'any';

export interface BudgetCaps {
  readonly dollars?: number;
  readonly turns?: number;
  readonly minutes?: number;
}

export interface Budget {
  readonly id: string;
  readonly scope: BudgetScope;
  readonly loop: BudgetLoop;
  readonly engine_id?: string;
  readonly caps: BudgetCaps;
  readonly label?: string;
}

export interface PaidDeclaration {
  readonly declared_at: string;
  /** The daily or monthly dollar budget made with the declaration, or none, confirmed twice. */
  readonly budget_id?: string;
  readonly no_cap_confirmed?: boolean;
}

export interface BudgetStoreInterface {
  list(): readonly Budget[];
  add(budget: Omit<Budget, 'id'>): Budget;
  edit(id: string, change: Partial<Omit<Budget, 'id'>>): Budget;
  remove(id: string): Budget;
  paid(): PaidDeclaration | undefined;
  /** Declare the paid loop, with a dollar cap, or with none after a second confirmation. */
  declarePaid(cap: { readonly scope: 'day' | 'month'; readonly dollars: number } | { readonly noCap: true; readonly phrase: string }): PaidDeclaration;
}

export interface SpendEntry {
  readonly run_id: string;
  readonly at: string;
  readonly loop: string;
  readonly engine_id: string;
  readonly turns: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly dollars: number;
  readonly minutes: number;
}

export interface SpendTotals {
  readonly dollars: number;
  readonly turns: number;
  readonly minutes: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly runs: number;
}

export interface SpendLedgerInterface {
  record(entry: SpendEntry): void;
  /** Sums of every entry matching, read from a byte-offset watermark. */
  totals(filter: { readonly runId?: string; readonly loop?: string; readonly engineId?: string; readonly since?: Date }): SpendTotals;
  /** Mean tokens per turn this machine measured for an engine, when it measured any. */
  /** Measured dollars per hour of run time; null when nothing has been measured. */
  perHour(filter: { readonly loop?: string; readonly engineId?: string }): number | null;
  perTurn(engineId: string): { readonly input: number; readonly output: number } | undefined;
}

export interface BudgetBreach {
  readonly budget: Budget;
  /** Which cap: dollars, turns or minutes. */
  readonly cap: keyof BudgetCaps;
  readonly limit: number;
  readonly spent: number;
  readonly projected?: number;
  readonly message: string;
}

/** What a day's or a month's budget has spent so far, and the cap it has used up, if any. */
export interface BudgetUsage {
  readonly spent: Readonly<Record<keyof BudgetCaps, number>>;
  readonly exhausted?: keyof BudgetCaps;
}

export interface BudgetGuardInterface {
  /** Before a run or an escalation: the first budget its projection would exceed. */
  wouldExceed(context: {
    readonly loop: string;
    readonly engineId: string;
    readonly runId: string;
    readonly projected: BudgetCaps;
  }): BudgetBreach | undefined;
  /** While it runs: the first matching budget it has used up. */
  exhausted(context: { readonly loop: string; readonly engineId: string; readonly runId: string }): BudgetBreach | undefined;
  /** A day or month budget's spend so far, for a view; a per-run budget has no running total. */
  usage(budget: Budget): BudgetUsage | undefined;
}
