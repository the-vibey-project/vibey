// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The only network a krypton client uses: the local Ollama server's HTTP API, and a vibey hub
 * (`vibey serve`, ADR-0068) when one is paired. `headers` carries a hub's bearer key; nothing
 * else sends one.
 */

import type { AbortSignalLike } from './platform-interface';

export interface HttpResponse {
  readonly status: number;
  readonly body: string;
}

export interface HttpClientInterface {
  /** Rejects on a refused connection, a bad URL, or no answer within `timeoutMs`. */
  get(url: string, timeoutMs: number, headers?: Readonly<Record<string, string>>): Promise<HttpResponse>;
  post(url: string, body: unknown, timeoutMs: number, headers?: Readonly<Record<string, string>>): Promise<HttpResponse>;
  /**
   * POST and hand each line of the streamed answer to `onLine` as it arrives. Resolves
   * with the status once the answer ends; `signal` aborts it.
   */
  postLines(
    url: string,
    body: unknown,
    onLine: (line: string) => void,
    signal?: AbortSignalLike,
  ): Promise<number>;
}
