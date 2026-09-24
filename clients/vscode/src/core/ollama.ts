// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * What the local Ollama server is doing, asked the way the family already asks it.
 *
 * Liveness is GET /api/version with a 2 s timeout, which is qwenloop's own `OllamaProbe`.
 * Whether the model is there is GET /v1/models, which is what `qwenloop doctor` checks,
 * with /api/tags as the second source. What is in memory, and with how large a window,
 * is GET /api/ps. Nothing here is a new kind of check (dogfood rule, ADR-0017). Declared
 * by `interfaces/ollama-interface.ts`.
 */
import type { HttpClientInterface } from './interfaces/http-client-interface';
import type {
  LoadedModel,
  OllamaAdviceInterface,
  OllamaEndpointInterface,
  OllamaProbeInterface,
  OllamaStatus,
  Platform,
} from './interfaces/ollama-interface';

export class OllamaEndpoint implements OllamaEndpointInterface {
  /** Ollama's own default address, the same one qwenloop falls back to. */
  static readonly DEFAULT_ROOT = 'http://127.0.0.1:11434';

  readonly root: string;

  /** `raw` may carry a trailing slash or a trailing `/v1`; either is taken off. */
  constructor(raw: string) {
    let root = raw.trim().replace(/\/+$/, '');
    if (root.endsWith('/v1')) {
      root = root.slice(0, -3).replace(/\/+$/, '');
    }
    if (!/^https?:\/\/[^/]+/.test(root)) {
      throw new Error(`${raw} is not an http:// or https:// address`);
    }
    this.root = root;
  }

  get v1(): string {
    return `${this.root}/v1`;
  }

  url(path: string): string {
    return `${this.root}${path.startsWith('/') ? path : `/${path}`}`;
  }
}

/** Model names as Ollama compares them: an untagged name means `:latest`. */
export class ModelName {
  static normalize(name: string): string {
    const trimmed = name.trim();
    const lastSegment = trimmed.slice(trimmed.lastIndexOf('/') + 1);
    return lastSegment.includes(':') ? trimmed : `${trimmed}:latest`;
  }

  static same(left: string, right: string): boolean {
    return ModelName.normalize(left) === ModelName.normalize(right);
  }
}

export class OllamaProbe implements OllamaProbeInterface {
  constructor(
    private readonly http: HttpClientInterface,
    private readonly endpoint: OllamaEndpointInterface,
    private readonly livenessTimeoutMs = 2000,
    private readonly listTimeoutMs = 5000,
  ) {}

  async version(): Promise<{ readonly version?: string; readonly error?: string }> {
    try {
      const response = await this.http.get(this.endpoint.url('/api/version'), this.livenessTimeoutMs);
      if (response.status !== 200) {
        return { error: `${this.endpoint.url('/api/version')} answered HTTP ${response.status}` };
      }
      const parsed = OllamaProbe.object(response.body);
      return { version: typeof parsed.version === 'string' ? parsed.version : 'unknown' };
    } catch (error) {
      return { error: (error as Error).message };
    }
  }

  async models(): Promise<{ readonly names: readonly string[]; readonly source: string }> {
    const fromV1 = await this.list('/v1/models', 'data', 'id');
    if (fromV1 !== undefined) {
      return { names: fromV1, source: '/v1/models' };
    }
    const fromTags = await this.list('/api/tags', 'models', 'name');
    if (fromTags !== undefined) {
      return { names: fromTags, source: '/api/tags' };
    }
    throw new Error('Ollama answered but listed no models at /v1/models or /api/tags');
  }

  async loaded(): Promise<readonly LoadedModel[]> {
    const response = await this.http.get(this.endpoint.url('/api/ps'), this.listTimeoutMs);
    if (response.status !== 200) {
      return [];
    }
    const entries = OllamaProbe.object(response.body).models;
    if (!Array.isArray(entries)) {
      return [];
    }
    const loaded: LoadedModel[] = [];
    for (const entry of entries) {
      if (typeof entry !== 'object' || entry === null) {
        continue;
      }
      const record = entry as Record<string, unknown>;
      const name = typeof record.name === 'string' ? record.name : record.model;
      if (typeof name !== 'string') {
        continue;
      }
      const context = record.context_length;
      loaded.push(
        typeof context === 'number' && context > 0 ? { name, contextLength: context } : { name },
      );
    }
    return loaded;
  }

  async status(model: string, contextWindow: number): Promise<OllamaStatus> {
    const base = { root: this.endpoint.root, model, contextWindow };
    const version = await this.version();
    if (version.error !== undefined) {
      return { ...base, reachable: false, error: version.error, contextCheck: 'unknown' };
    }
    const reachable = { ...base, reachable: true, version: version.version as string };
    let listing: { readonly names: readonly string[]; readonly source: string };
    try {
      listing = await this.models();
    } catch (error) {
      return { ...reachable, error: (error as Error).message, contextCheck: 'unknown' };
    }
    const present = listing.names.some((name) => ModelName.same(name, model));
    let loaded: LoadedModel | undefined;
    try {
      loaded = (await this.loaded()).find((entry) => ModelName.same(entry.name, model));
    } catch {
      loaded = undefined;
    }
    const known = loaded?.contextLength;
    return {
      ...reachable,
      modelPresent: present,
      modelSource: listing.source,
      ...(loaded === undefined ? {} : { loaded }),
      contextCheck: known === undefined ? 'unknown' : contextWindow > known ? 'too-small' : 'ok',
    };
  }

  /** The `key` field of each entry under `field`, or undefined when the answer is not a list. */
  private async list(path: string, field: string, key: string): Promise<string[] | undefined> {
    try {
      const response = await this.http.get(this.endpoint.url(path), this.listTimeoutMs);
      if (response.status !== 200) {
        return undefined;
      }
      const entries = OllamaProbe.object(response.body)[field];
      if (!Array.isArray(entries)) {
        return undefined;
      }
      return entries
        .map((entry: unknown) =>
          typeof entry === 'object' && entry !== null ? (entry as Record<string, unknown>)[key] : undefined,
        )
        .filter((name): name is string => typeof name === 'string');
    } catch {
      return undefined;
    }
  }

  /** A JSON object's fields, or none when the text is not a JSON object. */
  private static object(text: string): Record<string, unknown> {
    try {
      const parsed: unknown = JSON.parse(text);
      return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
}

/** Status in words a person who has never heard of Ollama can act on. */
export class OllamaAdvice implements OllamaAdviceInterface {
  summary(status: OllamaStatus): string {
    if (!status.reachable) {
      return `Ollama is not running at ${status.root}`;
    }
    if (status.modelPresent === undefined) {
      return `Ollama ${status.version} is running; its model list could not be read`;
    }
    if (!status.modelPresent) {
      return `Ollama ${status.version} is running; ${status.model} is not downloaded`;
    }
    if (status.contextCheck === 'too-small') {
      return `${status.model} is loaded with a ${OllamaAdvice.tokens(status.loaded?.contextLength)}-token window, smaller than the ${OllamaAdvice.tokens(status.contextWindow)} tasks need`;
    }
    return `Ollama ${status.version} is running and ${status.model} is ready`;
  }

  advice(status: OllamaStatus, platform: Platform): readonly string[] {
    if (!status.reachable) {
      return [
        'Ollama is the free program that runs the AI model on your own computer. It is not answering.',
        'Press "Start Ollama". If Ollama is not installed yet, get it from https://ollama.com/download and open it once.',
      ];
    }
    if (status.modelPresent === undefined) {
      return [`Ollama answered, but its list of models could not be read: ${status.error}.`];
    }
    if (!status.modelPresent) {
      return [
        `The model ${status.model} is not on this computer yet.`,
        'Press "Download the model". It downloads once; after that everything runs offline.',
      ];
    }
    if (status.contextCheck === 'too-small') {
      return [
        `Ollama loaded ${status.model} with room for ${OllamaAdvice.tokens(status.loaded?.contextLength)} tokens, but tasks are planned for ${OllamaAdvice.tokens(status.contextWindow)}. On a long task Ollama would drop the beginning without saying so.`,
        ...OllamaAdvice.contextFix(status.contextWindow, platform),
      ];
    }
    return [];
  }

  /** How to give the server a larger window, for this operating system. */
  static contextFix(window: number, platform: Platform): readonly string[] {
    if (platform === 'darwin') {
      return [
        `In the Ollama app, open Settings and set the context length to at least ${window}, then quit and reopen the app.`,
        `If you run Ollama without the app: launchctl setenv OLLAMA_CONTEXT_LENGTH ${window}, then restart Ollama.`,
      ];
    }
    if (platform === 'linux') {
      return [
        `As a service: sudo systemctl edit ollama, add Environment="OLLAMA_CONTEXT_LENGTH=${window}" under [Service], then sudo systemctl restart ollama.`,
        `By hand: stop Ollama and start it again with OLLAMA_CONTEXT_LENGTH=${window} ollama serve.`,
      ];
    }
    return [`Start Ollama with OLLAMA_CONTEXT_LENGTH=${window} in its environment.`];
  }

  private static tokens(count: number | undefined): string {
    return count === undefined ? 'an unknown number of' : count.toLocaleString('en-US');
  }
}
