// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The only network the extension uses: the local Ollama server's HTTP API. */

export interface HttpResponse {
  readonly status: number;
  readonly body: string;
}

export interface HttpClientInterface {
  /** Rejects on a refused connection, a bad URL, or no answer within `timeoutMs`. */
  get(url: string, timeoutMs: number): Promise<HttpResponse>;
  post(url: string, body: unknown, timeoutMs: number): Promise<HttpResponse>;
  /**
   * POST and hand each line of the streamed answer to `onLine` as it arrives. Resolves
   * with the status once the answer ends; `signal` aborts it.
   */
  postLines(
    url: string,
    body: unknown,
    onLine: (line: string) => void,
    signal?: AbortSignal,
  ): Promise<number>;
}
