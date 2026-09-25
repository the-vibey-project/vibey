// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { HubTransport, HubTransportError, LocalProcessTransport } from '../../src/transport';
import { FakeHttp, FakeProcessRunner } from './helpers';

describe('LocalProcessTransport', () => {
  it("is vibey's own command line, through the process runner it is given", async () => {
    const transport = new LocalProcessTransport(new FakeProcessRunner().on(['vibey', '--version'], { stdout: 'vibey 3.0.0\n' }), 'vibey', {});
    expect(transport.kind).toBe('local-process');
    expect(await transport.version()).toBe('vibey 3.0.0');
  });
});

describe('HubTransport', () => {
  const hub = new HubTransport('https://hub.local:8443', new FakeHttp());

  it('knows its address and the document its client is generated from', () => {
    expect(hub.kind).toBe('hub');
    expect(hub.baseUrl).toBe('https://hub.local:8443');
    expect(HubTransport.OPENAPI_DOCUMENT).toBe('docs/reference/hub-api.json');
  });

  it('refuses every call plainly until the hub document lands, and never pretends to be a hub', async () => {
    const calls: readonly (readonly [string, () => Promise<unknown>])[] = [
      ['version', () => hub.version()],
      ['projects', () => hub.projects()],
      ['gates', () => hub.gates('p1')],
      ['status', () => hub.status()],
      ['answer', () => hub.answer('g1', { mode: 'defaults' })],
      ['bump', () => hub.bump('j1')],
      ['loops', () => hub.loops()],
      ['budgets', () => hub.budgets()],
      ['setBudget', () => hub.setBudget(undefined, { dollars: 5 })],
      ['clearBudget', () => hub.clearBudget(undefined, 'all')],
      ['cost', () => hub.cost()],
    ];
    for (const [name, call] of calls) {
      const error = await call().then(
        () => undefined,
        (reason: unknown) => reason,
      );
      expect(error, name).toBeInstanceOf(HubTransportError);
      expect((error as Error).name).toBe('HubTransportError');
      expect((error as Error).message).toMatch(new RegExp(`^${name}: the hub transport is not built yet\\..*docs/reference/hub-api\\.json`));
    }
  });
});
