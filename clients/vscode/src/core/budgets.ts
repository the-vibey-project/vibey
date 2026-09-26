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
 * (10.g). Declared by `interfaces/budgets-interface.ts`. The rules, the ledger and the guard are
 * `@vibey/core`'s; this store is the part that keeps the file.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { BudgetError, BudgetGuard, BudgetRules, NoCapPath, SpendLedger } from '@vibey/core';
import type { Budget, BudgetStoreInterface, PaidDeclaration } from '@vibey/core';
import type { JsonlJournalInterface } from '@vibey/core';
import type { ClockInterface, IdSourceInterface } from '@vibey/core';

export { BudgetError, BudgetGuard, SpendLedger };

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
    const added: Budget = { id: this.ids.uuid().slice(0, 8), ...BudgetRules.checked(budget) };
    const state = this.read();
    this.write({ ...state, budgets: [...state.budgets, added] });
    this.note('add', null, added);
    return added;
  }

  edit(id: string, change: Partial<Omit<Budget, 'id'>>): Budget {
    const state = this.read();
    const old = BudgetRules.find(state.budgets, id);
    const edited: Budget = { ...BudgetRules.checked({ ...old, ...change }), id };
    this.write({ ...state, budgets: state.budgets.map((budget) => (budget.id === id ? edited : budget)) });
    this.note('edit', old, edited);
    return edited;
  }

  remove(id: string): Budget {
    const state = this.read();
    const old = BudgetRules.find(state.budgets, id);
    this.write({ ...state, budgets: state.budgets.filter((budget) => budget.id !== id) });
    this.note('remove', old, null);
    return old;
  }

  declarePaid(
    cap: { readonly scope: 'day' | 'month'; readonly dollars: number } | { readonly noCap: true; readonly phrase: string },
  ): PaidDeclaration {
    let declaration: PaidDeclaration;
    if ('noCap' in cap) {
      if (!NoCapPath.matches(cap.phrase)) {
        throw new BudgetError(`Declaring no dollar cap needs the phrase typed exactly: ${NoCapPath.PHRASE}`);
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

  /**
   * Ends a no-cap declaration in one action, binding at once (ADR-0063, step 6): paidloop is
   * undeclared again and needs a cap before it runs. False when no no-cap declaration stood.
   */
  endNoCap(): boolean {
    const { paid, ...rest } = this.read();
    if (paid?.no_cap_confirmed !== true) {
      return false;
    }
    this.write(rest);
    this.note('paid.no-cap-ended', paid, null);
    return true;
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
}
