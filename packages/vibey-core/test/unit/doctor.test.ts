// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The doctor over fakes of everything it asks: the extension's suite runs it again over the real
// settings, locator and environment rules.
import { describe, expect, it } from 'vitest';
import { CatalogueParser, DegradedCatalogue } from '../../src/catalogue';
import { Doctor, type DoctorDependencies } from '../../src/doctor';
import type { Catalogue } from '../../src/interfaces/catalogue-interface';
import type { OllamaProbeInterface, OllamaStatus } from '../../src/interfaces/ollama-interface';
import type { ResolvedSettings } from '../../src/interfaces/settings-interface';
import type { VolatileHit } from '../../src/interfaces/storage-interface';
import { LocalRunners } from '../../src/local-runner';
import { OllamaAdvice } from '../../src/ollama';
import { FakeProcessRunner, fixture } from './helpers';

const CATALOGUE = new CatalogueParser().parse(JSON.parse(fixture('vibey-loops.json')));
/** The settings the doctor reads, as a machine with nothing configured resolves them. */
const SETTINGS = {
  raw: { gitPath: '', cliPath: '', gptossloopPath: '', qwenloopPath: '', vibeySkillsPath: '' },
  stormHome: { path: '/Users/me/storm', source: 'the default' },
  ollamaSource: 'the default',
  model: 'gpt-oss:20b',
  modelSource: 'the default',
  contextWindow: 32768,
} as unknown as ResolvedSettings;
const ROOT = 'http://127.0.0.1:11434';

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
    const settings = SETTINGS;
    const executable = new Set(present);
    return new Doctor({
      settings,
      platform: 'darwin',
      gate: { inspect: () => [], enforce: () => undefined },
      locator: {
        locate: (name: string) => (executable.has(name) ? { path: `/opt/bin/${name}`, source: 'PATH' } : { source: 'PATH', error: `${name} was not found on PATH` }),
      },
      processes,
      environment: { PATH: '/opt/bin' },
      probe: new ScriptedProbe({ modelPresent: true, modelSource: '/v1/models', loaded: { name: 'gpt-oss:20b', contextLength: 32768 }, contextCheck: 'ok' }),
      advice: new OllamaAdvice(),
      catalogue: async () => CATALOGUE,
      environ: { PATH: '/opt/bin', VIBEY_PG_URL: 'postgresql://x', PGPASSWORD: 'x' },
      forbidden: { forbids: (name: string) => name === 'PGPASSWORD' || name.startsWith('VIBEY_PG'), forbidsPrefix: () => false },
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
      fix: ['Point vibey.cliPath at a newer vibey, or install one: pip install --upgrade vibey-engine'],
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
      fix: ['gptossloop ships with vibey: pip install vibey-engine', 'Or point the vibey.gptossloopPath setting at it.'],
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

