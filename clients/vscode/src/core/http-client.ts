// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * A small HTTP client on Node's own `http` and `https` modules, so the extension carries
 * no runtime dependency. Declared by `interfaces/http-client-interface.ts`.
 */
import * as http from 'node:http';
import * as https from 'node:https';
import type { HttpClientInterface, HttpResponse } from './interfaces/http-client-interface';

/** One protocol's request function: `http.request`, `https.request`, or a test's stand-in. */
export type RequestFunction = (
  url: URL,
  options: http.RequestOptions,
  callback: (response: http.IncomingMessage) => void,
) => http.ClientRequest;

export class NodeHttpClient implements HttpClientInterface {
  constructor(
    private readonly transports: Readonly<Record<string, RequestFunction>> = {
      'http:': http.request,
      'https:': https.request,
    },
  ) {}

  get(url: string, timeoutMs: number): Promise<HttpResponse> {
    return this.request('GET', url, undefined, timeoutMs);
  }

  post(url: string, body: unknown, timeoutMs: number): Promise<HttpResponse> {
    return this.request('POST', url, body, timeoutMs);
  }

  postLines(
    url: string,
    body: unknown,
    onLine: (line: string) => void,
    signal?: AbortSignal,
  ): Promise<number> {
    return new Promise((resolve, reject) => {
      const request = this.open('POST', url, (response) => {
        let pending = '';
        response.setEncoding('utf8');
        response.on('data', (chunk: string) => {
          pending += chunk;
          let newline = pending.indexOf('\n');
          while (newline >= 0) {
            const line = pending.slice(0, newline).trim();
            pending = pending.slice(newline + 1);
            if (line) {
              onLine(line);
            }
            newline = pending.indexOf('\n');
          }
        });
        response.on('end', () => {
          const rest = pending.trim();
          if (rest) {
            onLine(rest);
          }
          resolve(NodeHttpClient.status(response));
        });
        response.on('error', reject);
      });
      request.on('error', reject);
      if (signal !== undefined) {
        const abort = (): void => {
          request.destroy(new Error('cancelled'));
        };
        if (signal.aborted) {
          abort();
        } else {
          signal.addEventListener('abort', abort, { once: true });
        }
      }
      request.end(JSON.stringify(body));
    });
  }

  private request(
    method: string,
    url: string,
    body: unknown,
    timeoutMs: number,
  ): Promise<HttpResponse> {
    return new Promise((resolve, reject) => {
      const request = this.open(method, url, (response) => {
        let text = '';
        response.setEncoding('utf8');
        response.on('data', (chunk: string) => {
          text += chunk;
        });
        response.on('end', () => resolve({ status: NodeHttpClient.status(response), body: text }));
        response.on('error', reject);
      });
      request.setTimeout(timeoutMs, () => {
        request.destroy(new Error(`no answer from ${url} within ${timeoutMs} ms`));
      });
      request.on('error', reject);
      request.end(body === undefined ? undefined : JSON.stringify(body));
    });
  }

  private open(
    method: string,
    url: string,
    onResponse: (response: http.IncomingMessage) => void,
  ): http.ClientRequest {
    const target = new URL(url);
    const request = this.transports[target.protocol];
    if (request === undefined) {
      throw new Error(`${url}: only http and https are supported`);
    }
    return request(
      target,
      { method, headers: { 'content-type': 'application/json', accept: 'application/json' } },
      onResponse,
    );
  }

  /** A client-side response always carries a status code; the type allows none. */
  private static status(response: http.IncomingMessage): number {
    return response.statusCode as number;
  }
}
