// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The vibey conductor, through its own command line: projects, gates, status, answers, the queue. */

/** One line of `vibey projects --json`. */
export interface VibeyProject {
  readonly project_id: string;
  readonly name: string;
  readonly phase: string;
  readonly cycle?: number;
  readonly max_cycles?: number;
  readonly repo_path?: string;
  readonly created_at?: string;
  readonly open_gates?: number;
}

/** `vibey new --json`: the project a person just started, and what vibey queued first. */
export interface VibeyNewProject {
  readonly project_id: string;
  readonly name: string;
  /** vibey's own line, e.g. `design job <id>`: the interview is queued, not yet run. */
  readonly outcome: string;
}

/** What starting a project asks for: the folder it works in, and what the person wants built. */
export interface VibeyNewProjectOptions {
  readonly repo: string;
  readonly intake?: string;
}

/** `vibey abandon --json`, with the two lists reduced to what a confirmation shows: counts. */
export interface VibeyAbandonReport {
  readonly project_id: string;
  readonly name: string;
  readonly from: string;
  readonly to: string;
  readonly dry_run: boolean;
  readonly already_abandoned: boolean;
  readonly written: boolean;
  readonly cancelled_jobs: number;
  readonly withdrawn_gates: number;
}

/** One entry of `vibey gates --json`'s `gates`. */
export interface VibeyGate {
  readonly gate_id: string;
  readonly project_id: string;
  readonly project_name?: string;
  readonly job_id: string | null;
  readonly kind: string;
  readonly prompt: string;
  readonly options: readonly string[];
  readonly default_answer: string | null;
  readonly raised_at?: string;
  readonly timeout_at: string | null;
  /** The command that answers it, as vibey suggests it: `vibey answer <id> --verdict accept`. */
  readonly answer_with?: string;
}

export interface VibeyCircuit {
  readonly engine_id: string;
  readonly installed?: boolean;
  readonly version?: string | null;
  readonly circuit?: string;
  readonly consecutive_fail?: number;
  readonly cost_usd_cycle?: number;
}

/** `vibey status --json`. */
export interface VibeyStatus {
  readonly project_id: string;
  readonly name: string;
  readonly phase: string;
  readonly cycle?: number;
  readonly max_cycles?: number;
  readonly repo_path?: string;
  readonly queue_depth: Readonly<Record<string, number>>;
  readonly circuits: readonly VibeyCircuit[];
  readonly active_worktrees: readonly string[];
}

/** One project of `vibey budget --all --json` (contract: budgets.md, scope 1). */
export interface VibeyBudget {
  readonly project_id: string;
  readonly name: string;
  readonly cycle?: number;
  readonly caps: { readonly max_cycle_dollars: number | null; readonly max_cycle_turns: number | null };
  readonly spend: { readonly dollars: number; readonly turns: number };
  readonly exhausted: boolean;
  readonly history: readonly { readonly at: string; readonly by: string; readonly field: string; readonly old: unknown; readonly new: unknown }[];
}

export type AnswerMode = 'verdict' | 'choice' | 'interview' | 'raw';

export type GateAnswer =
  | { readonly mode: 'verdict'; readonly value: string }
  | { readonly mode: 'choice'; readonly value: string }
  | { readonly mode: 'defaults' }
  | { readonly mode: 'pairs'; readonly pairs: Readonly<Record<string, string>>; readonly defaults: boolean }
  | { readonly mode: 'raw'; readonly json: string };

export interface AnswerChoice {
  readonly label: string;
  readonly description?: string;
  /** Undefined: this choice asks for more input (pairs, or raw JSON). */
  readonly answer?: GateAnswer;
  readonly needs?: 'pairs' | 'raw';
}

export interface GateAnswerPlannerInterface {
  mode(gate: VibeyGate): AnswerMode;
  choices(gate: VibeyGate): readonly AnswerChoice[];
  /** `q1=yes q2=no` into pairs; an error message when it is not that shape. */
  parsePairs(text: string): Readonly<Record<string, string>> | string;
  /** An error message when `text` is not a JSON object. */
  checkRaw(text: string): string | undefined;
}

/** How a `VibeyCli` runs vibey, past the program, its environment and its timeout. */
export interface VibeyCliOptions {
  /** Send every call to the repository's GitHub-hosted runners: `vibey --workflows …` (ADR-0085). */
  readonly workflows?: boolean;
  /** The folder vibey runs in; `vibey -w` sends to that folder's repository. Undefined: wherever this process is. */
  readonly cwd?: () => string | undefined;
}

export interface VibeyCliInterface {
  version(): Promise<string>;
  projects(): Promise<readonly VibeyProject[]>;
  gates(projectId?: string): Promise<readonly VibeyGate[]>;
  status(projectId?: string): Promise<VibeyStatus>;
  answer(gateId: string, answer: GateAnswer): Promise<string>;
  bump(jobId: string, projectId?: string): Promise<string>;
  /** `vibey new --json`: create a project in `options.repo` and queue its design interview. */
  createProject(name: string, options: VibeyNewProjectOptions): Promise<VibeyNewProject>;
  /** `vibey retry --keep-workers --start-worker`: start, or start again, the project's worker. */
  startWork(projectId: string): Promise<string>;
  /** `vibey recover --project --stop-workers`: stop this project's own workers and free its jobs; a worker that serves every project is left running and named, and the call then fails rather than reset a lease it may hold. Reversible. */
  pauseWork(projectId: string): Promise<string>;
  /** `vibey abandon --json`: unwind a project for good; `dryRun` lists what it would cancel and writes nothing. */
  abandonProject(projectId: string, reason: string, options?: { readonly dryRun?: boolean }): Promise<VibeyAbandonReport>;
  /** `vibey loops --json`, unparsed: the catalogue parser reads it. */
  loops(): Promise<unknown>;
  budgets(): Promise<readonly VibeyBudget[]>;
  setBudget(projectId: string | undefined, caps: { readonly dollars?: number; readonly turns?: number }): Promise<string>;
  clearBudget(projectId: string | undefined, which: 'dollars' | 'turns' | 'all'): Promise<string>;
  /** `vibey cost`'s text: what an older vibey offers in place of `vibey budget`. */
  cost(projectId?: string): Promise<string>;
}
