// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The two transports behind `VibeyTransportInterface`.
 *
 * `LocalProcessTransport` is the command line the extension already drives (`vibey … --json`,
 * ADR-0059: never the database). It stays free of Node itself: the process runner is injected,
 * and the extension injects its Node one. `HubTransport` is the network transport, for the
 * extension's "Connect to vibey on this network", mobile and web. It speaks the hub's routes as
 * `docs/reference/hub-api.json` states them (ADR-0068), and reads every reply with the same
 * parsers as the command line, because the hub returns the very documents `--json` prints.
 * What the hub does not offer (a cap changed from the network, `vibey cost`) is refused with a
 * `HubTransportError` that says where to do it instead. Declared by
 * `interfaces/transport-interface.ts` and `interfaces/hub-interface.ts`.
 */
import type { HttpClientInterface, HttpResponse } from './interfaces/http-client-interface';
import type { HubDiscoveryInterface, HubKeyCheck, HubProbe } from './interfaces/hub-interface';
import type { Environment, ProcessRunnerInterface } from './interfaces/process-runner-interface';
import type { TransportKind, VibeyTransportInterface } from './interfaces/transport-interface';
import type { GateAnswer, VibeyBudget, VibeyGate, VibeyProject, VibeyStatus } from './interfaces/vibey-cli-interface';
import { VibeyCli } from './vibey-cli';

/** vibey's own command line on this machine, through an injected process runner. */
export class LocalProcessTransport extends VibeyCli implements VibeyTransportInterface {
  readonly kind: TransportKind = 'local-process';

  constructor(runner: ProcessRunnerInterface, executable: string, environment: Environment, timeoutMs?: number) {
    super(runner, executable, environment, timeoutMs);
  }
}

export class HubTransportError extends Error {
  constructor(
    message: string,
    /** The hub's HTTP status, when it answered at all. */
    readonly status?: number,
  ) {
    super(message);
    this.name = 'HubTransportError';
  }
}

/** A vibey hub over the network, with the key this device was paired with. */
export class HubTransport implements VibeyTransportInterface {
  /** The contract every route below follows. */
  static readonly OPENAPI_DOCUMENT = 'docs/reference/hub-api.json';
  /** Where a running hub serves that same reply, without a key. */
  static readonly OPENAPI_ROUTE = '/api/v1/openapi.json';
  /** The port `vibey serve` listens on when `[hub] port` does not say (docs/reference/configuration.md). */
  static readonly DEFAULT_PORT = 8765;
  readonly kind: TransportKind = 'hub';
  readonly baseUrl: string;

  constructor(
    baseUrl: string,
    readonly http: HttpClientInterface,
    private readonly key?: string,
    private readonly timeoutMs = 15_000,
    /** Names each gate answer so a retry is a no-op on the hub (`request_id`). */
    private readonly requestIds: () => string = HubTransport.requestId,
  ) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  async version(): Promise<string> {
    const reply = await this.read(HubTransport.OPENAPI_ROUTE, 'the OpenAPI document');
    const info = HubTransport.record(HubTransport.record(reply).info);
    return `vibey hub, API ${typeof info.version === 'string' ? `v${info.version}` : 'of unknown version'}, at ${this.baseUrl}`;
  }

  async projects(): Promise<readonly VibeyProject[]> {
    return VibeyCli.readProjects(await this.read('/api/v1/projects', 'projects'));
  }

  async gates(projectId?: string): Promise<readonly VibeyGate[]> {
    const query = projectId === undefined ? '' : `?project_id=${encodeURIComponent(projectId)}`;
    return VibeyCli.readGates(await this.read(`/api/v1/gates${query}`, 'gates'));
  }

  /** One project's status; with none named, the first the hub lists, as `vibey status` takes the latest. */
  async status(projectId?: string): Promise<VibeyStatus> {
    const id = projectId ?? (await this.projects())[0]?.project_id;
    if (id === undefined) {
      throw new HubTransportError(`status: ${this.baseUrl} has no projects yet. Create one on the host with vibey new.`);
    }
    return VibeyCli.readStatus(await this.read(`/api/v1/projects/${encodeURIComponent(id)}/status`, 'status'));
  }

  /** Answered once, under this device's name on the hub; a retry of the same request is a no-op there. */
  async answer(gateId: string, answer: GateAnswer): Promise<string> {
    const body = { answer: HubTransport.payload(answer), request_id: this.requestIds() };
    const reply = HubTransport.record(await this.send(`/api/v1/gates/${encodeURIComponent(gateId)}/answer`, body, 'answer'));
    return reply.replayed === true ? `already answered ${gateId} by this request; nothing changed` : `answered ${gateId}`;
  }

  async bump(jobId: string, projectId?: string): Promise<string> {
    if (projectId === undefined) {
      throw new HubTransportError('bump: the hub bumps a job within its project, so name the project too.');
    }
    await this.send(`/api/v1/projects/${encodeURIComponent(projectId)}/queue/${encodeURIComponent(jobId)}/bump`, {}, 'bump');
    return `bumped ${jobId}`;
  }

  loops(): Promise<unknown> {
    return this.read('/api/v1/loops', 'loops');
  }

  /** Every project's budget: the hub serves them one project at a time, each the `budget show --json` reply. */
  async budgets(): Promise<readonly VibeyBudget[]> {
    const projects = await this.projects();
    const replies = await Promise.all(
      projects.map((project) => this.read(`/api/v1/projects/${encodeURIComponent(project.project_id)}/budget`, 'budget')),
    );
    return VibeyCli.readBudgets(replies);
  }

  setBudget(_projectId: string | undefined, _caps: { readonly dollars?: number; readonly turns?: number }): Promise<string> {
    return this.hostOnly('setBudget', 'vibey budget set');
  }

  clearBudget(_projectId: string | undefined, _which: 'dollars' | 'turns' | 'all'): Promise<string> {
    return this.hostOnly('clearBudget', 'vibey budget clear');
  }

  cost(_projectId?: string): Promise<string> {
    return Promise.reject(new HubTransportError(`cost: ${this.baseUrl} serves no cost report; run vibey cost on the host.`));
  }

  /** What `vibey answer` sends for each mode (src/vibey/cli/main.py), as the hub's `answer` object. */
  static payload(answer: GateAnswer): Record<string, unknown> {
    switch (answer.mode) {
      case 'verdict':
        return { verdict: answer.value };
      case 'choice':
        return { choice: answer.value };
      case 'defaults':
        return { accept_defaults: true };
      case 'pairs':
        return { ...answer.pairs, ...(answer.defaults ? { accept_defaults: true } : {}) };
      case 'raw':
        return HubTransport.record(VibeyCli.json(answer.json, 'the answer'));
    }
  }

  /** What each refusal the hub documents means, in words a person can act on (docs/reference/hub-api.md). */
  static explain(status: number, call: string, baseUrl: string): string {
    const words: Readonly<Record<number, string>> = {
      401: `${baseUrl} does not know this device's key. Pair again: krypton: Connect to vibey on this network.`,
      403: "this device's key does not permit it. The host grants scopes when it pairs a device.",
      404: 'there is no such project or open gate on the hub.',
      409: 'another request got there first: the gate was already answered, or the queue refused the change.',
      421: `the hub does not answer to this name. Connect by an address it serves, or add the name to [hub] names in the host's vibey.toml.`,
      422: 'the hub could not read the request.',
      429: 'the hub is asking for fewer requests; try again in a moment.',
    };
    return `${call}: ${words[status] ?? `the hub answered HTTP ${status}.`}`;
  }

  private hostOnly(call: string, command: string): Promise<never> {
    return Promise.reject(
      new HubTransportError(`${call}: no scope can change a cap over the network (ADR-0068). Change it on the host with ${command}.`),
    );
  }

  private async read(route: string, call: string): Promise<unknown> {
    return this.parse(await this.request(() => this.http.get(`${this.baseUrl}${route}`, this.timeoutMs, this.headers()), call), call);
  }

  private async send(route: string, body: unknown, call: string): Promise<unknown> {
    return this.parse(await this.request(() => this.http.post(`${this.baseUrl}${route}`, body, this.timeoutMs, this.headers()), call), call);
  }

  private async request(call: () => Promise<HttpResponse>, name: string): Promise<HttpResponse> {
    let response: HttpResponse;
    try {
      response = await call();
    } catch (error) {
      throw new HubTransportError(`${name}: ${this.baseUrl} did not answer (${(error as Error).message}).`);
    }
    if (response.status !== 200) {
      throw new HubTransportError(HubTransport.explain(response.status, name, this.baseUrl), response.status);
    }
    return response;
  }

  private parse(response: HttpResponse, call: string): unknown {
    try {
      return JSON.parse(response.body);
    } catch {
      throw new HubTransportError(`${call}: ${this.baseUrl} answered with something that is not JSON.`, response.status);
    }
  }

  private headers(): Readonly<Record<string, string>> {
    return this.key === undefined ? {} : { authorization: `Bearer ${this.key}` };
  }

  private static record(value: unknown): Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  }

  private static requestId(): string {
    return `krypton-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  }
}

/** Looking for a hub: this computer first, then the names a person gives. Nothing is trusted for answering. */
export class HubDiscovery implements HubDiscoveryInterface {
  constructor(
    private readonly http: HttpClientInterface,
    private readonly timeoutMs = 1_500,
  ) {}

  candidates(extraNames: readonly string[], port: number = HubTransport.DEFAULT_PORT): readonly string[] {
    const all = ['127.0.0.1', 'localhost', ...extraNames].map((name) => HubDiscovery.address(name, port)).filter((url) => url !== '');
    return [...new Set(all)];
  }

  probe(urls: readonly string[]): Promise<readonly HubProbe[]> {
    return Promise.all(urls.map((url) => this.probeOne(url)));
  }

  async checkKey(url: string, key: string): Promise<HubKeyCheck> {
    const address = HubDiscovery.address(url, HubTransport.DEFAULT_PORT);
    if (address === '') {
      return { ok: false, reason: 'bad-address', message: `"${url}" is not an address to connect to.` };
    }
    try {
      const projects = await new HubTransport(address, this.http, key, this.timeoutMs * 4).projects();
      return { ok: true, projects: projects.length };
    } catch (error) {
      const status = (error as HubTransportError).status;
      const reason = status === 401 ? 'refused' : status === 403 ? 'forbidden' : 'unreachable';
      return { ok: false, reason, message: (error as Error).message };
    }
  }

  /** `studio.local`, `studio.local:9000` or `http://10.0.0.5:8765/x` as `scheme://host:port`; blank or unreadable is ''. */
  static address(name: string, port: number): string {
    const trimmed = name.trim();
    if (trimmed === '') {
      return '';
    }
    const match = /^(?:(https?):\/\/)?(\[[0-9a-f:.]+\]|[a-z0-9.-]+)(?::(\d{1,5}))?(?:\/.*)?$/i.exec(trimmed);
    if (match === null) {
      return '';
    }
    const [, scheme, host, given] = match as unknown as [string, string | undefined, string, string | undefined];
    return `${(scheme ?? 'http').toLowerCase()}://${host.toLowerCase()}:${given ?? port}`;
  }

  private async probeOne(url: string): Promise<HubProbe> {
    try {
      const live = await this.http.get(`${url}/health/live`, this.timeoutMs);
      if (live.status !== 200) {
        return { url, live: false, offersPairing: false, problem: `${url}/health/live answered HTTP ${live.status}, so this is not a vibey hub.` };
      }
    } catch (error) {
      return { url, live: false, offersPairing: false, problem: `nothing answered at ${url} (${(error as Error).message}).` };
    }
    try {
      const reply = JSON.parse((await this.http.get(`${url}${HubTransport.OPENAPI_ROUTE}`, this.timeoutMs)).body) as {
        info?: { version?: unknown };
        paths?: Record<string, unknown>;
      };
      const version = reply.info?.version;
      return {
        url,
        live: true,
        ...(typeof version === 'string' ? { apiVersion: version } : {}),
        offersPairing: Object.keys(reply.paths ?? {}).some((route) => /\bpair/.test(route)),
      };
    } catch {
      return { url, live: true, offersPairing: false };
    }
  }
}
