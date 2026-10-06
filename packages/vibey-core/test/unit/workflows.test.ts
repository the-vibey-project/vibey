// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// `vibey -w` from a client (ADR-0085): the command line read once, sent as `vibey --workflows …`
// or to the hub's /api/v1/workflows/runs, and what came back read into one result.
import { describe, expect, it } from 'vitest';
import type { HttpResponse } from '../../src/interfaces/http-client-interface';
import type { WorkflowsUpdate } from '../../src/interfaces/workflows-interface';
import { HubTransport, HubTransportError, LocalProcessTransport, WorkflowsTransport } from '../../src/transport';
import { VibeyCli, VibeyCliError } from '../../src/vibey-cli';
import { PortableTimer, WorkflowsCommandLine } from '../../src/workflows';
import { FakeClock, FakeHttp, FakeProcessRunner, fixture } from './helpers';

const line = new WorkflowsCommandLine();
const RAN = 'vibey -w: ran on GitHub: https://github.com/o/r/actions/runs/7\n';

describe('WorkflowsCommandLine', () => {
  it('reads what a person typed as argv: quotes group, and a leading vibey and -w are dropped', () => {
    expect(line.parse('status --json')).toEqual(['status', '--json']);
    expect(line.parse('  vibey -w status  ')).toEqual(['status']);
    expect(line.parse('vibey --workflows queue bump "job one" --source \'x y\'')).toEqual(['queue', 'bump', 'job one', '--source', 'x y']);
    expect(line.parse('--workflows gates')).toEqual(['gates']);
    expect(line.parse('')).toMatch(/Say which vibey command to run on GitHub/);
    expect(line.parse('vibey')).toMatch(/Say which/);
    expect(line.parse('vibey -w')).toMatch(/Say which/);
  });

  it('refuses a command line the workflows would not take, and says why', () => {
    expect(line.check(['status'])).toBeUndefined();
    expect(line.check([])).toMatch(/Say which/);
    expect(line.check(Array.from({ length: 201 }, () => 'x'))).toBe('A command line for the workflows takes at most 200 words; this one has 201.');
    expect(line.check(Array.from({ length: 200 }, () => 'x'))).toBeUndefined();
    expect(line.check(['vibey', 'status'])).toMatch(/Leave out "vibey"/);
    expect(line.check(['-w', 'status'])).toBe('Leave out -w: every command sent this way runs on the workflows.');
    expect(line.check(['--workflows'])).toMatch(/Leave out --workflows/);
  });

  it("reads the run's address out of what vibey -w wrote to stderr, and leaves the rest", () => {
    expect(line.fromProcess({ code: 0, stdout: '{}\n', stderr: `warn: slow\n${RAN}more\n` })).toEqual({
      exitCode: 0,
      stdout: '{}\n',
      stderr: 'warn: slow\nmore\n',
      url: 'https://github.com/o/r/actions/runs/7',
    });
    expect(line.fromProcess({ code: 3, stdout: '', stderr: RAN.trimEnd() })).toEqual({ exitCode: 3, stdout: '', stderr: '', url: 'https://github.com/o/r/actions/runs/7' });
    expect(line.fromProcess({ code: 2, stdout: '', stderr: 'vibey -w: refused\n' })).toEqual({ exitCode: 2, stdout: '', stderr: 'vibey -w: refused\n', url: '' });
    expect(line.fromProcess({ code: null, stdout: '', stderr: '' }).exitCode).toBe(1);
  });

  it("reads the hub's status: a result once it is done or failed, and where it is meanwhile", () => {
    expect(line.fromHub({ state: 'queued', url: '' })).toEqual({ update: { state: 'queued', url: '' } });
    expect(line.fromHub({ state: 'running', url: 'u' })).toEqual({ update: { state: 'running', url: 'u' } });
    expect(line.fromHub({ state: 'done', url: 'u', exit_code: 0, stdout: 'out', stderr: 'err' }).result).toEqual({ exitCode: 0, stdout: 'out', stderr: 'err', url: 'u' });
    expect(line.fromHub({ state: 'done', url: 'u', exit_code: null, stdout: 'out', stderr: '' }).result).toEqual({
      exitCode: 1,
      stdout: 'out',
      stderr: 'vibey -w: the run finished but handed back no exit code\n',
      url: 'u',
    });
    expect(line.fromHub({ state: 'failed', detail: 'the run was cancelled', url: 'u' }).result?.stderr).toBe('vibey -w: the run was cancelled\n');
    expect(line.fromHub({ state: 'failed' }).result).toEqual({ exitCode: 1, stdout: '', stderr: 'vibey -w: failed\n', url: '' });
    expect(line.fromHub([1])).toEqual({ update: { state: 'unknown', url: '' } });
    expect(line.fromHub(null)).toEqual({ update: { state: 'unknown', url: '' } });
  });

  it('says a wait that ran out as vibey -w does: 124, and the run when there is one', () => {
    expect(line.timedOut('', 60 * 60_000)).toEqual({ exitCode: 124, stdout: '', stderr: 'vibey -w: no report from GitHub within 60 minutes; the run may still finish.\n', url: '' });
    expect(line.timedOut('u', 60_000).stderr).toBe('vibey -w: no report from GitHub within 1 minute; the run may still finish: u\n');
    expect(WorkflowsCommandLine.duration(90_000)).toBe('90 seconds');
    expect(WorkflowsCommandLine.duration(1000)).toBe('1 second');
  });

  it('reports a result as lines and as one sentence', () => {
    const argv = ['queue', 'bump', 'job one', ''];
    expect(line.report(argv, { exitCode: 0, stdout: 'a\nb\n\n', stderr: 'w\r\n', url: 'u' })).toEqual([
      '$ vibey -w queue bump "job one" ""',
      'ran on GitHub: u',
      'exit code 0',
      '--- stdout',
      'a',
      'b',
      '--- stderr',
      'w',
    ]);
    expect(line.report(['status'], { exitCode: 1, stdout: ' \n', stderr: '', url: '' })).toEqual(['$ vibey -w status', 'GitHub showed no run for it.', 'exit code 1']);
    expect(line.summary(['status'], { exitCode: 0, stdout: '', stderr: 'noise', url: 'u' })).toBe('vibey -w status exited 0 (u).');
    expect(line.summary(['status'], { exitCode: 124, stdout: '', stderr: '', url: '' })).toBe('vibey -w status: no report from GitHub in time; the run may still finish.');
    expect(line.summary(['status'], { exitCode: 124, stdout: '', stderr: '', url: 'u' })).toMatch(/may still finish \(u\)\.$/);
    expect(line.summary(['status'], { exitCode: 3, stdout: '', stderr: 'first\n  VIBEY_PG_URL is not set.  \n\n', url: '' })).toBe(
      'vibey -w status exited 3: VIBEY_PG_URL is not set.',
    );
    expect(line.summary(['status'], { exitCode: 3, stdout: '', stderr: '', url: '' })).toBe('vibey -w status exited 3.');
  });
});

describe('PortableTimer', () => {
  it('waits with the platform setTimeout and reads the wall clock', async () => {
    const timer = new PortableTimer();
    const before = timer.monotonic();
    await timer.sleep(1);
    expect(timer.monotonic()).toBeGreaterThanOrEqual(before);
  });
});

describe('the command line on the workflows', () => {
  const env = { PATH: '/usr/bin' };

  it('sends one command line as vibey --workflows, with vibey -w its whole wait and a minute more', async () => {
    const runner = new FakeProcessRunner().on(['--workflows', 'status'], { code: 0, stdout: '{"phase": "BUILD"}', stderr: RAN });
    const vibey = new LocalProcessTransport(runner, '/bin/vibey', env);
    expect(vibey.workflows).toBe(false);
    expect(await vibey.runOnWorkflows(['status', '--json'])).toEqual({ exitCode: 0, stdout: '{"phase": "BUILD"}', stderr: '', url: 'https://github.com/o/r/actions/runs/7' });
    expect(runner.calls[0]).toEqual({ command: '/bin/vibey', args: ['--workflows', 'status', '--json'], options: { env, timeoutMs: 61 * 60_000 } });
  });

  it("passes a poll, a timeout and a folder on as vibey -w's own settings", async () => {
    const runner = new FakeProcessRunner().on(['--workflows'], { code: 5 });
    const vibey = new VibeyCli(runner, 'vibey', env, undefined, { cwd: () => '/repo' });
    expect((await vibey.runOnWorkflows(['gates'], { pollMs: 2000, timeoutMs: 120_000 })).exitCode).toBe(5);
    expect(runner.calls[0]?.options).toEqual({
      env: { ...env, VIBEY_WORKFLOWS_POLL_SECONDS: '2', VIBEY_WORKFLOWS_TIMEOUT_SECONDS: '120' },
      timeoutMs: 180_000,
      cwd: '/repo',
    });
    await vibey.runOnWorkflows(['gates'], { cwd: '/elsewhere' });
    expect(runner.calls[1]?.options.cwd).toBe('/elsewhere');
  });

  it('turns a run it had to stop into 124, and one that never started into an error', async () => {
    const stopped = new FakeProcessRunner().on(['--workflows'], { code: null, timedOut: true, stderr: RAN });
    expect(await new VibeyCli(stopped, 'vibey', env).runOnWorkflows(['status'], { timeoutMs: 60_000 })).toEqual({
      exitCode: 124,
      stdout: '',
      stderr: 'vibey -w: no report from GitHub within 1 minute; the run may still finish: https://github.com/o/r/actions/runs/7\n',
      url: 'https://github.com/o/r/actions/runs/7',
    });
    const missing = new FakeProcessRunner().on(['--workflows'], { code: null, error: 'spawn vibey ENOENT' });
    await expect(new VibeyCli(missing, 'vibey', env).runOnWorkflows(['status'])).rejects.toThrow('vibey --workflows status could not run: spawn vibey ENOENT');
    const killed = new FakeProcessRunner().on(['--workflows'], { code: null, signal: 'SIGKILL' });
    await expect(new VibeyCli(killed, 'vibey', env).runOnWorkflows(['status'])).rejects.toThrow('could not run: signal SIGKILL');
  });

  it('refuses a command line before anything runs', async () => {
    const runner = new FakeProcessRunner();
    const error = (await new VibeyCli(runner, 'vibey', env).runOnWorkflows([]).catch((reason: unknown) => reason)) as VibeyCliError;
    expect(error).toBeInstanceOf(VibeyCliError);
    expect(error.kind).toBe('refused');
    expect(runner.calls).toHaveLength(0);
  });
});

describe('WorkflowsTransport', () => {
  const env = { PATH: '/usr/bin' };

  it('sends every call through the one choke point as vibey --workflows, from the folder it is given', async () => {
    const runner = new FakeProcessRunner().on(['--workflows', 'status', '--json'], { stdout: fixture('vibey-status.json') });
    const vibey = new WorkflowsTransport(runner, '/bin/vibey', env, undefined, { cwd: () => '/repo' });
    expect(vibey.kind).toBe('workflows');
    expect(vibey.workflows).toBe(true);
    expect((await vibey.status()).queue_depth).toEqual({ ready: 2, leased: 1, succeeded: 7 });
    expect(runner.calls[0]).toEqual({ command: '/bin/vibey', args: ['--workflows', 'status', '--json'], options: { env, timeoutMs: 61 * 60_000, cwd: '/repo' } });
  });

  it('asks the remote vibey its version when a command is missing, and names the command line that failed', async () => {
    const runner = new FakeProcessRunner()
      .on(['projects'], { code: 2, stderr: "Error: No such command 'projects'." })
      .on(['--version'], { stdout: 'vibey 2.0.0\n' })
      .on(['status'], { code: 1, stderr: 'vibey -w: GitHub refused' });
    const vibey = new WorkflowsTransport(runner, 'vibey', env, 5000);
    await expect(vibey.projects()).rejects.toThrow('vibey 2.0.0 (vibey) has no "vibey projects" command');
    expect(runner.calls[1]?.args).toEqual(['--workflows', '--version']);
    expect(runner.calls[1]?.options).toEqual({ env, timeoutMs: 5000 });
    await expect(vibey.status()).rejects.toThrow('vibey --workflows status --json failed: vibey -w: GitHub refused');
  });

  it('keeps the local transport local unless it is told otherwise', async () => {
    const runner = new FakeProcessRunner().on(['status'], { stdout: fixture('vibey-status.json') });
    const local = new LocalProcessTransport(runner, 'vibey', env, undefined, { cwd: () => undefined });
    await local.status();
    expect(runner.calls[0]?.args).toEqual(['status', '--json']);
    expect(runner.calls[0]?.options).toEqual({ env, timeoutMs: 60_000 });
  });
});

describe('HubTransport on the workflows', () => {
  const base = 'http://studio.local:8765';
  const route = `${base}/api/v1/workflows/runs`;
  const ok = (body: unknown, status = 200): HttpResponse => ({ status, body: JSON.stringify(body) });
  const queued = ok({ request_id: 'r 1', state: 'queued', url: '', exit_code: null, stdout: '', stderr: '', detail: '' }, 202);
  const hubWith = (http: FakeHttp, clock = new FakeClock()) => new HubTransport(base, http, 'k3y', 1000, () => 'req-1', clock);
  /** Answers GETs of one request in turn; the last answer repeats. */
  const looks = (http: FakeHttp, answers: (HttpResponse | Error)[]): FakeHttp =>
    http.route('GET', `${route}/r%201`, () => {
      const next = (answers.length > 1 ? answers.shift() : answers[0]) as HttpResponse | Error;
      if (next instanceof Error) {
        throw next;
      }
      return next;
    });

  it('sends the command line, looks again every poll until it is done, and hands back what it printed', async () => {
    const sent: unknown[] = [];
    const http = new FakeHttp().route('POST', route, (body) => {
      sent.push(body);
      return queued;
    });
    looks(http, [ok({ state: 'running', url: 'https://gh/run/7' }), ok({ state: 'done', url: 'https://gh/run/7', exit_code: 0, stdout: '{}', stderr: '' })]);
    const clock = new FakeClock();
    const updates: WorkflowsUpdate[] = [];
    const result = await hubWith(http, clock).runOnWorkflows(['status', '--json'], { onUpdate: (update) => updates.push(update) });
    expect(result).toEqual({ exitCode: 0, stdout: '{}', stderr: '', url: 'https://gh/run/7' });
    expect(sent).toEqual([{ argv: ['status', '--json'] }]);
    expect(updates.map((update) => update.state)).toEqual(['queued', 'running', 'done']);
    expect(clock.mono).toBe(20_000);
    expect(http.requests.every((request) => request.headers?.authorization === 'Bearer k3y')).toBe(true);
  });

  it('hands back a failed run as vibey -w does: 1, with the reason on stderr', async () => {
    const http = looks(new FakeHttp().route('POST', route, ok({ request_id: 'r 1', state: 'queued' })), [ok({ state: 'failed', detail: 'the runner was cancelled', url: 'u' })]);
    expect(await hubWith(http).runOnWorkflows(['status'], { pollMs: 1000 })).toEqual({ exitCode: 1, stdout: '', stderr: 'vibey -w: the runner was cancelled\n', url: 'u' });
  });

  it('stops waiting when the time runs out: 124, never a sleep past the deadline', async () => {
    const http = looks(new FakeHttp().route('POST', route, queued), [ok({ state: 'running', url: 'u' })]);
    const clock = new FakeClock();
    const result = await hubWith(http, clock).runOnWorkflows(['status'], { pollMs: 10_000, timeoutMs: 25_000 });
    expect(result.exitCode).toBe(124);
    expect(result.stderr).toBe('vibey -w: no report from GitHub within 25 seconds; the run may still finish: u\n');
    expect(clock.mono).toBe(25_000);
  });

  it('looks again after a moment the hub turns it away, and stops at any other refusal', async () => {
    const passing = looks(new FakeHttp().route('POST', route, queued), [
      { status: 429, body: '' },
      { status: 502, body: '{"detail": "GitHub could not be read"}' },
      new Error('socket hang up'),
      ok({ state: 'done', exit_code: 7, stdout: '', stderr: 'x' }),
    ]);
    expect((await hubWith(passing).runOnWorkflows(['status'])).exitCode).toBe(7);
    const gone = looks(new FakeHttp().route('POST', route, queued), [{ status: 404, body: '{"detail": "no such request"}' }]);
    const error = (await hubWith(gone).runOnWorkflows(['status']).catch((reason: unknown) => reason)) as HubTransportError;
    expect(error).toBeInstanceOf(HubTransportError);
    expect(error.status).toBe(404);
    expect(error.message).toMatch(/workflows: .* The hub said: no such request$/);
    const garbled = looks(new FakeHttp().route('POST', route, queued), [{ status: 200, body: '<html>' }]);
    await expect(hubWith(garbled).runOnWorkflows(['status'])).rejects.toThrow(/not JSON/);
  });

  it("says why the hub refused the command, in the hub's own words", async () => {
    for (const [status, body, words] of [
      [403, '{"detail": "phone may not run `budget set` there: it needs every scope"}', /does not permit it\..* The hub said: phone may not run `budget set`/],
      [422, '{"detail": [{"msg": "too long"}]}', /could not read the request\.$/],
      [502, '{"detail": "gh: HTTP 404"}', /GitHub refused the hub.* The hub said: gh: HTTP 404$/],
      [503, '{"detail": "workflows are not enabled on this hub"}', /not have this switched on.* The hub said: workflows are not enabled on this hub$/],
    ] as const) {
      const http = new FakeHttp().route('POST', route, { status, body });
      const error = (await hubWith(http).runOnWorkflows(['budget', 'set']).catch((reason: unknown) => reason)) as HubTransportError;
      expect(error.status).toBe(status);
      expect(error.message).toMatch(words);
    }
  });

  it('refuses a command line before sending it, and a reply that names no request', async () => {
    const http = new FakeHttp();
    await expect(hubWith(http).runOnWorkflows(['-w', 'status'])).rejects.toThrow('workflows: Leave out -w');
    expect(http.requests).toHaveLength(0);
    const nameless = new FakeHttp().route('POST', route, ok({ state: 'queued' }, 202));
    await expect(hubWith(nameless).runOnWorkflows(['status'])).rejects.toThrow(`workflows: ${base} took the command but named no request to follow.`);
    const blank = new FakeHttp().route('POST', route, ok({ request_id: '', state: 'queued' }, 202));
    await expect(hubWith(blank).runOnWorkflows(['status'])).rejects.toThrow(/named no request/);
  });

  it("reads a refusal's detail only when it is words", () => {
    expect(HubTransport.detail('{"detail": " nope "}')).toBe('nope');
    expect(HubTransport.detail('{"detail": 3}')).toBe('');
    expect(HubTransport.detail('')).toBe('');
    expect(HubTransport.WORKFLOWS_ROUTE).toBe('/api/v1/workflows/runs');
  });

  it('waits with the portable timer when it is given no clock', async () => {
    const http = looks(new FakeHttp().route('POST', route, queued), [ok({ state: 'done', exit_code: 0 })]);
    expect((await new HubTransport(base, http).runOnWorkflows(['status'], { pollMs: 1 })).exitCode).toBe(0);
  });
});
