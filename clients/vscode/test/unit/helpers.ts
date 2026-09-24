// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Fakes and scratch directories the unit tests share. */
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { HttpClientInterface, HttpResponse } from '../../src/core/interfaces/http-client-interface';
import type {
  ChildHandle,
  CompletedProcess,
  ProcessExit,
  ProcessRunnerInterface,
  RunOptions,
} from '../../src/core/interfaces/process-runner-interface';
import type { ClockInterface, Disposable, IdSourceInterface } from '../../src/core/interfaces/support-interface';

/** A fresh directory for one test, resolved through symlinks so paths compare equal. */
export function scratch(prefix = 'vibey-vscode-'): string {
  return fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), prefix)));
}

export type Answer = Partial<CompletedProcess> | ((args: readonly string[], options: RunOptions) => Partial<CompletedProcess>);

export interface FakeChildControl {
  readonly command: string;
  readonly args: readonly string[];
  readonly options: RunOptions;
  readonly killed: NodeJS.Signals[];
  stdout(text: string): void;
  stderr(text: string): void;
  exit(exit: ProcessExit): void;
}

/** A process runner that answers from a script and records every call. */
export class FakeProcessRunner implements ProcessRunnerInterface {
  readonly calls: { command: string; args: readonly string[]; options: RunOptions }[] = [];
  readonly children: FakeChildControl[] = [];
  readonly launched: { command: string; args: readonly string[] }[] = [];
  private readonly answers: { match: (command: string, args: readonly string[]) => boolean; answer: Answer }[] = [];
  onSpawn: ((child: FakeChildControl) => void) | undefined;
  launchAnswer: { pid?: number; error?: string } = { pid: 4242 };

  /** Answer calls whose argv contains every word of `words`, in order of registration (last wins). */
  on(words: readonly string[], answer: Answer): this {
    this.answers.unshift({
      match: (command, args) => words.every((word) => [command, ...args].includes(word)),
      answer,
    });
    return this;
  }

  async run(command: string, args: readonly string[], options: RunOptions = {}): Promise<CompletedProcess> {
    this.calls.push({ command, args, options });
    const found = this.answers.find((candidate) => candidate.match(command, args));
    const partial = found === undefined ? {} : typeof found.answer === 'function' ? found.answer(args, options) : found.answer;
    return { code: 0, signal: null, stdout: '', stderr: '', timedOut: false, ...partial };
  }

  spawn(command: string, args: readonly string[], options: RunOptions = {}): ChildHandle {
    const out: ((text: string) => void)[] = [];
    const err: ((text: string) => void)[] = [];
    let resolve: (exit: ProcessExit) => void = () => undefined;
    const exited = new Promise<ProcessExit>((settle) => {
      resolve = settle;
    });
    const control: FakeChildControl = {
      command,
      args,
      options,
      killed: [],
      stdout: (text) => out.forEach((listener) => listener(text)),
      stderr: (text) => err.forEach((listener) => listener(text)),
      exit: (exit) => resolve(exit),
    };
    this.children.push(control);
    const handle: ChildHandle = {
      pid: 1000 + this.children.length,
      onStdout: (listener) => {
        out.push(listener);
      },
      onStderr: (listener) => {
        err.push(listener);
      },
      exited,
      kill: (signal: NodeJS.Signals = 'SIGTERM') => {
        control.killed.push(signal);
        return true;
      },
    };
    queueMicrotask(() => this.onSpawn?.(control));
    return handle;
  }

  async launchDetached(command: string, args: readonly string[]): Promise<{ readonly pid?: number; readonly error?: string }> {
    this.launched.push({ command, args });
    return this.launchAnswer;
  }
}

/** A clock the test moves by hand. `every` callbacks run on `tick()`; `sleep` advances time. */
export class FakeClock implements ClockInterface {
  mono = 0;
  wall = Date.parse('2026-09-24T12:00:00.000Z');
  private readonly timers = new Set<() => void>();

  now(): Date {
    return new Date(this.wall);
  }

  monotonic(): number {
    return this.mono;
  }

  advance(milliseconds: number): void {
    this.mono += milliseconds;
    this.wall += milliseconds;
  }

  every(_milliseconds: number, callback: () => void): Disposable {
    this.timers.add(callback);
    return { dispose: () => this.timers.delete(callback) };
  }

  tick(): void {
    for (const timer of [...this.timers]) {
      timer();
    }
  }

  get active(): number {
    return this.timers.size;
  }

  async sleep(milliseconds: number): Promise<void> {
    this.advance(milliseconds);
    await Promise.resolve();
  }
}

export class SequentialIds implements IdSourceInterface {
  private next = 0;

  uuid(): string {
    this.next += 1;
    return `0000000${this.next}-aaaa-4bbb-8ccc-${String(this.next).padStart(12, '0')}`.slice(-36);
  }
}

/** An HTTP client that answers from a table of routes. */
export class FakeHttp implements HttpClientInterface {
  readonly requests: { method: string; url: string; body?: unknown }[] = [];
  private readonly routes = new Map<string, HttpResponse | Error | ((body: unknown) => HttpResponse)>();
  lines: string[] = [];
  lineStatus = 200;
  linesError: Error | undefined;

  route(method: string, url: string, answer: HttpResponse | Error | ((body: unknown) => HttpResponse)): this {
    this.routes.set(`${method} ${url}`, answer);
    return this;
  }

  get(url: string): Promise<HttpResponse> {
    return this.answer('GET', url, undefined);
  }

  post(url: string, body: unknown): Promise<HttpResponse> {
    return this.answer('POST', url, body);
  }

  async postLines(url: string, body: unknown, onLine: (line: string) => void): Promise<number> {
    this.requests.push({ method: 'POST', url, body });
    if (this.linesError !== undefined) {
      throw this.linesError;
    }
    for (const line of this.lines) {
      onLine(line);
    }
    return this.lineStatus;
  }

  private async answer(method: string, url: string, body: unknown): Promise<HttpResponse> {
    this.requests.push({ method, url, body });
    const answer = this.routes.get(`${method} ${url}`);
    if (answer === undefined) {
      throw new Error(`connect ECONNREFUSED ${url}`);
    }
    if (answer instanceof Error) {
      throw answer;
    }
    return typeof answer === 'function' ? answer(body) : answer;
  }
}

export function json(value: unknown, status = 200): HttpResponse {
  return { status, body: JSON.stringify(value) };
}

/** Let promise callbacks queued so far run. */
export async function settle(times = 5): Promise<void> {
  for (let index = 0; index < times; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

export function fixture(name: string): string {
  return fs.readFileSync(path.join(__dirname, '..', 'fixtures', name), 'utf8');
}
