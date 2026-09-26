// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The hub transport Krypton's mobile and web app uses: the routes of
 * `docs/reference/hub-api.json` (ADR-0068, API version 1), over an injected `fetch`, with the
 * host token or a device key as the bearer. Every document is the one the matching
 * `vibey … --json` prints, so it reads the same shapes `@vibey/core`'s `VibeyCli` reads.
 *
 * `@vibey/core`'s own `HubTransport` is still the refusing stub it shipped as; this class is
 * what it becomes, kept here until it moves into the shared core. Declared by
 * `interfaces/hub-client-interface.ts`.
 */
import type {
  GateAnswer,
  TransportKind,
  VibeyBudget,
  VibeyCircuit,
  VibeyGate,
  VibeyProject,
  VibeyStatus,
} from '@vibey/core';
import { DevicePolicy } from './device-policy';
import type {
  FetchLike,
  HubClientInterface,
  HubConnection,
  HubDoctor,
  HubDoctorCheck,
  HubLane,
  HubQueueJob,
  HubRefusal,
} from './interfaces/hub-client-interface';

type Json = Record<string, unknown>;

export class HubError extends Error {
  constructor(
    readonly refusal: HubRefusal,
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'HubError';
  }
}

export class HubClient implements HubClientInterface {
  /** The contract this client is written against. */
  static readonly OPENAPI_DOCUMENT = 'docs/reference/hub-api.json';
  static readonly API_VERSION = '1';
  readonly kind: TransportKind = 'hub';

  /** What each refusal of the hub's table (hub-api.md, "Refusals") means to a person. */
  static readonly REFUSALS: Readonly<Record<number, readonly [HubRefusal, string]>> = {
    401: ['unauthenticated', 'The hub does not know this device. Pair again, or check the token.'],
    403: ['forbidden', 'This device is not allowed to do that. The host decides what each device may do.'],
    404: ['not-found', 'The hub has no such project or open gate. It may have been answered already.'],
    409: ['conflict', 'Someone else got there first: the gate was already answered, or the queue refused the move.'],
    421: ['wrong-host', 'The hub does not answer to this address. Use the address the host shows.'],
    422: ['invalid', 'The hub could not read that request.'],
    429: ['too-many', 'Too many requests. Wait a moment and try again.'],
    503: ['unavailable', "The hub is up, but vibey's database does not answer."],
  };

  private sequence = 0;
  private readonly requestIds = new Map<string, string>();

  constructor(
    readonly connection: HubConnection,
    private readonly fetchLike: FetchLike,
    private readonly newRequestId: () => string = () => `krypton-${Date.now()}`,
  ) {}

  /** A base URL with no trailing slash; an error message when it is not http(s). */
  static normaliseBaseUrl(value: string): string | { readonly error: string } {
    const trimmed = value.trim().replace(/\/+$/, '');
    if (!/^https?:\/\/[^\s/]+$/i.test(trimmed)) {
      return { error: 'Type the hub address as http://host:port, for example http://127.0.0.1:8765.' };
    }
    return trimmed;
  }

  async version(): Promise<string> {
    const { live } = await this.health();
    return live ? `vibey hub, API v${HubClient.API_VERSION}` : 'vibey hub (not answering)';
  }

  async health(): Promise<{ readonly live: boolean; readonly ready: boolean }> {
    const live = await this.probe('/health/live');
    const ready = live ? await this.probe('/health/ready') : false;
    return { live, ready };
  }

  async projects(): Promise<readonly VibeyProject[]> {
    const parsed = await this.get('/api/v1/projects');
    return HubClient.list(parsed, 'projects').filter(
      (item): item is VibeyProject =>
        HubClient.isRecord(item) && typeof item.project_id === 'string' && typeof item.phase === 'string',
    );
  }

  async gates(projectId?: string): Promise<readonly VibeyGate[]> {
    const query = projectId === undefined ? '' : `?project_id=${encodeURIComponent(projectId)}`;
    const parsed = await this.get(`/api/v1/gates${query}`);
    const gates = HubClient.isRecord(parsed) ? parsed.gates : undefined;
    return HubClient.list(gates, 'gates')
      .filter(
        (gate): gate is Json =>
          HubClient.isRecord(gate) && typeof gate.gate_id === 'string' && typeof gate.kind === 'string',
      )
      .map((gate) => ({
        ...(gate as unknown as VibeyGate),
        prompt: typeof gate.prompt === 'string' ? gate.prompt : '',
        options: Array.isArray(gate.options)
          ? gate.options.filter((option): option is string => typeof option === 'string')
          : [],
      }));
  }

  async status(projectId?: string): Promise<VibeyStatus> {
    if (projectId === undefined) {
      throw new HubError('invalid', 'Choose a project first: the hub reports one project at a time.');
    }
    const parsed = await this.get(`/api/v1/projects/${encodeURIComponent(projectId)}/status`);
    if (!HubClient.isRecord(parsed) || typeof parsed.project_id !== 'string' || typeof parsed.phase !== 'string') {
      throw new HubError('bad-answer', 'The hub did not send a project status.');
    }
    const depth = HubClient.isRecord(parsed.queue_depth) ? parsed.queue_depth : {};
    return {
      project_id: parsed.project_id,
      name: typeof parsed.name === 'string' ? parsed.name : parsed.project_id,
      phase: parsed.phase,
      ...(typeof parsed.cycle === 'number' ? { cycle: parsed.cycle } : {}),
      ...(typeof parsed.max_cycles === 'number' ? { max_cycles: parsed.max_cycles } : {}),
      queue_depth: Object.fromEntries(
        Object.entries(depth).filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
      ),
      circuits: Array.isArray(parsed.circuits)
        ? parsed.circuits.filter(
            (circuit): circuit is VibeyCircuit => HubClient.isRecord(circuit) && typeof circuit.engine_id === 'string',
          )
        : [],
      active_worktrees: Array.isArray(parsed.active_worktrees)
        ? parsed.active_worktrees.filter((item): item is string => typeof item === 'string')
        : [],
    };
  }

  async answer(gateId: string, answer: GateAnswer): Promise<string> {
    const document = HubClient.answerDocument(answer);
    // One request id per gate and answer, so a retry after a lost reply is a replay, not a 409.
    const key = `${gateId}:${JSON.stringify(document)}`;
    const requestId = this.requestIds.get(key) ?? this.requestId();
    this.requestIds.set(key, requestId);
    const body = { answer: document, request_id: requestId };
    const parsed = await this.post(`/api/v1/gates/${encodeURIComponent(gateId)}/answer`, body);
    const replayed = HubClient.isRecord(parsed) && parsed.replayed === true;
    return replayed ? 'Already answered with this answer; nothing changed.' : 'Answered.';
  }

  async bump(jobId: string, projectId?: string): Promise<string> {
    if (projectId === undefined) {
      throw new HubError('invalid', 'Choose the project the job belongs to first.');
    }
    await this.post(
      `/api/v1/projects/${encodeURIComponent(projectId)}/queue/${encodeURIComponent(jobId)}/bump`,
      {},
    );
    return 'Moved to the front of the queue.';
  }

  loops(): Promise<unknown> {
    return this.get('/api/v1/loops');
  }

  async budgets(): Promise<readonly VibeyBudget[]> {
    const projects = await this.projects();
    const budgets = await Promise.all(
      projects.map(async (project) => {
        const item = await this.get(`/api/v1/projects/${encodeURIComponent(project.project_id)}/budget`);
        return HubClient.budget(item, project);
      }),
    );
    return budgets;
  }

  setBudget(): Promise<string> {
    return this.hostOnly('set-cap');
  }

  clearBudget(): Promise<string> {
    return this.hostOnly('clear-cap');
  }

  cost(): Promise<string> {
    return Promise.reject(
      new HubError('not-on-a-device', 'Spend is shown per project under Budgets; `vibey cost` runs on the host.'),
    );
  }

  async lanes(): Promise<readonly HubLane[]> {
    const parsed = await this.get('/api/v1/lanes');
    const lanes = HubClient.isRecord(parsed) ? parsed.lanes : undefined;
    return HubClient.list(lanes, 'lanes')
      .filter((lane): lane is Json => HubClient.isRecord(lane) && typeof lane.id === 'string')
      .map((lane) => ({
        id: lane.id as string,
        engine: typeof lane.engine === 'string' ? lane.engine : 'unknown',
        label: typeof lane.label === 'string' ? lane.label : (lane.id as string),
        state: typeof lane.state === 'string' ? lane.state : 'unknown',
        outcome: typeof lane.outcome === 'string' ? lane.outcome : null,
        offset: typeof lane.offset === 'number' ? lane.offset : 0,
        last_event_at: typeof lane.last_event_at === 'number' ? lane.last_event_at : 0,
      }));
  }

  async doctor(): Promise<HubDoctor> {
    const parsed = await this.get('/api/v1/doctor');
    if (!HubClient.isRecord(parsed)) {
      throw new HubError('bad-answer', 'The hub did not send its checks.');
    }
    return {
      scope: typeof parsed.scope === 'string' ? parsed.scope : '',
      checks: HubClient.list(parsed.checks, 'checks')
        .filter((check): check is Json => HubClient.isRecord(check) && typeof check.name === 'string')
        .map(
          (check): HubDoctorCheck => ({
            name: check.name as string,
            mark: typeof check.mark === 'string' ? check.mark : 'FAIL',
            detail: typeof check.detail === 'string' ? check.detail : '',
          }),
        ),
    };
  }

  async queue(projectId: string): Promise<readonly HubQueueJob[]> {
    const parsed = await this.get(`/api/v1/projects/${encodeURIComponent(projectId)}/queue`);
    const jobs = HubClient.isRecord(parsed) ? parsed.jobs : undefined;
    return HubClient.list(jobs, 'jobs')
      .filter((job): job is Json => HubClient.isRecord(job) && typeof job.job_id === 'string')
      .map((job) => ({
        job_id: job.job_id as string,
        kind: typeof job.kind === 'string' ? job.kind : 'job',
        state: typeof job.state === 'string' ? job.state : 'unknown',
        phase: typeof job.phase === 'string' ? job.phase : '',
        position: typeof job.position === 'number' ? job.position : null,
      }));
  }

  /**
   * A `GateAnswer` as the hub takes it: what `vibey answer --raw` takes. `--defaults` is
   * resolved by the command line on the host from the gate's own defaults, so a device cannot
   * send it; it sends pairs instead.
   */
  static answerDocument(answer: GateAnswer): Json {
    switch (answer.mode) {
      case 'verdict':
        return { verdict: answer.value };
      case 'choice':
        return { choice: answer.value };
      case 'pairs':
        if (answer.defaults) {
          throw new HubError('not-on-a-device', 'Accepting the defaults happens on the host. Answer every question here.');
        }
        return { ...answer.pairs };
      case 'raw': {
        let parsed: unknown;
        try {
          parsed = JSON.parse(answer.json);
        } catch {
          throw new HubError('invalid', 'That answer is not JSON.');
        }
        if (!HubClient.isRecord(parsed)) {
          throw new HubError('invalid', 'The answer must be a JSON object, like {"choice": "yes"}.');
        }
        return parsed;
      }
      case 'defaults':
        throw new HubError('not-on-a-device', 'Accepting the defaults happens on the host. Answer every question here.');
    }
  }

  private static budget(item: unknown, project: VibeyProject): VibeyBudget {
    const record = HubClient.isRecord(item) ? item : {};
    const caps = HubClient.isRecord(record.caps) ? record.caps : {};
    const spend = HubClient.isRecord(record.spend) ? record.spend : {};
    return {
      project_id: project.project_id,
      name: typeof record.name === 'string' ? record.name : project.name,
      ...(typeof record.cycle === 'number' ? { cycle: record.cycle } : {}),
      caps: {
        max_cycle_dollars: typeof caps.max_cycle_dollars === 'number' ? caps.max_cycle_dollars : null,
        max_cycle_turns: typeof caps.max_cycle_turns === 'number' ? caps.max_cycle_turns : null,
      },
      spend: {
        dollars: typeof spend.dollars === 'number' ? spend.dollars : 0,
        turns: typeof spend.turns === 'number' ? spend.turns : 0,
      },
      exhausted: record.exhausted === true,
      history: Array.isArray(record.history)
        ? (record.history.filter(HubClient.isRecord) as unknown as VibeyBudget['history'])
        : [],
    };
  }

  private hostOnly(action: 'set-cap' | 'clear-cap'): Promise<never> {
    return Promise.reject(new HubError('not-on-a-device', DevicePolicy.HOST_ONLY[action] as string));
  }

  private requestId(): string {
    this.sequence += 1;
    return `${this.newRequestId()}-${this.sequence}`;
  }

  private async probe(path: string): Promise<boolean> {
    try {
      const response = await this.fetchLike(`${this.connection.baseUrl}${path}`, { method: 'GET', headers: {} });
      return response.status === 200;
    } catch {
      return false;
    }
  }

  private get(path: string): Promise<unknown> {
    return this.send(path, { method: 'GET', headers: this.headers() });
  }

  private post(path: string, body: unknown): Promise<unknown> {
    const text = JSON.stringify(body);
    return this.send(path, {
      method: 'POST',
      headers: { ...this.headers(), 'Content-Type': 'application/json' },
      body: text,
    });
  }

  private headers(): Record<string, string> {
    return { Authorization: `Bearer ${this.connection.token}`, Accept: 'application/json' };
  }

  private async send(path: string, init: { method: 'GET' | 'POST'; headers: Record<string, string>; body?: string }): Promise<unknown> {
    let response;
    try {
      response = await this.fetchLike(`${this.connection.baseUrl}${path}`, init);
    } catch {
      throw new HubError('unreachable', `No hub answers at ${this.connection.baseUrl}. Is \`vibey serve\` running, and is this device on the same network?`);
    }
    const text = await response.text();
    if (response.status !== 200) {
      const known = HubClient.REFUSALS[response.status];
      if (known !== undefined) {
        throw new HubError(known[0], known[1], response.status);
      }
      throw new HubError('bad-answer', `The hub answered ${response.status}.`, response.status);
    }
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new HubError('bad-answer', 'The hub sent something that is not JSON.', response.status);
    }
  }

  private static list(value: unknown, what: string): readonly unknown[] {
    if (!Array.isArray(value)) {
      throw new HubError('bad-answer', `The hub did not send a list of ${what}.`);
    }
    return value;
  }

  private static isRecord(value: unknown): value is Json {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }
}
