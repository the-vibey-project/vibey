// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The two transports behind `VibeyTransportInterface`.
 *
 * `LocalProcessTransport` is the command line the extension already drives (`vibey … --json`,
 * ADR-0059: never the database). It stays free of Node itself: the process runner is injected,
 * and the extension injects its Node one. `HubTransport` is the network transport for mobile
 * and web. Its client is to be generated from the hub's OpenAPI document,
 * `docs/reference/hub-api.json`, which the hub lane has not landed yet; until it does, every
 * call is refused with a `HubTransportError`, so nothing mistakes the stub for a hub.
 * Declared by `interfaces/transport-interface.ts`.
 */
import type { HttpClientInterface } from './interfaces/http-client-interface';
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
  constructor(message: string) {
    super(message);
    this.name = 'HubTransportError';
  }
}

/** A vibey hub over the network. A stub until the hub's OpenAPI document exists. */
export class HubTransport implements VibeyTransportInterface {
  /** Where the generated client's contract will come from. */
  static readonly OPENAPI_DOCUMENT = 'docs/reference/hub-api.json';
  readonly kind: TransportKind = 'hub';

  constructor(
    readonly baseUrl: string,
    readonly http: HttpClientInterface,
  ) {}

  version(): Promise<string> {
    return this.refuse('version');
  }

  projects(): Promise<readonly VibeyProject[]> {
    return this.refuse('projects');
  }

  gates(_projectId?: string): Promise<readonly VibeyGate[]> {
    return this.refuse('gates');
  }

  status(_projectId?: string): Promise<VibeyStatus> {
    return this.refuse('status');
  }

  answer(_gateId: string, _answer: GateAnswer): Promise<string> {
    return this.refuse('answer');
  }

  bump(_jobId: string, _projectId?: string): Promise<string> {
    return this.refuse('bump');
  }

  loops(): Promise<unknown> {
    return this.refuse('loops');
  }

  budgets(): Promise<readonly VibeyBudget[]> {
    return this.refuse('budgets');
  }

  setBudget(_projectId: string | undefined, _caps: { readonly dollars?: number; readonly turns?: number }): Promise<string> {
    return this.refuse('setBudget');
  }

  clearBudget(_projectId: string | undefined, _which: 'dollars' | 'turns' | 'all'): Promise<string> {
    return this.refuse('clearBudget');
  }

  cost(_projectId?: string): Promise<string> {
    return this.refuse('cost');
  }

  private refuse(call: string): Promise<never> {
    return Promise.reject(
      new HubTransportError(
        `${call}: the hub transport is not built yet. Its client is generated from ${HubTransport.OPENAPI_DOCUMENT}, ` +
          `which ${this.baseUrl} cannot be reached through until that document lands. Use the local process transport.`,
      ),
    );
  }
}
