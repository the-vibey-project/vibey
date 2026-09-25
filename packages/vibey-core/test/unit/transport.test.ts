// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { HubDiscovery, HubTransport, HubTransportError, LocalProcessTransport } from '../../src/transport';
import { FakeHttp, FakeProcessRunner } from './helpers';

describe('LocalProcessTransport', () => {
  it("is vibey's own command line, through the process runner it is given", async () => {
    const transport = new LocalProcessTransport(new FakeProcessRunner().on(['vibey', '--version'], { stdout: 'vibey 3.0.0\n' }), 'vibey', {});
    expect(transport.kind).toBe('local-process');
    expect(await transport.version()).toBe('vibey 3.0.0');
  });
});

describe('HubTransport', () => {
  const base = 'http://studio.local:8765';
  const ok = (body: unknown) => ({ status: 200, body: JSON.stringify(body) });
  const project = { project_id: 'p1', name: 'greeter', phase: 'BUILD' };
  const budget = {
    project_id: 'p1',
    name: 'greeter',
    cycle: 2,
    caps: { max_cycle_dollars: 5, max_cycle_turns: null },
    spend: { dollars: 1.5, turns: 3 },
    exhausted: false,
    history: [],
  };
  const hubWith = (http: FakeHttp) => new HubTransport(`${base}/`, http, 'k3y', 1000, () => 'req-1');

  it('knows its address, its contract, and sends its key as a bearer token', async () => {
    const http = new FakeHttp().route('GET', `${base}/api/v1/projects`, ok([project, { project_id: 'x' }]));
    const hub = hubWith(http);
    expect(hub.kind).toBe('hub');
    expect(hub.baseUrl).toBe(base);
    expect(HubTransport.OPENAPI_DOCUMENT).toBe('docs/reference/hub-api.json');
    expect(await hub.projects()).toEqual([project]);
    expect(http.requests[0]?.headers).toEqual({ authorization: 'Bearer k3y' });
  });

  it('sends no authorization at all without a key', async () => {
    const http = new FakeHttp().route('GET', `${base}/api/v1/loops`, ok({ loops: [] }));
    expect(await new HubTransport(base, http).loops()).toEqual({ loops: [] });
    expect(http.requests[0]?.headers).toEqual({});
  });

  it('names the API version it serves, or says it is unknown', async () => {
    const http = new FakeHttp().route('GET', `${base}/api/v1/openapi.json`, ok({ info: { version: '1' } }));
    expect(await hubWith(http).version()).toBe(`vibey hub, API v1, at ${base}`);
    const bare = new FakeHttp().route('GET', `${base}/api/v1/openapi.json`, ok([]));
    expect(await hubWith(bare).version()).toBe(`vibey hub, API of unknown version, at ${base}`);
  });

  it('reads gates, for every project or one', async () => {
    const gate = { gate_id: 'g1', project_id: 'p1', kind: 'approval', prompt: 'ok?', job_id: null, default_answer: null, timeout_at: null };
    const http = new FakeHttp()
      .route('GET', `${base}/api/v1/gates`, ok({ gates: [gate] }))
      .route('GET', `${base}/api/v1/gates?project_id=p%201`, ok({ gates: [] }));
    const hub = hubWith(http);
    expect(await hub.gates()).toEqual([{ ...gate, options: [] }]);
    expect(await hub.gates('p 1')).toEqual([]);
  });

  it("reads a project's status, taking the first project when none is named", async () => {
    const status = { project_id: 'p1', name: 'greeter', phase: 'BUILD', queue_depth: {}, circuits: [], active_worktrees: [] };
    const http = new FakeHttp()
      .route('GET', `${base}/api/v1/projects`, ok([project]))
      .route('GET', `${base}/api/v1/projects/p1/status`, ok(status));
    const hub = hubWith(http);
    expect((await hub.status()).phase).toBe('BUILD');
    expect((await hub.status('p1')).name).toBe('greeter');
    const empty = new FakeHttp().route('GET', `${base}/api/v1/projects`, ok([]));
    await expect(hubWith(empty).status()).rejects.toThrow(/has no projects yet/);
  });

  it('answers a gate once, with a request id, in the shape vibey answer sends', async () => {
    const seen: unknown[] = [];
    const http = new FakeHttp().route('POST', `${base}/api/v1/gates/g1/answer`, (body) => {
      seen.push(body);
      return ok(seen.length === 1 ? { answered: true } : { replayed: true });
    });
    const hub = hubWith(http);
    expect(await hub.answer('g1', { mode: 'verdict', value: 'accept' })).toBe('answered g1');
    expect(await hub.answer('g1', { mode: 'verdict', value: 'accept' })).toBe('already answered g1 by this request; nothing changed');
    expect(seen[0]).toEqual({ answer: { verdict: 'accept' }, request_id: 'req-1' });
    expect(http.requests[0]?.headers).toEqual({ authorization: 'Bearer k3y' });
  });

  it('turns every answer mode into the object the hub takes', () => {
    expect(HubTransport.payload({ mode: 'choice', value: 'deploy' })).toEqual({ choice: 'deploy' });
    expect(HubTransport.payload({ mode: 'defaults' })).toEqual({ accept_defaults: true });
    expect(HubTransport.payload({ mode: 'pairs', pairs: { q1: 'yes' }, defaults: true })).toEqual({ q1: 'yes', accept_defaults: true });
    expect(HubTransport.payload({ mode: 'pairs', pairs: { q1: 'yes' }, defaults: false })).toEqual({ q1: 'yes' });
    expect(HubTransport.payload({ mode: 'raw', json: '{"max_dollars": 25}' })).toEqual({ max_dollars: 25 });
    expect(HubTransport.payload({ mode: 'raw', json: '[1]' })).toEqual({});
  });

  it('bumps a job within its project, and asks for the project when it is missing', async () => {
    const http = new FakeHttp().route('POST', `${base}/api/v1/projects/p1/queue/j1/bump`, ok({ bumped: true }));
    const hub = hubWith(http);
    expect(await hub.bump('j1', 'p1')).toBe('bumped j1');
    await expect(hub.bump('j1')).rejects.toThrow(/name the project too/);
  });

  it("reads every project's budget, one project at a time", async () => {
    const http = new FakeHttp()
      .route('GET', `${base}/api/v1/projects`, ok([project]))
      .route('GET', `${base}/api/v1/projects/p1/budget`, ok(budget));
    expect(await hubWith(http).budgets()).toEqual([budget]);
  });

  it('refuses what only the host may do, and says where to do it', async () => {
    const hub = hubWith(new FakeHttp());
    await expect(hub.setBudget(undefined, { dollars: 5 })).rejects.toThrow(/setBudget: no scope can change a cap .* vibey budget set/);
    await expect(hub.clearBudget('p1', 'all')).rejects.toThrow(/clearBudget: .* vibey budget clear/);
    await expect(hub.cost()).rejects.toThrow(/serves no cost report; run vibey cost on the host/);
  });

  it('explains each refusal the hub documents, and carries its status', async () => {
    for (const [status, words] of [
      [401, /does not know this device's key\. Pair again/],
      [403, /does not permit it/],
      [404, /no such project or open gate/],
      [409, /got there first/],
      [421, /\[hub\] names/],
      [422, /could not read the request/],
      [429, /fewer requests/],
      [500, /answered HTTP 500/],
    ] as const) {
      const http = new FakeHttp().route('GET', `${base}/api/v1/projects`, { status, body: '' });
      const error = await hubWith(http).projects().catch((reason: unknown) => reason);
      expect(error).toBeInstanceOf(HubTransportError);
      expect((error as HubTransportError).status).toBe(status);
      expect((error as Error).message).toMatch(words);
    }
  });

  it('says plainly when the hub does not answer or answers with something that is not JSON', async () => {
    const down = new FakeHttp();
    await expect(hubWith(down).projects()).rejects.toThrow(/did not answer \(connect ECONNREFUSED/);
    const garbled = new FakeHttp().route('GET', `${base}/api/v1/loops`, { status: 200, body: '<html>' });
    const error = (await hubWith(garbled).loops().catch((reason: unknown) => reason)) as HubTransportError;
    expect(error.message).toMatch(/not JSON/);
    expect(error.name).toBe('HubTransportError');
  });

  it('makes its own request ids when none are given', async () => {
    const seen: unknown[] = [];
    const http = new FakeHttp().route('POST', `${base}/api/v1/gates/g1/answer`, (body) => {
      seen.push(body);
      return ok({});
    });
    await new HubTransport(base, http).answer('g1', { mode: 'defaults' });
    expect((seen[0] as { request_id: string }).request_id).toMatch(/^krypton-[a-z0-9]+-[a-z0-9]+$/);
  });
});

describe('HubDiscovery', () => {
  const ok = (body: unknown) => ({ status: 200, body: JSON.stringify(body) });

  it('looks on this computer first, then at the names given, on the hub port, once each', () => {
    const discovery = new HubDiscovery(new FakeHttp());
    expect(discovery.candidates(['studio.local', 'https://mac.lan:9443/x', '', 'localhost', '[fe80::1]', 'fe80::1', 'ftp://nope'])).toEqual([
      'http://127.0.0.1:8765',
      'http://localhost:8765',
      'http://studio.local:8765',
      'https://mac.lan:9443',
      'http://[fe80::1]:8765',
    ]);
    expect(discovery.candidates([], 9000)).toEqual(['http://127.0.0.1:9000', 'http://localhost:9000']);
    expect(HubDiscovery.address('http://[::1', 8765)).toBe('');
  });

  it('knows a live hub, its API version, and whether it offers pairing', async () => {
    const http = new FakeHttp()
      .route('GET', 'http://a:8765/health/live', ok({ status: 'live' }))
      .route('GET', 'http://a:8765/api/v1/openapi.json', ok({ info: { version: '1' }, paths: { '/api/v1/projects': {} } }))
      .route('GET', 'http://b:8765/health/live', ok({}))
      .route('GET', 'http://b:8765/api/v1/openapi.json', ok({ paths: { '/api/v1/pair': {} } }))
      .route('GET', 'http://c:8765/health/live', ok({}))
      .route('GET', 'http://c:8765/api/v1/openapi.json', { status: 200, body: 'nope' })
      .route('GET', 'http://d:8765/health/live', { status: 404, body: '' })
      .route('GET', 'http://e:8765/health/live', ok({}))
      .route('GET', 'http://e:8765/api/v1/openapi.json', ok({}));
    const probes = await new HubDiscovery(http).probe(['http://a:8765', 'http://b:8765', 'http://c:8765', 'http://d:8765', 'http://z:8765', 'http://e:8765']);
    expect(probes[0]).toEqual({ url: 'http://a:8765', live: true, apiVersion: '1', offersPairing: false });
    expect(probes[1]).toEqual({ url: 'http://b:8765', live: true, offersPairing: true });
    expect(probes[2]).toEqual({ url: 'http://c:8765', live: true, offersPairing: false });
    expect(probes[3]?.live).toBe(false);
    expect(probes[3]?.problem).toMatch(/answered HTTP 404, so this is not a vibey hub/);
    expect(probes[4]?.problem).toMatch(/nothing answered at http:\/\/z:8765/);
    expect(probes[5]).toEqual({ url: 'http://e:8765', live: true, offersPairing: false });
  });

  it('checks a key by what the hub says, never by the network it came from', async () => {
    const http = new FakeHttp()
      .route('GET', 'http://good:8765/api/v1/projects', ok([{ project_id: 'p1', name: 'n', phase: 'BUILD' }]))
      .route('GET', 'http://bad:8765/api/v1/projects', { status: 401, body: '' })
      .route('GET', 'http://narrow:8765/api/v1/projects', { status: 403, body: '' });
    const discovery = new HubDiscovery(http);
    expect(await discovery.checkKey('good', 'k')).toEqual({ ok: true, projects: 1 });
    expect(await discovery.checkKey('bad', 'k')).toMatchObject({ ok: false, reason: 'refused' });
    expect(await discovery.checkKey('narrow', 'k')).toMatchObject({ ok: false, reason: 'forbidden' });
    expect(await discovery.checkKey('gone', 'k')).toMatchObject({ ok: false, reason: 'unreachable' });
    expect(await discovery.checkKey('  ', 'k')).toMatchObject({ ok: false, reason: 'bad-address' });
    expect(http.requests[0]?.headers).toEqual({ authorization: 'Bearer k' });
  });
});
