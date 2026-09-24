// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Getting Ollama running and the model onto the machine.
 *
 * Nothing in vibey pulls models, so the download is Ollama's own POST /api/pull, whose
 * streamed JSON lines (status, total, completed) drive a progress bar; when it fails the
 * person is shown `ollama pull <model>`, which does the same thing in a terminal.
 *
 * Nothing distinguishes the Ollama app from `ollama serve`, `brew services` or a systemd
 * unit from the outside, so starting always probes first and never starts a second
 * server when one answers. Every operating-system fact is read by
 * `OllamaStartFactsReader` and every decision taken by `OllamaStartPlanner`, so a new
 * platform (Ubuntu 26.04 is next, #1116) changes those two and nothing else. Declared by
 * `interfaces/ollama-interface.ts`.
 */
import type { HttpClientInterface } from './interfaces/http-client-interface';
import type {
  ModelPullerInterface,
  OllamaEndpointInterface,
  OllamaStartFacts,
  OllamaStartFactsReaderInterface,
  OllamaStartPlan,
  OllamaStartPlannerInterface,
  Platform,
  PullOutcome,
  PullProgressInterface,
  PullUpdate,
} from './interfaces/ollama-interface';
import type { ProcessRunnerInterface } from './interfaces/process-runner-interface';
import { ModelName } from './ollama';

/** Folds /api/pull's per-layer lines into one running total. */
export class PullProgress implements PullProgressInterface {
  private readonly totals = new Map<string, number>();
  private readonly completed = new Map<string, number>();

  accept(line: string): PullUpdate {
    let record: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(line);
      record =
        typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {};
    } catch {
      return this.update(line, `Ollama sent a line that is not JSON: ${line.slice(0, 200)}`);
    }
    if (typeof record.error === 'string') {
      return this.update('error', record.error);
    }
    const digest = typeof record.digest === 'string' ? record.digest : undefined;
    if (digest !== undefined && typeof record.total === 'number') {
      this.totals.set(digest, record.total);
      this.completed.set(digest, typeof record.completed === 'number' ? record.completed : 0);
    }
    return this.update(typeof record.status === 'string' ? record.status : 'working');
  }

  private update(status: string, error?: string): PullUpdate {
    const totalBytes = [...this.totals.values()].reduce((sum, value) => sum + value, 0);
    const completedBytes = [...this.completed.values()].reduce((sum, value) => sum + value, 0);
    return {
      status,
      completedBytes,
      totalBytes,
      done: status === 'success',
      ...(totalBytes > 0 ? { percent: Math.floor((completedBytes / totalBytes) * 100) } : {}),
      ...(error === undefined ? {} : { error }),
    };
  }
}

export class ModelPuller implements ModelPullerInterface {
  /** Download sizes from Ollama's catalogue, for the question asked before a download. */
  static readonly SIZE_HINTS: Readonly<Record<string, string>> = {
    'gpt-oss:20b': 'about 14 GB',
    'gpt-oss:120b': 'about 65 GB',
  };

  constructor(
    private readonly http: HttpClientInterface,
    private readonly endpoint: OllamaEndpointInterface,
  ) {}

  static sizeHint(model: string): string | undefined {
    return ModelPuller.SIZE_HINTS[ModelName.normalize(model)];
  }

  static fallbackCommand(model: string): string {
    return `ollama pull ${model}`;
  }

  async pull(
    model: string,
    onUpdate: (update: PullUpdate) => void,
    signal?: AbortSignal,
  ): Promise<PullOutcome> {
    const progress = new PullProgress();
    const fallbackCommand = ModelPuller.fallbackCommand(model);
    let error: string | undefined;
    let succeeded = false;
    let status: number;
    try {
      status = await this.http.postLines(
        this.endpoint.url('/api/pull'),
        { model, stream: true },
        (line) => {
          const update = progress.accept(line);
          error = update.error ?? error;
          succeeded = succeeded || update.done;
          onUpdate(update);
        },
        signal,
      );
    } catch (failure) {
      return { ok: false, error: (failure as Error).message, fallbackCommand };
    }
    if (error !== undefined) {
      return { ok: false, error, fallbackCommand };
    }
    if (status !== 200) {
      return { ok: false, error: `Ollama answered HTTP ${status}`, fallbackCommand };
    }
    if (!succeeded) {
      return { ok: false, error: 'the download ended before Ollama reported success', fallbackCommand };
    }
    return { ok: true, fallbackCommand };
  }
}

export class OllamaStartPlanner implements OllamaStartPlannerInterface {
  plan(facts: OllamaStartFacts, reachable: boolean): OllamaStartPlan {
    if (reachable) {
      return {
        kind: 'already-running',
        explanation: 'Ollama is already running, so nothing was started.',
      };
    }
    if (facts.platform === 'darwin' && facts.appExists) {
      return {
        kind: 'launch',
        command: 'open',
        args: ['-a', facts.appPath],
        explanation: `Opening the Ollama app (${facts.appPath}).`,
      };
    }
    if (facts.platform === 'linux' && facts.systemdUnit) {
      return {
        kind: 'terminal',
        commandLine: 'sudo systemctl start ollama',
        explanation:
          'Ollama is installed as a system service, which only an administrator can start. A terminal opens with the command; type your password there.',
      };
    }
    if (facts.ollamaPath !== undefined) {
      return {
        kind: 'launch',
        command: facts.ollamaPath,
        args: ['serve'],
        explanation: `Starting ${facts.ollamaPath} serve in the background.`,
      };
    }
    return {
      kind: 'impossible',
      explanation:
        'Ollama is not installed. Get it from https://ollama.com/download, open it once, then press "Start Ollama" again.',
    };
  }
}

export class OllamaStartFactsReader implements OllamaStartFactsReaderInterface {
  constructor(
    private readonly platform: Platform,
    private readonly exists: (path: string) => boolean,
    private readonly runner: ProcessRunnerInterface,
  ) {}

  async read(appPath: string, ollamaPath: string | undefined): Promise<OllamaStartFacts> {
    const appExists = this.platform === 'darwin' && appPath !== '' && this.exists(appPath);
    let systemdUnit = false;
    if (this.platform === 'linux') {
      const unit = await this.runner.run('systemctl', ['cat', 'ollama.service'], { timeoutMs: 5000 });
      systemdUnit = unit.code === 0;
    }
    return {
      platform: this.platform,
      appPath,
      appExists,
      systemdUnit,
      ...(ollamaPath === undefined ? {} : { ollamaPath }),
    };
  }
}
