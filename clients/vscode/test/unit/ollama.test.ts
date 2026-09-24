// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import type { OllamaStatus } from '../../src/core/interfaces/ollama-interface';
import { ModelName, OllamaAdvice, OllamaEndpoint, OllamaProbe } from '../../src/core/ollama';
import { ModelPuller, OllamaStartFactsReader, OllamaStartPlanner, PullProgress } from '../../src/core/ollama-lifecycle';
import { FakeHttp, FakeProcessRunner, json } from './helpers';

const root = 'http://127.0.0.1:11434';
const endpoint = new OllamaEndpoint(root);
const live = (): FakeHttp =>
  new FakeHttp()
    .route('GET', `${root}/api/version`, json({ version: '0.34.4' }))
    .route('GET', `${root}/v1/models`, json({ object: 'list', data: [{ id: 'gpt-oss:20b' }, { id: 'qwen3' }, { nope: 1 }, 'bad'] }))
    .route('GET', `${root}/api/ps`, json({ models: [{ name: 'gpt-oss:20b', context_length: 131072 }] }));

describe('OllamaEndpoint', () => {
  it('keeps the root form, whatever it was given', () => {
    expect(new OllamaEndpoint(' http://box:11434/v1/ ').root).toBe('http://box:11434');
    expect(new OllamaEndpoint('https://box/').v1).toBe('https://box/v1');
    expect(endpoint.url('api/ps')).toBe(`${root}/api/ps`);
    expect(endpoint.url('/api/ps')).toBe(`${root}/api/ps`);
    expect(() => new OllamaEndpoint('box:11434')).toThrow('is not an http:// or https:// address');
  });
});

describe('ModelName', () => {
  it('reads an untagged name as :latest, as Ollama does', () => {
    expect(ModelName.normalize('qwen3')).toBe('qwen3:latest');
    expect(ModelName.normalize('hf.co/org/model:Q4')).toBe('hf.co/org/model:Q4');
    expect(ModelName.normalize('registry:5000/model')).toBe('registry:5000/model:latest');
    expect(ModelName.same('qwen3', 'qwen3:latest')).toBe(true);
    expect(ModelName.same('gpt-oss:20b', 'gpt-oss:120b')).toBe(false);
  });
});

describe('OllamaProbe', () => {
  it('reports a ready model with the window it loaded, from the family own endpoints', async () => {
    const status = await new OllamaProbe(live(), endpoint).status('gpt-oss:20b', 32768);
    expect(status).toEqual({
      root,
      model: 'gpt-oss:20b',
      contextWindow: 32768,
      reachable: true,
      version: '0.34.4',
      modelPresent: true,
      modelSource: '/v1/models',
      loaded: { name: 'gpt-oss:20b', contextLength: 131072 },
      contextCheck: 'ok',
    });
  });

  it('says a window is too small when qwenloop would plan past it', async () => {
    const status = await new OllamaProbe(live(), endpoint).status('gpt-oss:20b', 262144);
    expect(status.contextCheck).toBe('too-small');
  });

  it("knows the window only once the model is loaded, and matches Ollama's :latest", async () => {
    const http = live().route('GET', `${root}/api/ps`, json({ models: [{ model: 'qwen3:latest' }, { name: 3 }, null, 'x'] }));
    const status = await new OllamaProbe(http, endpoint).status('qwen3', 32768);
    expect(status.modelPresent).toBe(true);
    expect(status.loaded).toEqual({ name: 'qwen3:latest' });
    expect(status.contextCheck).toBe('unknown');
  });

  it('falls back to /api/tags, and says when neither lists models', async () => {
    const tags = live()
      .route('GET', `${root}/v1/models`, json({}, 404))
      .route('GET', `${root}/api/tags`, json({ models: [{ name: 'gpt-oss:20b' }] }));
    expect((await new OllamaProbe(tags, endpoint).status('gpt-oss:20b', 1)).modelSource).toBe('/api/tags');
    const neither = live()
      .route('GET', `${root}/v1/models`, json({ data: 'not a list' }))
      .route('GET', `${root}/api/tags`, new Error('reset'));
    const status = await new OllamaProbe(neither, endpoint).status('gpt-oss:20b', 1);
    expect(status.reachable).toBe(true);
    expect(status.modelPresent).toBeUndefined();
    expect(status.error).toContain('listed no models');
  });

  it('reports an unreachable server, and a server that answers badly', async () => {
    const down = await new OllamaProbe(new FakeHttp(), endpoint).status('gpt-oss:20b', 1);
    expect(down.reachable).toBe(false);
    expect(down.error).toContain('ECONNREFUSED');
    const odd = new FakeHttp().route('GET', `${root}/api/version`, json({}, 500));
    expect((await new OllamaProbe(odd, endpoint).version()).error).toBe(`${root}/api/version answered HTTP 500`);
    const nameless = new FakeHttp().route('GET', `${root}/api/version`, { status: 200, body: 'not json' });
    expect((await new OllamaProbe(nameless, endpoint).version()).version).toBe('unknown');
    const listy = new FakeHttp().route('GET', `${root}/api/version`, { status: 200, body: '["0.12.0"]' });
    expect((await new OllamaProbe(listy, endpoint).version()).version).toBe('unknown');
  });

  it('treats a failing or odd /api/ps as nothing loaded', async () => {
    const failing = live().route('GET', `${root}/api/ps`, new Error('reset'));
    expect((await new OllamaProbe(failing, endpoint).status('gpt-oss:20b', 1)).contextCheck).toBe('unknown');
    const refused = live().route('GET', `${root}/api/ps`, json({}, 500));
    expect(await new OllamaProbe(refused, endpoint).loaded()).toEqual([]);
    const shapeless = live().route('GET', `${root}/api/ps`, json({ models: 'none' }));
    expect(await new OllamaProbe(shapeless, endpoint).loaded()).toEqual([]);
  });

  it("reads a model's abilities from POST /api/show", async () => {
    const http = new FakeHttp().route('POST', `${root}/api/show`, json({ capabilities: ['completion', 'tools', 'thinking', 7] }));
    expect(await new OllamaProbe(http, endpoint).capabilities('gpt-oss:20b')).toEqual(['completion', 'tools', 'thinking']);
    expect(http.requests[0]?.body).toEqual({ model: 'gpt-oss:20b' });
    const missing = new FakeHttp().route('POST', `${root}/api/show`, json({ error: 'not found' }, 404));
    expect(await new OllamaProbe(missing, endpoint).capabilities('x')).toBeUndefined();
    expect(await new OllamaProbe(new FakeHttp(), endpoint).capabilities('x')).toBeUndefined();
  });
});

describe('OllamaAdvice', () => {
  const advice = new OllamaAdvice();
  const base: OllamaStatus = { root, model: 'gpt-oss:20b', contextWindow: 65536, reachable: true, version: '0.34.4', modelPresent: true, contextCheck: 'ok' };

  it('says what to do, in plain words, for each state', () => {
    const down = { ...base, reachable: false, error: 'refused' };
    expect(advice.summary(down)).toBe(`Ollama is not running at ${root}`);
    expect(advice.advice(down, 'darwin').join(' ')).toContain('Start Ollama');
    const unlisted = { ...base, modelPresent: undefined, error: 'no list' };
    expect(advice.summary(unlisted)).toContain('could not be read');
    expect(advice.advice(unlisted, 'linux')).toEqual(['Ollama answered, but its list of models could not be read: no list.']);
    const missing = { ...base, modelPresent: false };
    expect(advice.summary(missing)).toContain('not downloaded');
    expect(advice.advice(missing, 'linux').join(' ')).toContain('Download the model');
    expect(advice.summary(base)).toBe('Ollama 0.34.4 is running and gpt-oss:20b is ready');
    expect(advice.advice(base, 'darwin')).toEqual([]);
  });

  it('gives the fix for a too-small window on each platform', () => {
    const small: OllamaStatus = { ...base, contextCheck: 'too-small', loaded: { name: 'gpt-oss:20b', contextLength: 8192 } };
    expect(advice.summary(small)).toBe('gpt-oss:20b is loaded with a 8,192-token window, smaller than the 65,536 tasks need');
    expect(advice.advice(small, 'darwin').join(' ')).toContain('launchctl setenv OLLAMA_CONTEXT_LENGTH 65536');
    expect(advice.advice(small, 'linux').join(' ')).toContain('Environment="OLLAMA_CONTEXT_LENGTH=65536"');
    expect(advice.advice(small, 'other')).toContain('Start Ollama with OLLAMA_CONTEXT_LENGTH=65536 in its environment.');
    expect(advice.summary({ ...small, loaded: undefined })).toContain('an unknown number of');
  });
});

describe('PullProgress', () => {
  it('adds up every layer and says when it is done', () => {
    const progress = new PullProgress();
    expect(progress.accept('{"status":"pulling manifest"}')).toEqual({ status: 'pulling manifest', completedBytes: 0, totalBytes: 0, done: false });
    progress.accept('{"status":"pulling a","digest":"sha256:a","total":100,"completed":50}');
    const update = progress.accept('{"status":"pulling b","digest":"sha256:b","total":100}');
    expect(update.percent).toBe(25);
    expect(progress.accept('{"digest":"sha256:c"}').status).toBe('working');
    expect(progress.accept('{"status":"success"}').done).toBe(true);
    expect(progress.accept('[]').status).toBe('working');
  });

  it('carries an error line, and a line that is not JSON', () => {
    const progress = new PullProgress();
    expect(progress.accept('{"error":"file does not exist"}')).toMatchObject({ status: 'error', error: 'file does not exist' });
    expect(progress.accept('garbage').error).toContain('not JSON: garbage');
  });
});

describe('ModelPuller', () => {
  it('pulls through /api/pull and reports progress', async () => {
    const http = new FakeHttp();
    http.lines = ['{"status":"pulling a","digest":"a","total":10,"completed":10}', '{"status":"success"}'];
    const updates: number[] = [];
    const outcome = await new ModelPuller(http, endpoint).pull('gpt-oss:20b', (update) => updates.push(update.percent ?? -1));
    expect(outcome).toEqual({ ok: true, fallbackCommand: 'ollama pull gpt-oss:20b' });
    expect(updates).toEqual([100, 100]);
    expect(http.requests[0]).toEqual({ method: 'POST', url: `${root}/api/pull`, body: { model: 'gpt-oss:20b', stream: true } });
  });

  it('fails plainly, with the terminal command to try instead', async () => {
    const puller = (setup: (http: FakeHttp) => void) => {
      const http = new FakeHttp();
      setup(http);
      return new ModelPuller(http, endpoint).pull('x', () => undefined);
    };
    expect(await puller((http) => (http.linesError = new Error('socket hang up')))).toEqual({ ok: false, error: 'socket hang up', fallbackCommand: 'ollama pull x' });
    expect((await puller((http) => (http.lines = ['{"error":"no such model"}']))).error).toBe('no such model');
    expect((await puller((http) => ((http.lines = ['{"status":"success"}']), (http.lineStatus = 500)))).error).toBe('Ollama answered HTTP 500');
    expect((await puller((http) => (http.lines = ['{"status":"pulling"}']))).error).toContain('before Ollama reported success');
  });

  it("knows the catalogue's download sizes", () => {
    expect(ModelPuller.sizeHint('gpt-oss:20b')).toBe('about 14 GB');
    expect(ModelPuller.sizeHint('mystery')).toBeUndefined();
  });
});

describe('OllamaStartPlanner', () => {
  const planner = new OllamaStartPlanner();
  const facts = { platform: 'darwin' as const, appPath: '/Applications/Ollama.app', appExists: true, systemdUnit: false };

  it('never starts a second server', () => {
    expect(planner.plan(facts, true).kind).toBe('already-running');
  });

  it('opens the app on macOS, else ollama serve', () => {
    expect(planner.plan(facts, false)).toMatchObject({ kind: 'launch', command: 'open', args: ['-a', '/Applications/Ollama.app'] });
    expect(planner.plan({ ...facts, appExists: false, ollamaPath: '/usr/local/bin/ollama' }, false)).toMatchObject({
      kind: 'launch',
      command: '/usr/local/bin/ollama',
      args: ['serve'],
    });
    expect(planner.plan({ ...facts, appExists: false }, false).kind).toBe('impossible');
  });

  it('shows the systemd command on Linux when the unit exists', () => {
    expect(planner.plan({ ...facts, platform: 'linux', appExists: false, systemdUnit: true }, false)).toMatchObject({
      kind: 'terminal',
      commandLine: 'sudo systemctl start ollama',
    });
    expect(planner.plan({ ...facts, platform: 'linux', appExists: false, ollamaPath: '/usr/bin/ollama' }, false).kind).toBe('launch');
  });
});

describe('OllamaStartFactsReader', () => {
  it('reads the app on macOS and the systemd unit on Linux', async () => {
    const runner = new FakeProcessRunner().on(['systemctl'], { code: 0 });
    expect(await new OllamaStartFactsReader('darwin', () => true, runner).read('/Applications/Ollama.app', '/bin/ollama')).toEqual({
      platform: 'darwin',
      appPath: '/Applications/Ollama.app',
      appExists: true,
      systemdUnit: false,
      ollamaPath: '/bin/ollama',
    });
    expect(await new OllamaStartFactsReader('darwin', () => true, runner).read('', undefined)).toMatchObject({ appExists: false });
    expect(await new OllamaStartFactsReader('linux', () => true, runner).read('/x', undefined)).toMatchObject({ appExists: false, systemdUnit: true });
    const noUnit = new FakeProcessRunner().on(['systemctl'], { code: 1 });
    expect(await new OllamaStartFactsReader('linux', () => false, noUnit).read('/x', undefined)).toMatchObject({ systemdUnit: false });
  });
});
