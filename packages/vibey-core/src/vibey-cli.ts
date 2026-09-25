// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The conductor through its own command line, as the issue's first slice asks: no server,
 * just `vibey` (#290). Projects come from `vibey projects --json`, open gates from
 * `vibey gates --json`, a project's queue and engines from `vibey status --json`, and an
 * answer goes through `vibey answer` exactly as a person would type it. The vibey on PATH
 * may be an older release without `projects` and `gates`; that is said plainly, with the
 * release that adds them, and nothing falls back to reading the database. Declared by
 * `interfaces/vibey-cli-interface.ts`.
 */
import type { Environment, ProcessRunnerInterface } from './interfaces/process-runner-interface';
import type {
  AnswerChoice,
  AnswerMode,
  GateAnswer,
  GateAnswerPlannerInterface,
  VibeyCircuit,
  VibeyBudget,
  VibeyCliInterface,
  VibeyGate,
  VibeyProject,
  VibeyStatus,
} from './interfaces/vibey-cli-interface';

export class VibeyCliError extends Error {
  constructor(
    message: string,
    readonly kind: 'missing-command' | 'failed' | 'bad-output',
  ) {
    super(message);
    this.name = 'VibeyCliError';
  }
}

export class VibeyCli implements VibeyCliInterface {
  /** The last release without `projects`, `gates`, `loops` and `budget`; 3.0.0 is the first with them. */
  static readonly COMMANDS_AFTER = '2.1.0';
  static readonly COMMANDS_IN = '3.0.0';
  /** How the extension signs a budget change: a label for vibey's record, not an authority. */
  static readonly ACTOR = 'vibey-vscode';

  constructor(
    private readonly runner: ProcessRunnerInterface,
    private readonly executable: string,
    private readonly environment: Environment,
    private readonly timeoutMs = 60_000,
  ) {}

  async version(): Promise<string> {
    return (await this.must(['--version'])).trim();
  }

  async projects(): Promise<readonly VibeyProject[]> {
    const parsed = VibeyCli.json(await this.must(['projects', '--json'], 'projects'), 'vibey projects --json');
    if (!Array.isArray(parsed)) {
      throw new VibeyCliError('vibey projects --json did not print a list', 'bad-output');
    }
    return parsed.filter(VibeyCli.isProject);
  }

  async gates(projectId?: string): Promise<readonly VibeyGate[]> {
    const args = projectId === undefined ? ['gates', '--json'] : ['gates', projectId, '--json'];
    const parsed = VibeyCli.json(await this.must(args, 'gates'), 'vibey gates --json');
    const gates = VibeyCli.field(parsed, 'gates');
    if (!Array.isArray(gates)) {
      throw new VibeyCliError('vibey gates --json did not print {"gates": [...]}', 'bad-output');
    }
    return gates.filter(VibeyCli.isGate).map((gate) => ({
      ...gate,
      options: Array.isArray(gate.options) ? gate.options.filter((option): option is string => typeof option === 'string') : [],
    }));
  }

  async status(projectId?: string): Promise<VibeyStatus> {
    const args = projectId === undefined ? ['status', '--json'] : ['status', '--json', projectId];
    const parsed = VibeyCli.json(await this.must(args), 'vibey status --json');
    if (!VibeyCli.isRecord(parsed) || typeof parsed.project_id !== 'string' || typeof parsed.phase !== 'string') {
      throw new VibeyCliError('vibey status --json did not print a project', 'bad-output');
    }
    const depth = VibeyCli.isRecord(parsed.queue_depth) ? parsed.queue_depth : {};
    return {
      project_id: parsed.project_id,
      name: typeof parsed.name === 'string' ? parsed.name : parsed.project_id,
      phase: parsed.phase,
      ...(typeof parsed.cycle === 'number' ? { cycle: parsed.cycle } : {}),
      ...(typeof parsed.max_cycles === 'number' ? { max_cycles: parsed.max_cycles } : {}),
      ...(typeof parsed.repo_path === 'string' ? { repo_path: parsed.repo_path } : {}),
      queue_depth: Object.fromEntries(
        Object.entries(depth).filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
      ),
      circuits: Array.isArray(parsed.circuits)
        ? parsed.circuits.filter(
            (circuit): circuit is VibeyCircuit => VibeyCli.isRecord(circuit) && typeof circuit.engine_id === 'string',
          )
        : [],
      active_worktrees: Array.isArray(parsed.active_worktrees)
        ? parsed.active_worktrees.filter((item): item is string => typeof item === 'string')
        : [],
    };
  }

  async answer(gateId: string, answer: GateAnswer): Promise<string> {
    return (await this.must(VibeyCli.answerArgs(gateId, answer))).trim();
  }

  async bump(jobId: string, projectId?: string): Promise<string> {
    const args = ['queue', 'bump', jobId, '--source', 'vscode'];
    if (projectId !== undefined) {
      args.push('--project', projectId);
    }
    return (await this.must(args)).trim();
  }

  async loops(): Promise<unknown> {
    return VibeyCli.json(await this.must(['loops', '--json'], 'loops'), 'vibey loops --json');
  }

  async budgets(): Promise<readonly VibeyBudget[]> {
    const parsed = VibeyCli.json(await this.must(['budget', '--all', '--json'], 'budget'), 'vibey budget --all --json');
    if (!Array.isArray(parsed)) {
      throw new VibeyCliError('vibey budget --all --json did not print a list', 'bad-output');
    }
    return parsed
      .filter((item): item is Record<string, unknown> => VibeyCli.isRecord(item) && typeof item.project_id === 'string')
      .map((item) => {
        const caps = VibeyCli.isRecord(item.caps) ? item.caps : {};
        const spend = VibeyCli.isRecord(item.spend) ? item.spend : {};
        return {
          project_id: item.project_id as string,
          name: typeof item.name === 'string' ? item.name : (item.project_id as string),
          ...(typeof item.cycle === 'number' ? { cycle: item.cycle } : {}),
          caps: {
            max_cycle_dollars: typeof caps.max_cycle_dollars === 'number' ? caps.max_cycle_dollars : null,
            max_cycle_turns: typeof caps.max_cycle_turns === 'number' ? caps.max_cycle_turns : null,
          },
          spend: {
            dollars: typeof spend.dollars === 'number' ? spend.dollars : 0,
            turns: typeof spend.turns === 'number' ? spend.turns : 0,
          },
          exhausted: item.exhausted === true,
          history: Array.isArray(item.history) ? (item.history.filter(VibeyCli.isRecord) as unknown as VibeyBudget['history']) : [],
        };
      });
  }

  async setBudget(projectId: string | undefined, caps: { readonly dollars?: number; readonly turns?: number }): Promise<string> {
    const args = ['budget', 'set', ...(projectId === undefined ? [] : [projectId])];
    if (caps.dollars !== undefined) {
      args.push('--max-cycle-dollars', String(caps.dollars));
    }
    if (caps.turns !== undefined) {
      args.push('--max-cycle-turns', String(caps.turns));
    }
    args.push('--by', VibeyCli.ACTOR);
    return (await this.must(args, 'budget')).trim();
  }

  async clearBudget(projectId: string | undefined, which: 'dollars' | 'turns' | 'all'): Promise<string> {
    return (
      await this.must(['budget', 'clear', ...(projectId === undefined ? [] : [projectId]), `--${which}`, '--by', VibeyCli.ACTOR], 'budget')
    ).trim();
  }

  async cost(projectId?: string): Promise<string> {
    return (await this.must(projectId === undefined ? ['cost'] : ['cost', projectId])).trim();
  }

  /** `vibey answer`'s argv for one answer, in the forms docs/reference/cli.md documents. */
  static answerArgs(gateId: string, answer: GateAnswer): string[] {
    switch (answer.mode) {
      case 'verdict':
        return ['answer', gateId, '--verdict', answer.value];
      case 'choice':
        return ['answer', gateId, '--choice', answer.value];
      case 'defaults':
        return ['answer', gateId, '--defaults'];
      case 'pairs':
        return [
          'answer',
          gateId,
          ...Object.entries(answer.pairs).map(([question, value]) => `${question}=${value}`),
          ...(answer.defaults ? ['--defaults'] : []),
        ];
      case 'raw':
        return ['answer', gateId, '--raw', answer.json];
    }
  }

  private async must(args: readonly string[], command?: string): Promise<string> {
    const result = await this.runner.run(this.executable, args, { env: this.environment, timeoutMs: this.timeoutMs });
    if (result.code === 0) {
      return result.stdout;
    }
    const said = `${result.stderr}\n${result.stdout}`.trim();
    if (command !== undefined && /No such command/i.test(said)) {
      const version = await this.runner.run(this.executable, ['--version'], { env: this.environment, timeoutMs: this.timeoutMs });
      const which = version.code === 0 ? version.stdout.trim() : 'this vibey';
      throw new VibeyCliError(
        `${which} (${this.executable}) has no "vibey ${command}" command. It was added after vibey ${VibeyCli.COMMANDS_AFTER} and ships in vibey ${VibeyCli.COMMANDS_IN}; point the vibey.cliPath setting at a newer vibey.`,
        'missing-command',
      );
    }
    throw new VibeyCliError(
      `vibey ${args.join(' ')} failed: ${said || result.error || `exit ${result.code}`}`,
      'failed',
    );
  }

  private static json(text: string, what: string): unknown {
    try {
      return JSON.parse(text);
    } catch {
      throw new VibeyCliError(`${what} printed something that is not JSON: ${text.slice(0, 200)}`, 'bad-output');
    }
  }

  private static field(value: unknown, key: string): unknown {
    return VibeyCli.isRecord(value) ? value[key] : undefined;
  }

  private static isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  private static isProject(value: unknown): value is VibeyProject {
    return (
      VibeyCli.isRecord(value) &&
      typeof value.project_id === 'string' &&
      typeof value.name === 'string' &&
      typeof value.phase === 'string'
    );
  }

  private static isGate(value: unknown): value is VibeyGate {
    return (
      VibeyCli.isRecord(value) &&
      typeof value.gate_id === 'string' &&
      typeof value.project_id === 'string' &&
      typeof value.kind === 'string' &&
      typeof value.prompt === 'string'
    );
  }
}

/** How a person answers a gate from a quick pick, in the modes `vibey answer` takes. */
export class GateAnswerPlanner implements GateAnswerPlannerInterface {
  /** The verdicts `vibey answer --verdict` accepts, when a review gate lists none. */
  static readonly VERDICTS = ['accept', 'changes', 'cancel', 'approve', 'request_changes'];

  mode(gate: VibeyGate): AnswerMode {
    const hint = gate.answer_with ?? '';
    if (/--verdict\b/.test(hint)) {
      return 'verdict';
    }
    if (/--choice\b/.test(hint)) {
      return 'choice';
    }
    if (/--defaults\b|\s\w+=\S/.test(hint)) {
      return 'interview';
    }
    if (/--raw\b/.test(hint)) {
      return 'raw';
    }
    const kind = gate.kind.toLowerCase();
    if (kind.includes('interview')) {
      return 'interview';
    }
    if (/review|approval|acceptance/.test(kind)) {
      return 'verdict';
    }
    if (/triage|choice|deploy|route/.test(kind)) {
      return 'choice';
    }
    return 'raw';
  }

  choices(gate: VibeyGate): readonly AnswerChoice[] {
    const mode = this.mode(gate);
    const marked = (value: string): string | undefined =>
      gate.default_answer === value ? 'the default' : undefined;
    const raw: AnswerChoice = {
      label: 'Answer with JSON…',
      description: 'vibey answer --raw, for any other shape',
      needs: 'raw',
    };
    if (mode === 'verdict' || mode === 'choice') {
      const values = gate.options.length > 0 ? gate.options : mode === 'verdict' ? GateAnswerPlanner.VERDICTS : [];
      return [
        ...values.map((value): AnswerChoice => {
          const description = marked(value);
          return {
            label: value,
            ...(description === undefined ? {} : { description }),
            answer: { mode, value },
          };
        }),
        raw,
      ];
    }
    if (mode === 'interview') {
      return [
        { label: 'Accept every default', description: 'vibey answer --defaults', answer: { mode: 'defaults' } },
        { label: 'Answer questions…', description: 'QUESTION_ID=ANSWER pairs; the rest take their defaults', needs: 'pairs' },
        raw,
      ];
    }
    return [raw];
  }

  parsePairs(text: string): Readonly<Record<string, string>> | string {
    const pairs: Record<string, string> = {};
    const items = text.trim().split(/\s+/).filter((item) => item !== '');
    if (items.length === 0) {
      return 'Type at least one QUESTION_ID=ANSWER pair.';
    }
    for (const item of items) {
      const equals = item.indexOf('=');
      if (equals <= 0) {
        return `"${item}" is not QUESTION_ID=ANSWER.`;
      }
      pairs[item.slice(0, equals)] = item.slice(equals + 1);
    }
    return pairs;
  }

  checkRaw(text: string): string | undefined {
    try {
      const parsed: unknown = JSON.parse(text);
      return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
        ? undefined
        : 'vibey answer --raw takes a JSON object, like {"max_dollars": 25}.';
    } catch (error) {
      return `That is not JSON: ${(error as Error).message}`;
    }
  }
}
