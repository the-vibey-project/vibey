// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { CatalogueParser, DegradedCatalogue } from '@vibey/core';
import { Doctor, type DoctorDependencies } from '@vibey/core';
import { EngineCommand } from '../../src/core/engine-command';
import { ForbiddenEnvironment } from '../../src/core/environment';
import { LocalRunners } from '@vibey/core';
import type { Catalogue, CatalogueEngine } from '@vibey/core';
import type { OllamaProbeInterface, OllamaStatus } from '@vibey/core';
import type { RunRequest } from '@vibey/core';
import type { RawSettings } from '@vibey/core';
import type { VolatileHit } from '@vibey/core';
import { OllamaAdvice } from '@vibey/core';
import { NodeHttpClient } from '../../src/core/http-client';
import { NodeProcessRunner } from '../../src/core/process-runner';
import { CoreServices } from '../../src/core/services';
import { ExecutableLocator, SettingsResolver } from '../../src/core/settings';
import { MacStorage } from '../../src/core/storage';
import { RandomIds, SystemClock, TaskNaming } from '../../src/core/support';
import { FakeClock, FakeHttp, FakeProcessRunner, SequentialIds, durable, fixture, json, scratch } from './helpers';

const CATALOGUE = new CatalogueParser().parse(JSON.parse(fixture('vibey-loops.json')));
const engineOf = (id: string): CatalogueEngine => CATALOGUE.loops.flatMap((loop) => loop.engines).find((engine) => engine.engine_id === id) as CatalogueEngine;
const ROOT = 'http://127.0.0.1:11434';

/** Ollama ready with gpt-oss:20b downloaded, and loaded with `loaded` tokens when given. */
function ollama(http: FakeHttp, loaded?: number): FakeHttp {
  return http
    .route('GET', `${ROOT}/api/version`, json({ version: '0.12.3' }))
    .route('GET', `${ROOT}/v1/models`, json({ data: [{ id: 'gpt-oss:20b' }] }))
    .route('GET', `${ROOT}/api/ps`, json({ models: loaded === undefined ? [] : [{ name: 'gpt-oss:20b', context_length: loaded }] }));
}

class ScriptedProbe implements OllamaProbeInterface {
  /** What POST /api/show says the model can do; undefined when it says nothing. */
  abilities: readonly string[] | undefined = ['completion', 'tools', 'thinking'];

  constructor(private readonly answer: Partial<OllamaStatus>) {}

  async version(): Promise<{ readonly version?: string }> {
    return { version: '0.12.3' };
  }

  async models(): Promise<{ readonly names: readonly string[]; readonly source: string }> {
    return { names: [], source: '/v1/models' };
  }

  async loaded(): Promise<readonly []> {
    return [];
  }

  async capabilities(): Promise<readonly string[] | undefined> {
    return this.abilities;
  }

  async status(model: string, contextWindow: number): Promise<OllamaStatus> {
    return { root: ROOT, model, contextWindow, reachable: true, version: '0.12.3', contextCheck: 'unknown', ...this.answer };
  }
}

describe('Doctor', () => {
  const doctor = (overrides: Partial<DoctorDependencies> = {}, present = ['git', 'gptossloop', 'vibey', 'vibey-skills'], processes = new FakeProcessRunner()) => {
    const home = scratch('vibey-doctor-');
    const settings = new SettingsResolver({ HOME: home }, new MacStorage()).resolve({ stormHome: home });
    const executable = new Set(present.map((name) => `/opt/bin/${name}`));
    return new Doctor({
      settings,
      platform: 'darwin',
      gate: { inspect: () => [], enforce: () => undefined },
      locator: new ExecutableLocator({ PATH: '/opt/bin' }, (candidate) => executable.has(candidate)),
      processes,
      environment: { PATH: '/opt/bin' },
      probe: new ScriptedProbe({ modelPresent: true, modelSource: '/v1/models', loaded: { name: 'gpt-oss:20b', contextLength: 32768 }, contextCheck: 'ok' }),
      advice: new OllamaAdvice(),
      catalogue: async () => CATALOGUE,
      environ: { PATH: '/opt/bin', VIBEY_PG_URL: 'postgresql://x', PGPASSWORD: 'x' },
      forbidden: ForbiddenEnvironment.MODEL_SESSION,
      paidDeclared: () => false,
      runner: LocalRunners.GPTOSSLOOP,
      ...overrides,
    });
  };
  const versions = (): FakeProcessRunner =>
    new FakeProcessRunner()
      .on(['/opt/bin/git', '--version'], { stdout: 'git version 2.47.0\n' })
      .on(['/opt/bin/gptossloop', '--version'], { stdout: 'gptossloop 0.3.0\n' })
      .on(['/opt/bin/vibey', '--version'], { stdout: 'vibey 3.0.0\nextra line\n' })
      .on(['/opt/bin/vibey-skills', '--version'], { stderr: 'vibey-skills 1.2.0\n' });

  it('passes a ready machine, naming each program with where it was found and what version it is', async () => {
    const checks = await doctor({}, undefined, versions()).run();
    expect(checks.map((check) => [check.name, check.status])).toEqual([
      ['storm home', 'pass'],
      ['git', 'pass'],
      ['gptossloop', 'pass'],
      ['vibey', 'pass'],
      ['vibey commands', 'pass'],
      ['vibey-skills', 'pass'],
      ['loops', 'pass'],
      ['Ollama', 'pass'],
      ['model', 'pass'],
      ['context window', 'pass'],
      ['model abilities', 'info'],
      ['environment', 'pass'],
      ['paid loop', 'info'],
    ]);
    const detail = Object.fromEntries(checks.map((check) => [check.name, check.detail]));
    expect(detail.git).toBe('git version 2.47.0 at /opt/bin/git (from PATH)');
    expect(detail.gptossloop).toBe('gptossloop 0.3.0 at /opt/bin/gptossloop (from PATH)');
    expect(detail.vibey).toBe('vibey 3.0.0 at /opt/bin/vibey (from PATH)');
    expect(detail['vibey-skills']).toBe('vibey-skills 1.2.0 at /opt/bin/vibey-skills (from PATH)');
    expect(detail['vibey commands']).toBe('vibey has projects, gates, loops, budget');
    expect(detail.loops).toBe('vibey loops: sovereignloop (gptossloop); paidloop (claudeloop, codexloop, cursorloop, agyloop)');
    expect(detail.Ollama).toBe(`Ollama 0.12.3 at ${ROOT} (from the default)`);
    expect(detail.model).toBe('gpt-oss:20b is downloaded (/v1/models; from the default)');
    expect(detail['context window']).toBe('gpt-oss:20b is loaded with 32,768 tokens; tasks plan for 32,768');
    expect(detail['model abilities']).toBe('completion, tools, thinking; no vision, so no image menu');
    expect(detail.environment).toBe('2 variable(s) never reach a model: PGPASSWORD, VIBEY_PG_URL');
    expect(detail['paid loop']).toBe('Not declared: everything runs on your own computer (sovereignloop).');
    expect(Doctor.failed(checks)).toBe(false);
    expect(Doctor.render(checks.slice(0, 2))).toBe(`[ok  ] storm home: ${checks[0]?.detail}\n[ok  ] git: git version 2.47.0 at /opt/bin/git (from PATH)`);
  });

  it('says what is missing or wrong, with steps a beginner can follow', async () => {
    const processes = new FakeProcessRunner()
      .on(['/opt/bin/gptossloop', '--version'], { code: 1, stderr: 'ImportError: no module named qwenloop\n' })
      .on(['/opt/bin/vibey-skills', '--version'], { code: 2 })
      .on(['/opt/bin/vibey', '--version'], { code: null, error: 'spawn EACCES' });
    const hit: VolatileHit = { name: 'storm home', path: '/tmp/storm', resolved: '/private/tmp/storm', location: '/private/tmp', why: 'emptied at restart' };
    const checks = await doctor(
      {
        gate: { inspect: () => [hit], enforce: () => undefined },
        catalogue: async () => DegradedCatalogue.sovereign('gpt-oss:20b', 'vibey was not found, so the loop and model picker is limited.'),
        probe: new ScriptedProbe({ reachable: false, error: 'connect ECONNREFUSED 127.0.0.1:11434' }),
        environ: { PATH: '/opt/bin' },
        paidDeclared: () => true,
      },
      ['gptossloop', 'vibey', 'vibey-skills'],
      processes,
    ).run();
    const byName = new Map(checks.map((check) => [check.name, check]));
    expect(byName.get('storm home')).toMatchObject({ status: 'fail', detail: expect.stringContaining('is under /private/tmp: emptied at restart') as unknown as string });
    expect(byName.get('git')).toEqual({
      name: 'git',
      status: 'fail',
      detail: 'git was not found on PATH (looked in PATH)',
      fix: ['Install git: https://git-scm.com/downloads'],
    });
    expect(byName.get('gptossloop')?.detail).toBe('/opt/bin/gptossloop (from PATH) did not answer --version: ImportError: no module named qwenloop');
    expect(byName.get('vibey')).toMatchObject({ status: 'warn', detail: '/opt/bin/vibey (from PATH) did not answer --version: spawn EACCES' });
    expect(byName.has('vibey commands')).toBe(false);
    expect(byName.get('vibey-skills')).toMatchObject({ status: 'info', detail: '/opt/bin/vibey-skills (from PATH) did not answer --version: exit 2' });
    expect(byName.get('loops')).toEqual({ name: 'loops', status: 'warn', detail: 'vibey was not found, so the loop and model picker is limited.' });
    expect(byName.get('Ollama')).toMatchObject({ status: 'fail', detail: `${ROOT}: connect ECONNREFUSED 127.0.0.1:11434` });
    expect(byName.get('Ollama')?.fix?.length).toBeGreaterThan(0);
    expect(byName.has('model')).toBe(false);
    expect(byName.get('environment')?.detail).toBe('nothing in your environment is held back from the model');
    expect(byName.get('paid loop')?.detail).toBe('Declared: paid engines may run when you choose paidloop, within your budgets.');
    expect(Doctor.failed(checks)).toBe(true);
    expect(Doctor.render(checks)).toContain('[FAIL] git: git was not found on PATH (looked in PATH)\n         -> Install git: https://git-scm.com/downloads');
    expect(Doctor.render(checks)).toContain('[warn] loops:');
    expect(Doctor.render(checks)).toContain('[info] vibey-skills:');
  });

  it('names the vibey commands an older vibey lacks, and the release that adds them', async () => {
    const processes = versions().on(['projects', '--help'], { code: 2 }).on(['budget', '--help'], { code: 2 });
    const check = (await doctor({}, undefined, processes).run()).find((each) => each.name === 'vibey commands');
    expect(check).toEqual({
      name: 'vibey commands',
      status: 'warn',
      detail: 'this vibey lacks projects, budget; they ship in vibey 3.0.0 (added after 2.1.0)',
      fix: ['Point vibey.cliPath at a newer vibey, or install one: pip install --upgrade vibey'],
    });
  });

  it("judges the model and its window by what Ollama says, and says when it has not said", async () => {
    const ollamaChecks = async (answer: Partial<OllamaStatus>, abilities: { readonly list: readonly string[] | undefined } = { list: ['completion'] }) => {
      const probe = new ScriptedProbe(answer);
      probe.abilities = abilities.list;
      const checks = await doctor({ probe }, undefined, versions()).run();
      return Object.fromEntries(checks.filter((check) => ['model', 'context window', 'model abilities'].includes(check.name)).map((check) => [check.name, check]));
    };
    const missing = await ollamaChecks({ modelPresent: false, modelSource: '/v1/models' });
    expect(missing.model).toMatchObject({ status: 'fail' });
    expect(missing).not.toHaveProperty('context window');
    const small = await ollamaChecks({ modelPresent: true, modelSource: '/api/tags', loaded: { name: 'gpt-oss:20b', contextLength: 8192 }, contextCheck: 'too-small' });
    expect(small['context window']).toMatchObject({ status: 'warn' });
    const unknown = await ollamaChecks({ modelPresent: true, modelSource: '/v1/models', contextCheck: 'unknown' }, { list: undefined });
    expect(unknown['context window']).toEqual({
      name: 'context window',
      status: 'info',
      detail: 'unknown until gpt-oss:20b is loaded (it loads at the first task); tasks plan for 32,768 tokens',
    });
    expect(unknown['model abilities']?.detail).toBe('Ollama did not say what the model can do');
    expect((await ollamaChecks({ modelPresent: true, contextCheck: 'unknown' }, { list: [] }))['model abilities']?.detail).toBe(
      'none listed; no vision, so no image menu',
    );
    expect((await ollamaChecks({ modelPresent: true, contextCheck: 'unknown' }, { list: ['completion', 'vision'] }))['model abilities']?.detail).toBe('completion, vision');
  });

  it('checks the program of the engine that runs by default, gptossloop, and says it ships with vibey', async () => {
    const checks = await doctor({}, ['git', 'qwenloop', 'vibey', 'vibey-skills'], versions()).run();
    expect(checks.find((check) => check.name === 'gptossloop')).toEqual({
      name: 'gptossloop',
      status: 'fail',
      detail: 'gptossloop was not found on PATH (looked in PATH)',
      fix: ['gptossloop ships with vibey: pip install vibey', 'Or point the vibey.gptossloopPath setting at it.'],
    });
    // A runner named as another default is the one checked, under its own setting.
    const qwen = await doctor({ runner: LocalRunners.QWENLOOP }, ['git', 'qwenloop', 'vibey', 'vibey-skills'], versions().on(['/opt/bin/qwenloop', '--version'], { stdout: 'qwenloop 0.3.0\n' })).run();
    expect(qwen.find((check) => check.name === 'qwenloop')).toMatchObject({ status: 'pass', detail: 'qwenloop 0.3.0 at /opt/bin/qwenloop (from PATH)' });
    expect(qwen.some((check) => check.name === 'gptossloop')).toBe(false);
  });

  it('lists a loop with every engine switched off as such', async () => {
    const off: Catalogue = { ...CATALOGUE, loops: CATALOGUE.loops.map((loop) => ({ ...loop, engines: loop.engines.map((engine) => ({ ...engine, enabled: false })) })) };
    const checks = await doctor({ catalogue: async () => off }, undefined, versions()).run();
    expect(checks.find((check) => check.name === 'loops')?.detail).toBe('vibey loops: sovereignloop (none switched on); paidloop (none switched on)');
  });
});

describe('CoreServices', () => {
  const build = (options: { present?: string[]; raw?: Partial<RawSettings>; platform?: string; environ?: Record<string, string> } = {}) => {
    // The real durability gate is wired in: the storm home must be somewhere a restart keeps.
    const home = durable('services-');
    const bin = path.join(home, 'bin');
    const workspace = path.join(home, 'workspace');
    fs.mkdirSync(workspace);
    const present = new Set((options.present ?? ['git', 'gptossloop', 'qwenloop', 'vibey', 'vibey-skills']).map((name) => path.join(bin, name)));
    const processes = new FakeProcessRunner();
    const http = new FakeHttp();
    const clock = new FakeClock();
    const environ = { PATH: bin, HOME: home, GIT_DIR: '/elsewhere/.git', VIBEY_PG_URL: 'postgresql://vibey@localhost/vibey', ...options.environ };
    const core = new CoreServices({
      raw: { stormHome: path.join(home, 'storm'), ...options.raw },
      environ,
      platform: options.platform ?? 'darwin',
      actor: 'vibey-vscode test',
      workspaceRoots: () => [workspace],
      processes,
      http,
      clock,
      ids: new SequentialIds(),
      isExecutable: (candidate) => present.has(candidate),
    });
    return { core, home, bin, workspace, processes, http, clock, environ };
  };

  it('puts the core together once, for the editor and the CLI alike', () => {
    const { core, home, bin } = build();
    expect(core.platform).toBe('darwin');
    expect(build({ platform: 'linux' }).core.platform).toBe('linux');
    expect(build({ platform: 'freebsd' }).core.platform).toBe('other');
    expect(core.settings.stormHome.path).toBe(path.join(home, 'storm'));
    expect(core.settings.stateDir).toBe(path.join(home, 'storm', '.vibey-vscode'));
    // Tools no model drives keep vibey's own settings; only git plumbing is taken out.
    expect(core.toolEnvironment).toEqual({ PATH: bin, HOME: home, VIBEY_PG_URL: 'postgresql://vibey@localhost/vibey' });
    expect(core.vibey).toBeDefined();
    expect(core.skills).toBeDefined();
    const bare = build({ present: [] }).core;
    expect(bare.vibey).toBeUndefined();
    expect(bare.skills).toBeUndefined();
    expect(core.loop()).toBe('sovereignloop');
    expect(core.withSettings({ loop: 'paidloop' }).loop()).toBe('paidloop');
    const journal = core.journalFor(path.join(home, 'Docs Batch'), path.join(home, 'repo'));
    expect(journal).toMatch(new RegExp(`^${core.settings.stateDir}/batches/docs-batch-[0-9a-f]{10}\\.jsonl$`));
    expect(core.journalFor(path.join(home, 'Docs Batch'), path.join(home, 'repo'))).toBe(journal);
    expect(core.journalFor(path.join(home, 'Docs Batch'), path.join(home, 'other'))).not.toBe(journal);
  });

  it('uses the real process runner, HTTP client, clock and ids unless given others', () => {
    const home = durable('defaults-');
    const core = new CoreServices({ raw: { stormHome: home }, environ: { PATH: '' }, platform: 'linux', actor: 'test', workspaceRoots: () => [] });
    expect(core.processes).toBeInstanceOf(NodeProcessRunner);
    expect(core.http).toBeInstanceOf(NodeHttpClient);
    expect(core.clock).toBeInstanceOf(SystemClock);
    expect(core.ids).toBeInstanceOf(RandomIds);
    core.history.applied('r1', 'merged into main');
    const line = fs.readFileSync(path.join(core.settings.stateDir, 'runs.jsonl'), 'utf8');
    expect(JSON.parse(line)).toMatchObject({ type: 'run.applied', run_id: 'r1', detail: 'merged into main' });
  });

  it('reads vibey loops once until asked again, and says plainly when there is no vibey', async () => {
    const { core, processes } = build();
    processes.on(['loops', '--json'], { stdout: fixture('vibey-loops.json') });
    const first = await core.catalogue();
    expect(first.source).toBe('vibey');
    expect(await core.catalogue()).toBe(first);
    expect(processes.calls.filter((call) => call.args.includes('loops'))).toHaveLength(1);
    await core.catalogue(true);
    expect(processes.calls.filter((call) => call.args.includes('loops'))).toHaveLength(2);
    const degraded = await build({ present: ['git', 'gptossloop'] }).core.catalogue();
    expect(degraded.source).toBe('degraded');
    expect(degraded.notice).toContain('vibey was not found');
  });

  it("hands each run its services: the selector, a slot per machine or paid engine, what Ollama holds, and the person's config", async () => {
    const { core, http, home, environ } = build();
    const services = await core.runServices();
    expect((await core.runServices()).selector).toBe(services.selector);
    expect(services.environ).toBe(environ);
    const gptossloop = engineOf('gptossloop');
    const qwenloop = engineOf('qwenloop');
    const local = services.lockFor(gptossloop, 'local');
    expect(local.tryAcquire('test')).toEqual({ acquired: true });
    expect(fs.existsSync(core.settings.modelLockPath)).toBe(true);
    local.release();
    const paid = services.lockFor(engineOf('claudeloop'), 'paid');
    paid.tryAcquire('test');
    expect(fs.existsSync(path.join(core.settings.stateDir, 'locks', 'claudeloop'))).toBe(true);
    paid.release();
    expect(await services.resident()).toEqual([]);
    http.route('GET', `${ROOT}/api/ps`, json({ models: [{ name: 'gpt-oss:20b', context_length: 32768 }] }));
    expect(await services.resident()).toEqual(['gpt-oss:20b']);
    expect(services.command(gptossloop)).toBeInstanceOf(EngineCommand);
    expect(services.command(qwenloop)).toBeInstanceOf(EngineCommand);
    expect(services.command(engineOf('claudeloop'))).toBe('claudeloop cannot run: claudeloop was not found on PATH. Install it, or choose another engine.');
    // Each runner's program is named by its own setting; vibey.qwenloopPath still finds qwenloop.
    const declared = await build({ raw: { gptossloopPath: '/opt/g/gptossloop', qwenloopPath: '/opt/q/qwenloop' } }).core.runServices();
    expect(declared.command(gptossloop)).toBe(
      'gptossloop cannot run: /opt/g/gptossloop is not an executable file. It ships with vibey (pip install vibey), or set vibey.gptossloopPath.',
    );
    expect(declared.command(qwenloop)).toBe(
      'qwenloop cannot run: /opt/q/qwenloop is not an executable file. It ships with vibey (pip install vibey), or set vibey.qwenloopPath.',
    );
    expect(services.runners).toBe(LocalRunners.FAMILY);
    expect(services.userConfig(LocalRunners.GPTOSSLOOP)).toBeUndefined();
    expect(services.userConfig(LocalRunners.QWENLOOP)).toBeUndefined();
    // Each runner's own <PREFIX>_CONFIG, never the other's.
    const gptossConfig = path.join(home, 'gptossloop.toml');
    const qwenConfig = path.join(home, 'qwenloop.toml');
    fs.writeFileSync(gptossConfig, 'context_window = 8192\n');
    fs.writeFileSync(qwenConfig, 'context_window = 4096\n');
    const both = await build({ environ: { GPTOSSLOOP_CONFIG: gptossConfig, QWENLOOP_CONFIG: qwenConfig } }).core.runServices();
    expect(both.userConfig(LocalRunners.GPTOSSLOOP)).toEqual({ path: gptossConfig, text: 'context_window = 8192\n' });
    expect(both.userConfig(LocalRunners.QWENLOOP)).toEqual({ path: qwenConfig, text: 'context_window = 4096\n' });
    const onlyQwen = await build({ environ: { QWENLOOP_CONFIG: qwenConfig } }).core.runServices();
    expect(onlyQwen.userConfig(LocalRunners.GPTOSSLOOP)).toBeUndefined();
    // Unset, each looks where platformdirs puts its own: <config dir>/<runner>/config.toml.
    const built = build();
    const platformDefault = path.join(built.home, 'Library', 'Application Support', 'gptossloop', 'config.toml');
    fs.mkdirSync(path.dirname(platformDefault), { recursive: true });
    fs.writeFileSync(platformDefault, 'max_turns = 12\n');
    const defaults = await built.core.runServices();
    expect(defaults.userConfig(LocalRunners.GPTOSSLOOP)).toEqual({ path: platformDefault, text: 'max_turns = 12\n' });
    expect(defaults.userConfig(LocalRunners.QWENLOOP)).toBeUndefined();
    expect(services.paidDeclared()).toBe(false);
    core.budgets.declarePaid({ scope: 'day', dollars: 5 });
    expect(services.paidDeclared()).toBe(true);
    await core.catalogue(true);
    expect((await core.runServices()).selector).not.toBe(services.selector);
  });

  it('starts a task through the queue, with the real selector and slot, and records it', async () => {
    const { core, processes, http, bin, home } = build();
    const repository = path.join(home, 'repo');
    processes
      .on(['loops', '--json'], { stdout: fixture('vibey-loops.json') })
      .on(['rev-parse', '--show-toplevel'], { stdout: `${repository}\n` })
      .on(['rev-parse', '--verify'], { stdout: `${'a'.repeat(40)}\n` });
    processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    http.route('GET', `${ROOT}/api/ps`, json({ models: [] }));
    const request: RunRequest = {
      task: 'Add a line.',
      title: 'Add a line',
      directory: repository,
      inPlace: false,
      baseRef: '',
      loop: 'sovereignloop',
      effort: 'LOW',
      baseEffort: 'LOW',
      engine: 'auto',
      contextWindow: 32768,
      commitMessage: 'docs: add a line',
      slugSource: 'Add a line',
      origin: 'ask',
    };
    const run = await core.start(request);
    expect(core.queue.snapshot().running).toContain(run);
    const record = await run.result;
    expect(record).toMatchObject({ outcome: 'wound-down', engine: 'gptossloop', max_turns: 16 });
    const child = processes.children[0];
    expect(child?.command).toBe(path.join(bin, 'gptossloop'));
    expect(child?.options.env).toMatchObject({ GPTOSSLOOP_BASE_URL: `${ROOT}/v1`, GPTOSSLOOP_MODEL: 'gpt-oss:20b' });
    expect(child?.options.env).not.toHaveProperty('QWENLOOP_BASE_URL');
    expect(child?.options.env).not.toHaveProperty('VIBEY_PG_URL');
    expect(child?.options.env).not.toHaveProperty('GIT_DIR');
    const naming = new TaskNaming();
    expect(child?.options.cwd).toBe(path.join(core.settings.stormHome.path, naming.worktreeName(repository, 'add-a-line', naming.shortId(run.runId))));
    expect(core.history.list()[0]?.record.run_id).toBe(run.runId);
    expect(fs.existsSync(core.settings.modelLockPath)).toBe(false);
  });

  it('checks before a batch that Ollama answers and has the model; a paid batch does not need it', async () => {
    const batch = async (setup: (built: ReturnType<typeof build>) => void, raw: Partial<RawSettings> = {}) => {
      const built = build({ raw });
      setup(built);
      const folder = path.join(built.home, 'tasks');
      fs.mkdirSync(folder);
      fs.writeFileSync(path.join(folder, '01.md'), 'one');
      built.processes.on(['loops', '--json'], { stdout: fixture('vibey-loops.json') });
      built.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
      return built.core.batch().run({
        directory: folder,
        repository: built.home,
        baseRef: '',
        journal: path.join(built.home, 'journal.jsonl'),
        commitType: 'docs',
        contextWindow: 32768,
        loop: built.core.settings.loop,
        effort: 'LOW',
        baseEffort: 'LOW',
        engine: 'auto',
      });
    };
    expect((await batch(() => undefined)).halted).toBe(`Ollama is not answering at ${ROOT}: connect ECONNREFUSED ${ROOT}/api/version`);
    expect(
      (
        await batch(({ http }) => {
          http.route('GET', `${ROOT}/api/version`, json({ version: '0.12.3' })).route('GET', `${ROOT}/v1/models`, json({ data: [{ id: 'qwen3:14b' }] })).route('GET', `${ROOT}/api/ps`, json({ models: [] }));
        })
      ).halted,
    ).toBe('gpt-oss:20b is not downloaded; run: ollama pull gpt-oss:20b');
    expect((await batch(({ http }) => ollama(http))).halted).toBe('the run was stopped');
    expect((await batch(() => undefined, { loop: 'paidloop' })).halted).toMatch(/^an infrastructure error, not a task failure: paidloop is declared-only/);
  });

  it('checks the setup with the same settings and paths', async () => {
    const { core, processes, http } = build();
    ollama(http, 131072);
    processes.on(['--version'], { stdout: 'v1\n' }).on(['loops', '--json'], { stdout: fixture('vibey-loops.json') });
    http.route('POST', `${ROOT}/api/show`, json({ capabilities: ['completion', 'tools'] }));
    const checks = await core.doctor().run();
    expect(Doctor.failed(checks)).toBe(false);
    expect(checks.find((check) => check.name === 'environment')?.detail).toBe('1 variable(s) never reach a model: VIBEY_PG_URL');
  });

  it("follows every lane in the storm home and the open folders, one tracker over every engine's state directory", () => {
    const { core, workspace } = build();
    const at = new FakeClock().now().getTime() / 1000;
    const place = (cwd: string, stateDir: string, id: string): void => {
      const file = path.join(cwd, stateDir, 'runs', id, 'events.jsonl');
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, `${JSON.stringify({ type: 'turn.completed', turn: 1 })}\n`);
      fs.utimesSync(file, at, at);
    };
    place(workspace, '.qwenloop', 'r1');
    place(path.join(core.settings.stormHome.path, 'vscode-repo-task-00000001'), '.claudeloop', 'c1');
    const lanes = core.lanes(CATALOGUE).refresh();
    expect(lanes.map((lane) => [lane.id, lane.engine]).sort()).toEqual([
      ['c1', 'claudeloop'],
      // gptossloop and qwenloop share the runner's .qwenloop records; the default engine names them.
      ['r1', 'gptossloop'],
    ]);
  });
});
