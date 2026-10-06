// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { readFileSync } from 'fs';
import { join } from 'path';
import { HubClient, HubError } from '../../src/core/hub-client';
import type { FetchInit, FetchLike } from '../../src/core/interfaces/hub-client-interface';

type Route = { status: number; body: unknown } | Error;

/** A hub made of canned answers, recording every request. */
function fakeHub(routes: Record<string, Route>) {
  const calls: { url: string; init: FetchInit }[] = [];
  const fetchLike: FetchLike = async (url, init) => {
    calls.push({ url, init });
    const path = url.replace('http://hub.local:8765', '');
    const route = routes[`${init.method} ${path}`];
    if (route === undefined) {
      return { status: 404, text: async () => '' };
    }
    if (route instanceof Error) {
      throw route;
    }
    const text = typeof route.body === 'string' ? route.body : JSON.stringify(route.body);
    return { status: route.status, text: async () => text };
  };
  const client = new HubClient({ baseUrl: 'http://hub.local:8765', token: 's3cret' }, fetchLike, () => 'req');
  return { client, calls };
}

const project = { project_id: 'p1', name: 'Greeter', phase: 'BUILD', cycle: 1, max_cycles: 3, open_gates: 2 };
const gate = {
  gate_id: 'g1',
  project_id: 'p1',
  project_name: 'Greeter',
  job_id: null,
  kind: 'review_collect',
  prompt: 'Accept?',
  options: ['accept', 7, 'changes'],
  default_answer: null,
  timeout_at: null,
};

describe('HubClient', () => {
  it('is written against every route it calls in the committed OpenAPI document', () => {
    const document = JSON.parse(
      readFileSync(join(__dirname, '../../../..', HubClient.OPENAPI_DOCUMENT), 'utf8'),
    ) as { info: { version: string }; paths: Record<string, Record<string, unknown>> };
    expect(document.info.version).toBe(HubClient.API_VERSION);
    const used = [
      ['get', '/health/live'],
      ['get', '/health/ready'],
      ['get', '/api/v1/projects'],
      ['get', '/api/v1/gates'],
      ['post', '/api/v1/gates/{gate_id}/answer'],
      ['get', '/api/v1/projects/{project_id}/status'],
      ['get', '/api/v1/projects/{project_id}/budget'],
      ['get', '/api/v1/projects/{project_id}/queue'],
      ['post', '/api/v1/projects/{project_id}/queue/{job_id}/bump'],
      ['get', '/api/v1/loops'],
      ['get', '/api/v1/lanes'],
      ['get', '/api/v1/doctor'],
      ['post', '/api/v1/workflows/runs'],
      ['get', '/api/v1/workflows/runs/{request_id}'],
    ];
    for (const [method, path] of used) {
      expect(document.paths[path as string]?.[method as string]).toBeDefined();
    }
  });

  it('sends the bearer token and reads projects', async () => {
    const { client, calls } = fakeHub({ 'GET /api/v1/projects': { status: 200, body: [project, { junk: true }, 'x'] } });
    expect(client.kind).toBe('hub');
    await expect(client.projects()).resolves.toEqual([project]);
    expect(calls[0]?.init.headers.Authorization).toBe('Bearer s3cret');
  });

  it('reads gates, keeping only string options, and asks for one project', async () => {
    const { client, calls } = fakeHub({
      'GET /api/v1/gates': { status: 200, body: { gates: [gate, { gate_id: 'bad' }] } },
      'GET /api/v1/gates?project_id=p%201': {
        status: 200,
        body: { gates: [{ ...gate, prompt: undefined, options: undefined }] },
      },
    });
    const all = await client.gates();
    expect(all).toHaveLength(1);
    expect(all[0]?.options).toEqual(['accept', 'changes']);
    const one = await client.gates('p 1');
    expect(one[0]).toMatchObject({ prompt: '', options: [] });
    expect(calls[1]?.url).toContain('?project_id=p%201');
  });

  it('refuses a gates document that is not a list', async () => {
    const { client } = fakeHub({ 'GET /api/v1/gates': { status: 200, body: [] } });
    await expect(client.gates()).rejects.toMatchObject({ refusal: 'bad-answer' });
  });

  it('reads a status in full and with every optional field missing', async () => {
    const { client } = fakeHub({
      'GET /api/v1/projects/p1/status': {
        status: 200,
        body: {
          project_id: 'p1',
          name: 'Greeter',
          phase: 'BUILD',
          cycle: 2,
          max_cycles: 5,
          queue_depth: { ready: 3, bad: 'x' },
          circuits: [{ engine_id: 'claudeloop' }, { nope: 1 }],
          active_worktrees: ['/w', 4],
        },
      },
      'GET /api/v1/projects/p2/status': { status: 200, body: { project_id: 'p2', phase: 'DESIGN' } },
      'GET /api/v1/projects/p3/status': { status: 200, body: { phase: 'DESIGN' } },
    });
    await expect(client.status('p1')).resolves.toEqual({
      project_id: 'p1',
      name: 'Greeter',
      phase: 'BUILD',
      cycle: 2,
      max_cycles: 5,
      queue_depth: { ready: 3 },
      circuits: [{ engine_id: 'claudeloop' }],
      active_worktrees: ['/w'],
    });
    await expect(client.status('p2')).resolves.toEqual({
      project_id: 'p2',
      name: 'p2',
      phase: 'DESIGN',
      queue_depth: {},
      circuits: [],
      active_worktrees: [],
    });
    await expect(client.status('p3')).rejects.toMatchObject({ refusal: 'bad-answer' });
    await expect(client.status()).rejects.toMatchObject({ refusal: 'invalid' });
  });

  it('answers a gate once, with a request id, and says when it was a replay', async () => {
    const { client, calls } = fakeHub({
      'POST /api/v1/gates/g1/answer': { status: 200, body: { replayed: false } },
      'POST /api/v1/gates/g2/answer': { status: 200, body: { replayed: true } },
    });
    await expect(client.answer('g1', { mode: 'verdict', value: 'accept' })).resolves.toBe('Answered.');
    const sent = JSON.parse(calls[0]?.init.body ?? '{}') as unknown;
    expect(sent).toEqual({ answer: { verdict: 'accept' }, request_id: 'req-1' });
    expect(calls[0]?.init.headers['Content-Type']).toBe('application/json');
    await expect(client.answer('g2', { mode: 'choice', value: 'yes' })).resolves.toMatch(/Already answered/);
    expect(JSON.parse(calls[1]?.init.body ?? '{}')).toEqual({ answer: { choice: 'yes' }, request_id: 'req-2' });
  });

  it('reuses the request id when the same answer is retried', async () => {
    const { client, calls } = fakeHub({ 'POST /api/v1/gates/g1/answer': { status: 200, body: {} } });
    await client.answer('g1', { mode: 'verdict', value: 'accept' });
    await client.answer('g1', { mode: 'verdict', value: 'accept' });
    await client.answer('g1', { mode: 'verdict', value: 'changes' });
    const ids = calls.map((call) => (JSON.parse(call.init.body ?? '{}') as { request_id: string }).request_id);
    expect(ids).toEqual(['req-1', 'req-1', 'req-2']);
  });

  it('turns every answer mode into what vibey answer --raw takes, or refuses it', () => {
    expect(HubClient.answerDocument({ mode: 'pairs', pairs: { q1: 'yes' }, defaults: false })).toEqual({ q1: 'yes' });
    expect(HubClient.answerDocument({ mode: 'raw', json: '{"max_dollars": 25}' })).toEqual({ max_dollars: 25 });
    expect(() => HubClient.answerDocument({ mode: 'pairs', pairs: {}, defaults: true })).toThrow(HubError);
    expect(() => HubClient.answerDocument({ mode: 'defaults' })).toThrow(/on the host/);
    expect(() => HubClient.answerDocument({ mode: 'raw', json: '{' })).toThrow(/not JSON/);
    expect(() => HubClient.answerDocument({ mode: 'raw', json: '[1]' })).toThrow(/JSON object/);
  });

  it('bumps a job of a named project only', async () => {
    const { client, calls } = fakeHub({ 'POST /api/v1/projects/p1/queue/j1/bump': { status: 200, body: {} } });
    await expect(client.bump('j1', 'p1')).resolves.toMatch(/front/);
    expect(calls[0]?.init.body).toBe('{}');
    await expect(client.bump('j1')).rejects.toMatchObject({ refusal: 'invalid' });
  });

  it('reads loops, lanes, the doctor and the queue', async () => {
    const { client } = fakeHub({
      'GET /api/v1/loops': { status: 200, body: { loops: [] } },
      'GET /api/v1/lanes': {
        status: 200,
        body: {
          lanes: [
            { id: 'a', engine: 'gptossloop', label: 'w · gptossloop', state: 'running', outcome: 'ok', offset: 10, last_event_at: 5 },
            { id: 'b' },
            { nope: true },
          ],
        },
      },
      'GET /api/v1/doctor': {
        status: 200,
        body: { scope: 'hub', checks: [{ name: 'database', mark: 'PASS', detail: 'answers' }, { name: 'x' }, 3] },
      },
      'GET /api/v1/projects/p1/queue': {
        status: 200,
        body: { jobs: [{ job_id: 'j1', kind: 'build', state: 'ready', phase: 'BUILD', position: 1 }, { job_id: 'j2' }, {}] },
      },
    });
    await expect(client.loops()).resolves.toEqual({ loops: [] });
    await expect(client.lanes()).resolves.toEqual([
      { id: 'a', engine: 'gptossloop', label: 'w · gptossloop', state: 'running', outcome: 'ok', offset: 10, last_event_at: 5 },
      { id: 'b', engine: 'unknown', label: 'b', state: 'unknown', outcome: null, offset: 0, last_event_at: 0 },
    ]);
    await expect(client.doctor()).resolves.toEqual({
      scope: 'hub',
      checks: [
        { name: 'database', mark: 'PASS', detail: 'answers' },
        { name: 'x', mark: 'FAIL', detail: '' },
      ],
    });
    await expect(client.queue('p1')).resolves.toEqual([
      { job_id: 'j1', kind: 'build', state: 'ready', phase: 'BUILD', position: 1 },
      { job_id: 'j2', kind: 'job', state: 'unknown', phase: '', position: null },
    ]);
  });

  it('reads a doctor that names no scope', async () => {
    const { client } = fakeHub({ 'GET /api/v1/doctor': { status: 200, body: { checks: [] } } });
    await expect(client.doctor()).resolves.toEqual({ scope: '', checks: [] });
  });

  it('refuses doctor, lanes and queue documents of the wrong shape', async () => {
    const { client } = fakeHub({
      'GET /api/v1/doctor': { status: 200, body: [] },
      'GET /api/v1/lanes': { status: 200, body: [] },
      'GET /api/v1/projects/p1/queue': { status: 200, body: [] },
    });
    await expect(client.doctor()).rejects.toMatchObject({ refusal: 'bad-answer' });
    await expect(client.lanes()).rejects.toMatchObject({ refusal: 'bad-answer' });
    await expect(client.queue('p1')).rejects.toMatchObject({ refusal: 'bad-answer' });
  });

  it('reads every project budget, filling what the hub leaves out', async () => {
    const { client } = fakeHub({
      'GET /api/v1/projects': { status: 200, body: [project, { ...project, project_id: 'p2', name: 'Two' }] },
      'GET /api/v1/projects/p1/budget': {
        status: 200,
        body: {
          name: 'Greeter',
          cycle: 1,
          caps: { max_cycle_dollars: 10, max_cycle_turns: 50 },
          spend: { dollars: 2.5, turns: 4 },
          exhausted: false,
          history: [{ at: 'now', by: 'op', field: 'x', old: 1, new: 2 }, 'junk'],
        },
      },
      'GET /api/v1/projects/p2/budget': { status: 200, body: 'null' },
    });
    const budgets = await client.budgets();
    expect(budgets[0]).toEqual({
      project_id: 'p1',
      name: 'Greeter',
      cycle: 1,
      caps: { max_cycle_dollars: 10, max_cycle_turns: 50 },
      spend: { dollars: 2.5, turns: 4 },
      exhausted: false,
      history: [{ at: 'now', by: 'op', field: 'x', old: 1, new: 2 }],
    });
    expect(budgets[1]).toEqual({
      project_id: 'p2',
      name: 'Two',
      caps: { max_cycle_dollars: null, max_cycle_turns: null },
      spend: { dollars: 0, turns: 0 },
      exhausted: false,
      history: [],
    });
  });

  it('never sets or clears a cap, and leaves cost to the host', async () => {
    const { client, calls } = fakeHub({});
    await expect(client.setBudget()).rejects.toMatchObject({ refusal: 'not-on-a-device' });
    await expect(client.clearBudget()).rejects.toThrow(/lifted on the host/);
    await expect(client.cost()).rejects.toMatchObject({ refusal: 'not-on-a-device' });
    expect(calls).toHaveLength(0);
  });

  it('reports health without credentials, and version from it', async () => {
    const up = fakeHub({ 'GET /health/live': { status: 200, body: {} }, 'GET /health/ready': { status: 503, body: {} } });
    await expect(up.client.health()).resolves.toEqual({ live: true, ready: false });
    expect(up.calls[0]?.init.headers).toEqual({});
    await expect(up.client.version()).resolves.toBe('vibey hub, API v1');
    const down = fakeHub({ 'GET /health/live': new Error('refused') });
    await expect(down.client.health()).resolves.toEqual({ live: false, ready: false });
    await expect(down.client.version()).resolves.toMatch(/not answering/);
  });

  it('says what each refusal means', async () => {
    for (const status of [401, 403, 404, 409, 421, 422, 429, 503]) {
      const { client } = fakeHub({ 'GET /api/v1/projects': { status, body: '' } });
      const error = (await client.projects().catch((caught: unknown) => caught)) as HubError;
      expect(error).toBeInstanceOf(HubError);
      expect(error.status).toBe(status);
      expect(error.refusal).toBe(HubClient.REFUSALS[status]?.[0]);
    }
    const odd = fakeHub({ 'GET /api/v1/projects': { status: 500, body: '' } });
    await expect(odd.client.projects()).rejects.toMatchObject({ refusal: 'bad-answer', status: 500 });
  });

  it('says so when nothing answers, or what answers is not JSON', async () => {
    const gone = fakeHub({ 'GET /api/v1/projects': new Error('ECONNREFUSED') });
    await expect(gone.client.projects()).rejects.toMatchObject({ refusal: 'unreachable' });
    const garbled = fakeHub({ 'GET /api/v1/projects': { status: 200, body: '<html>' } });
    await expect(garbled.client.projects()).rejects.toThrow(/not JSON/);
    const notList = fakeHub({ 'GET /api/v1/projects': { status: 200, body: {} } });
    await expect(notList.client.projects()).rejects.toThrow(/list of projects/);
  });

  it('normalises a typed base URL, and refuses one that is not http(s)', () => {
    expect(HubClient.normaliseBaseUrl(' http://127.0.0.1:8765/ ')).toBe('http://127.0.0.1:8765');
    expect(HubClient.normaliseBaseUrl('https://mac.local:8765')).toBe('https://mac.local:8765');
    expect(HubClient.normaliseBaseUrl('ftp://x')).toHaveProperty('error');
    expect(HubClient.normaliseBaseUrl('http://x/path')).toHaveProperty('error');
  });

  it('starts a workflows run with the argv alone, and takes the 202', async () => {
    const queued = { request_id: 'r1', state: 'queued', url: '', exit_code: null, stdout: '', stderr: '', detail: '' };
    const { client, calls } = fakeHub({ 'POST /api/v1/workflows/runs': { status: 202, body: queued } });
    await expect(client.startWorkflowRun(['status', '--json'])).resolves.toEqual(queued);
    expect(calls[0]?.init.method).toBe('POST');
    expect(calls[0]?.init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(calls[0]?.init.body ?? '')).toEqual({ argv: ['status', '--json'] });
  });

  it('refuses an empty or over-long command line before anything is sent', async () => {
    const { client, calls } = fakeHub({});
    await expect(client.startWorkflowRun([])).rejects.toMatchObject({ refusal: 'invalid' });
    await expect(client.startWorkflowRun(Array.from({ length: 201 }, () => 'x'))).rejects.toThrow(/1 to 200 words/);
    expect(calls).toHaveLength(0);
  });

  it('reads a workflows run, filling what the hub leaves out', async () => {
    const done = { request_id: 'r 1', state: 'done', url: 'https://github.com/o/r/actions/runs/9', exit_code: 0, stdout: '{}', stderr: 'warn', detail: '' };
    const { client, calls } = fakeHub({
      'GET /api/v1/workflows/runs/r%201': { status: 200, body: done },
      'GET /api/v1/workflows/runs/r2': { status: 200, body: { request_id: 'r2', state: 'running', exit_code: '0', url: 7 } },
    });
    await expect(client.workflowRun('r 1')).resolves.toEqual(done);
    expect(calls[0]?.init.headers.Authorization).toBe('Bearer s3cret');
    await expect(client.workflowRun('r2')).resolves.toEqual({
      request_id: 'r2',
      state: 'running',
      url: '',
      exit_code: null,
      stdout: '',
      stderr: '',
      detail: '',
    });
  });

  it('refuses a workflows run that is not one', async () => {
    const { client } = fakeHub({
      'GET /api/v1/workflows/runs/a': { status: 200, body: [] },
      'GET /api/v1/workflows/runs/b': { status: 200, body: { state: 'done' } },
      'GET /api/v1/workflows/runs/c': { status: 200, body: { request_id: 'c', state: 'lost' } },
      'POST /api/v1/workflows/runs': { status: 200, body: { request_id: 'c', state: 'queued' } },
    });
    for (const id of ['a', 'b', 'c']) {
      await expect(client.workflowRun(id)).rejects.toMatchObject({ refusal: 'bad-answer' });
    }
    // The start answers 202; a 200 there is not the contract.
    await expect(client.startWorkflowRun(['status'])).rejects.toMatchObject({ refusal: 'bad-answer', status: 200 });
  });

  it('says what each workflows refusal means, with the hub’s own reason', async () => {
    for (const status of [403, 404, 422, 502, 503]) {
      const { client } = fakeHub({ 'POST /api/v1/workflows/runs': { status, body: { detail: ' why ' } } });
      const error = (await client.startWorkflowRun(['status']).catch((caught: unknown) => caught)) as HubError;
      expect(error.status).toBe(status);
      expect(error.refusal).toBe(HubClient.WORKFLOW_REFUSALS[status]?.[0]);
      expect(error.message).toBe(`${HubClient.WORKFLOW_REFUSALS[status]?.[1]} The hub said: why`);
    }
    const scope = fakeHub({ 'POST /api/v1/workflows/runs': { status: 403, body: { detail: 'phone may not run commands on the workflows' } } });
    await expect(scope.client.startWorkflowRun(['status'])).rejects.toThrow(/needs the `workflows` scope.*phone may not/);
    const off = fakeHub({ 'GET /api/v1/workflows/runs/r': { status: 503, body: 'not json' } });
    await expect(off.client.workflowRun('r')).rejects.toThrow(/^This hub does not run commands on GitHub: workflows are not enabled on it\.$/);
    // FastAPI's validation detail is a list, not a sentence: the plain message stands alone.
    const invalid = fakeHub({ 'POST /api/v1/workflows/runs': { status: 422, body: { detail: [{ msg: 'too long' }] } } });
    await expect(invalid.client.startWorkflowRun(['x'])).rejects.toThrow(/^The hub refused that command line\.$/);
    // Refusals the workflows routes share with every route keep the shared words.
    const busy = fakeHub({ 'POST /api/v1/workflows/runs': { status: 429, body: { detail: 'slow down' } } });
    await expect(busy.client.startWorkflowRun(['x'])).rejects.toMatchObject({ refusal: 'too-many', message: HubClient.REFUSALS[429]?.[1] });
  });

  it('keeps a run link only when it is https, so no other scheme reaches the URL handler', () => {
    expect(HubClient.httpsUrl('https://github.com/o/r/actions/runs/7')).toBe('https://github.com/o/r/actions/runs/7');
    for (const refused of ['javascript:alert(1)', 'intent://x#Intent;end', 'tel:123', 'http://github.com/x', 'not a url', '']) {
      expect(HubClient.httpsUrl(refused)).toBe('');
    }
  });

  it('describes every scope the host may grant, workflows among them', () => {
    expect(Object.keys(HubClient.SCOPES)).toEqual(['view', 'answer', 'spend', 'run', 'bump', 'workflows']);
    expect(HubClient.SCOPES.workflows).toBe("Run vibey commands on the repository's GitHub-hosted runners");
  });

  it('names each request uniquely by default', async () => {
    const calls: string[] = [];
    const client = new HubClient({ baseUrl: 'http://h', token: 't' }, async (_url, init) => {
      calls.push(init.body ?? '');
      return { status: 200, text: async () => '{}' };
    });
    await client.answer('g', { mode: 'choice', value: 'a' });
    expect(JSON.parse(calls[0] ?? '{}').request_id).toMatch(/^krypton-\d+-1$/);
  });
});
