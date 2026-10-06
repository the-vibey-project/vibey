// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// vibey on the repository's GitHub workflows from the editor (ADR-0085): the `vibey.workflows`
// setting picks the transport, and `krypton: Run a vibey command on GitHub` (`/workflows`) reads
// its command line the same way from the palette, the panel and @krypton.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { CommandTable, HubTransport, LocalProcessTransport, SlashCommands, WorkflowsCommandLine, WorkflowsTransport } from '@vibey/core';
import type { RawSettings } from '@vibey/core';
import { CoreServices } from '../../src/core/services';
import { SettingsResolver } from '../../src/core/settings';
import { MacStorage } from '../../src/core/storage';
import { FakeClock, FakeHttp, FakeProcessRunner, durable, fixture, json } from './helpers';

const build = (options: { raw?: Partial<RawSettings>; vibey?: boolean; hub?: boolean } = {}) => {
  const home = durable('workflows-');
  const bin = path.join(home, 'bin');
  const workspace = path.join(home, 'workspace');
  fs.mkdirSync(workspace);
  const processes = new FakeProcessRunner();
  const http = new FakeHttp();
  const clock = new FakeClock();
  const core = new CoreServices({
    raw: { stormHome: path.join(home, 'storm'), ...options.raw },
    environ: { PATH: bin, HOME: home },
    platform: 'darwin',
    actor: 'test',
    workspaceRoots: () => [workspace],
    processes,
    http,
    clock,
    isExecutable: (candidate) => options.vibey !== false && candidate === path.join(bin, 'vibey'),
    ...(options.hub === true ? { hub: { url: 'http://studio.local:8765', key: 'k' } } : {}),
  });
  return { core, bin, workspace, processes, http, clock };
};

describe('the vibey.workflows setting', () => {
  it('is off unless it is switched on', () => {
    const resolver = new SettingsResolver({ HOME: '/home/me' }, new MacStorage());
    expect(resolver.resolve({}).workflows).toBe(false);
    expect(resolver.resolve({ workflows: true }).workflows).toBe(true);
  });

  it('keeps vibey local by default', () => {
    const { core } = build();
    expect(core.vibey).toBeInstanceOf(LocalProcessTransport);
    expect(core.vibey?.kind).toBe('local-process');
  });

  it("sends every call to the workflows when it is on, from the open folder, whose repository vibey -w sends to", async () => {
    const { core, bin, workspace, processes } = build({ raw: { workflows: true } });
    expect(core.vibey).toBeInstanceOf(WorkflowsTransport);
    expect(core.vibey?.kind).toBe('workflows');
    processes.on(['--workflows', 'status', '--json'], { stdout: fixture('vibey-status.json') });
    await core.vibey?.status();
    expect(processes.calls[0]?.command).toBe(path.join(bin, 'vibey'));
    expect(processes.calls[0]?.args).toEqual(['--workflows', 'status', '--json']);
    expect(processes.calls[0]?.options.cwd).toBe(workspace);
  });

  it('gives way to a paired hub, and finds nothing to run without a vibey', () => {
    expect(build({ raw: { workflows: true }, hub: true }).core.vibey).toBeInstanceOf(HubTransport);
    expect(build({ raw: { workflows: true }, vibey: false }).core.vibey).toBeUndefined();
  });

  it("waits for a hub's run on the editor's own clock", async () => {
    const { core, http, clock } = build({ hub: true });
    const route = 'http://studio.local:8765/api/v1/workflows/runs';
    const looks = [json({ state: 'running', url: 'https://github.com/o/r/actions/runs/9' }), json({ state: 'done', url: 'https://github.com/o/r/actions/runs/9', exit_code: 0, stdout: 'ok', stderr: '' })];
    http.route('POST', route, json({ request_id: 'r1', state: 'queued' }, 202)).route('GET', `${route}/r1`, () => looks.shift() ?? json({}));
    expect(await core.vibey?.runOnWorkflows(['gates'])).toEqual({ exitCode: 0, stdout: 'ok', stderr: '', url: 'https://github.com/o/r/actions/runs/9' });
    expect(clock.mono).toBe(2 * WorkflowsCommandLine.POLL_MS);
  });
});

describe('krypton: Run a vibey command on GitHub', () => {
  const slash = new SlashCommands();
  const line = new WorkflowsCommandLine();

  it('is in the one command table, as /workflows', () => {
    const spec = CommandTable.byId('vibey.runOnWorkflows');
    expect(spec).toMatchObject({ title: 'Run a vibey command on GitHub', slash: 'workflows', group: 'Connect & look' });
    expect(slash.firstWords()).toContain('workflows');
  });

  it('routes /workflows, typed in the panel or after @krypton, to the command with the rest as its command line', () => {
    const typed = slash.parse('/workflows queue bump "job one" --project p1');
    expect(typed.kind).toBe('command');
    if (typed.kind !== 'command') {
      return;
    }
    expect(typed.spec.id).toBe('vibey.runOnWorkflows');
    expect(line.parse(typed.args)).toEqual(['queue', 'bump', 'job one', '--project', 'p1']);
    // @krypton hands the command and the prompt over apart; the chat joins them back the same way.
    const chat = slash.parse(`/${'workflows'} ${'status --json'}`);
    expect(chat.kind === 'command' && chat.spec.id).toBe('vibey.runOnWorkflows');
    expect(chat.kind === 'command' && line.parse(chat.args)).toEqual(['status', '--json']);
  });

  it('splits what is typed into the input box as a shell would, and refuses what cannot be sent', () => {
    expect(line.parse('status --json')).toEqual(['status', '--json']);
    expect(line.parse('vibey -w answer g1 --raw "{\\"max_dollars\\": 25}"')).toEqual(['answer', 'g1', '--raw', '{"max_dollars": 25}']);
    expect(line.parse('   ')).toMatch(/Say which vibey command/);
    expect(line.parse('vibey --workflows')).toMatch(/Say which vibey command/);
  });
});
