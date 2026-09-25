// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The pieces that touch the machine: files, HTTP and processes, tested against the real thing. */
import * as fs from 'node:fs';
import * as http from 'node:http';
import type { AddressInfo } from 'node:net';
import * as path from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { NodeHttpClient, type RequestFunction } from '../../src/core/http-client';
import { JsonlJournal, JsonlParse, JsonlTail } from '../../src/core/jsonl';
import { NodeProcessRunner } from '../../src/core/process-runner';
import { scratch } from './helpers';

describe('JsonlTail', () => {
  it('reads new complete lines from a byte offset, and leaves a torn last line for next time', () => {
    const file = path.join(scratch(), 'events.jsonl');
    const tail = new JsonlTail(4);
    expect(tail.read(file, 0)).toEqual({ records: [], malformed: 0, nextOffset: 0, missing: true, restarted: false });
    fs.writeFileSync(file, '{"a":1}\n{"b":"é"}\n{"c":');
    const first = tail.read(file, 0);
    expect(first.records).toEqual([{ a: 1 }, { b: 'é' }]);
    expect(first.nextOffset).toBe(Buffer.byteLength('{"a":1}\n{"b":"é"}\n'));
    expect(tail.read(file, first.nextOffset).records).toEqual([]);
    fs.appendFileSync(file, '3}\nnot json\n\n');
    const second = tail.read(file, first.nextOffset);
    expect(second.records).toEqual([{ c: 3 }]);
    expect(second.malformed).toBe(1);
    expect(tail.read(file, second.nextOffset)).toEqual({ records: [], malformed: 0, nextOffset: second.nextOffset, missing: false, restarted: false });
  });

  it('starts again when the file becomes shorter than the offset', () => {
    const file = path.join(scratch(), 'events.jsonl');
    fs.writeFileSync(file, '{"x":1}\n');
    const chunk = new JsonlTail().read(file, 100);
    expect(chunk.restarted).toBe(true);
    expect(chunk.records).toEqual([{ x: 1 }]);
  });
});

describe('JsonlParse', () => {
  it('skips blank lines and counts the ones that are not JSON', () => {
    expect(JsonlParse.lines('{"a":1}\n\n  \n{nope\n[2]')).toEqual({ records: [{ a: 1 }, [2]], malformed: 1 });
  });
});

describe('JsonlJournal', () => {
  it('appends durable lines, creating its directory, and ends a torn line rather than cutting it', () => {
    const file = path.join(scratch(), 'deep', 'journal.jsonl');
    const journal = new JsonlJournal(file);
    expect(journal.readAll()).toEqual({ records: [], malformed: 0 });
    journal.append({ type: 'one' });
    fs.appendFileSync(file, '{"torn":');
    journal.append({ type: 'two' });
    journal.append({ type: 'three' });
    expect(fs.readFileSync(file, 'utf8')).toBe('{"type":"one"}\n{"torn":\n{"type":"two"}\n{"type":"three"}\n');
    fs.appendFileSync(file, '[1]\n');
    expect(journal.readAll()).toEqual({ records: [{ type: 'one' }, { type: 'two' }, { type: 'three' }], malformed: 2 });
    expect(journal.file).toBe(file);
  });
});

describe('NodeHttpClient', () => {
  let server: http.Server;
  let base = '';

  beforeAll(async () => {
    server = http.createServer((request, response) => {
      let body = '';
      request.on('data', (chunk: Buffer) => (body += chunk.toString()));
      request.on('end', () => {
        if (request.url === '/slow') {
          return;
        }
        if (request.url === '/lines') {
          response.writeHead(200);
          response.write('{"n":1}\n\n{"n"');
          setTimeout(() => response.end(':2}\n{"n":3}'), 10);
          return;
        }
        if (request.url === '/whoami') {
          response.writeHead(200);
          response.end(request.headers.authorization ?? 'nobody');
          return;
        }
        if (request.url === '/lines-ended') {
          response.writeHead(201);
          response.end('{"n":1}\n');
          return;
        }
        response.writeHead(request.url === '/missing' ? 404 : 200, { 'content-type': 'application/json' });
        response.end(JSON.stringify({ method: request.method, body }));
      });
    });
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  });

  afterAll(async () => {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  });

  it('gets and posts JSON, with the status', async () => {
    const client = new NodeHttpClient();
    expect(await client.get(`${base}/x`, 2000)).toEqual({ status: 200, body: '{"method":"GET","body":""}' });
    expect(await client.post(`${base}/x`, { a: 1 }, 2000)).toEqual({ status: 200, body: '{"method":"POST","body":"{\\"a\\":1}"}' });
    expect((await client.get(`${base}/missing`, 2000)).status).toBe(404);
  });

  it("sends a hub's bearer key only when it is given one", async () => {
    const client = new NodeHttpClient();
    expect((await client.get(`${base}/whoami`, 2000)).body).toBe('nobody');
    expect((await client.get(`${base}/whoami`, 2000, { authorization: 'Bearer k' })).body).toBe('Bearer k');
    expect((await client.post(`${base}/whoami`, {}, 2000, { authorization: 'Bearer p' })).body).toBe('Bearer p');
  });

  it('gives up on a server that does not answer in time, and on one that is not there', async () => {
    const client = new NodeHttpClient();
    await expect(client.get(`${base}/slow`, 50)).rejects.toThrow('within 50 ms');
    await expect(client.get('http://127.0.0.1:1/x', 2000)).rejects.toThrow();
    await expect(client.get('ftp://127.0.0.1/x', 2000)).rejects.toThrow('only http and https are supported');
    await expect(client.get('not a url', 2000)).rejects.toThrow();
  });

  it('streams lines as they arrive, joining a line split across chunks', async () => {
    const lines: string[] = [];
    expect(await new NodeHttpClient().postLines(`${base}/lines`, {}, (line) => lines.push(line))).toBe(200);
    expect(lines).toEqual(['{"n":1}', '{"n":2}', '{"n":3}']);
    const ended: string[] = [];
    expect(await new NodeHttpClient().postLines(`${base}/lines-ended`, {}, (line) => ended.push(line))).toBe(201);
    expect(ended).toEqual(['{"n":1}']);
  });

  it('stops a stream when asked, before or during it', async () => {
    const before = new AbortController();
    before.abort();
    await expect(new NodeHttpClient().postLines(`${base}/slow`, {}, () => undefined, before.signal)).rejects.toThrow('cancelled');
    const during = new AbortController();
    const pending = new NodeHttpClient().postLines(`${base}/slow`, {}, () => undefined, during.signal);
    setTimeout(() => during.abort(), 20);
    await expect(pending).rejects.toThrow('cancelled');
  });

  it('uses the https transport for an https address', async () => {
    const seen: string[] = [];
    const viaHttp: RequestFunction = (url, options, callback) => {
      seen.push(url.protocol);
      return http.request(new URL(`${base}${url.pathname}`), options, callback);
    };
    const client = new NodeHttpClient({ 'http:': http.request, 'https:': viaHttp });
    expect((await client.get('https://ollama.example/x', 2000)).status).toBe(200);
    expect(seen).toEqual(['https:']);
  });
});

describe('NodeProcessRunner', () => {
  const runner = new NodeProcessRunner();
  const node = process.execPath;

  it('runs a program to completion with its output, directory and environment', async () => {
    const directory = scratch();
    const result = await runner.run(node, ['-e', 'process.stdout.write(process.cwd() + "|" + process.env.ONLY); process.stderr.write("warn"); process.exit(3)'], {
      cwd: directory,
      env: { ONLY: 'this', PATH: process.env.PATH ?? '' },
    });
    expect(result).toEqual({ code: 3, signal: null, stdout: `${directory}|this`, stderr: 'warn', timedOut: false });
    const inherited = await runner.run(node, ['-e', 'process.stdout.write("ok")']);
    expect(inherited.stdout).toBe('ok');
  });

  it('reports a program that cannot start, and one that runs out of time', async () => {
    const missing = await runner.run('/definitely/not/a/program', []);
    expect(missing.code).toBeNull();
    expect(missing.error).toContain('/definitely/not/a/program');
    const slow = await runner.run(node, ['-e', 'setTimeout(() => {}, 10000)'], { timeoutMs: 100 });
    expect(slow.timedOut).toBe(true);
    expect(slow.signal).toBe('SIGTERM');
    expect(slow.error).toBe('timed out after 100 ms');
  });

  it('streams a child and lets it be killed', async () => {
    const child = runner.spawn(node, ['-e', 'console.log("hello"); setTimeout(() => {}, 10000)']);
    expect(child.pid).toBeGreaterThan(0);
    const lines: string[] = [];
    child.onStdout((text) => lines.push(text));
    child.onStderr(() => undefined);
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(child.kill()).toBe(true);
    expect(await child.exited).toEqual({ code: null, signal: 'SIGTERM' });
    expect(lines.join('')).toContain('hello');
  });

  it('launches a program that outlives this one, or says why it could not', async () => {
    const launched = await runner.launchDetached(node, ['-e', 'setTimeout(() => {}, 50)'], { env: { PATH: process.env.PATH ?? '' } });
    expect(launched.pid).toBeGreaterThan(0);
    expect(await runner.launchDetached(node, ['-e', ''])).toHaveProperty('pid');
    expect((await runner.launchDetached('/definitely/not/a/program', [])).error).toContain('/definitely/not/a/program');
  });
});
