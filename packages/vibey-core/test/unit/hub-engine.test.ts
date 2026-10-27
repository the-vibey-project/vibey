// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { HubEngine } from '../../src/hub-engine';
import { VibeyCliError } from '../../src/vibey-cli';
import { FakeProcessRunner } from './helpers';

const engine = (runner: FakeProcessRunner, cwd?: string): HubEngine => new HubEngine(runner, '/bin/vibey', { PATH: '/usr/bin' }, cwd);

describe('HubEngine (the one hub on this computer, #1186)', () => {
  it('asks vibey hub status, start and stop, always the local vibey, from the folder it was given', async () => {
    const runner = new FakeProcessRunner()
      .on(['hub', 'status'], { stdout: 'http://127.0.0.1:8765/api/v1 (pid 7)\n' })
      .on(['hub', 'start'], { stdout: 'hub started: http://127.0.0.1:8765/api/v1 (pid 9)\n' })
      .on(['hub', 'stop'], { stdout: 'hub stopped (pid 7)\n' });
    const hub = engine(runner, '/home/me');
    expect(await hub.run('status')).toEqual({ action: 'status', running: true, message: 'http://127.0.0.1:8765/api/v1 (pid 7)' });
    expect(await hub.run('start')).toMatchObject({ action: 'start', running: true });
    expect(await hub.run('stop')).toEqual({ action: 'stop', running: false, message: 'hub stopped (pid 7)' });
    expect(runner.calls.map((call) => call.args)).toEqual([['hub', 'status'], ['hub', 'start'], ['hub', 'stop']]);
    expect(runner.calls[0]?.command).toBe('/bin/vibey');
    expect(runner.calls[0]?.options.cwd).toBe('/home/me');
    expect(runner.calls[0]?.options.env).toEqual({ PATH: '/usr/bin' });
    expect(runner.calls.flatMap((call) => call.args)).not.toContain('--workflows');
  });

  it('reads no hub running as an answer, not a failure, and says so when vibey said nothing', async () => {
    const said = new FakeProcessRunner().on(['hub', 'status'], { code: 3, stdout: 'hub is not running\n' });
    expect(await engine(said).run('status')).toEqual({ action: 'status', running: false, message: 'hub is not running' });
    const silent = new FakeProcessRunner().on(['hub', 'status'], { code: 3 });
    expect(await engine(silent).run('status')).toMatchObject({ running: false, message: 'The vibey hub is not running.' });
    expect(silent.calls[0]?.options.cwd).toBeUndefined();
  });

  it('takes vibey sentence from stderr when stdout is empty', async () => {
    const runner = new FakeProcessRunner().on(['hub', 'stop'], { code: 0, stderr: 'a note\n' });
    expect((await engine(runner).run('stop')).message).toBe('a note');
  });

  it('says plainly which vibey lacks the command', async () => {
    const runner = new FakeProcessRunner().on(['hub', 'start'], { code: 2, stderr: "Error: No such command 'start'." });
    const error = (await engine(runner).run('start').catch((caught: unknown) => caught)) as VibeyCliError;
    expect(error).toBeInstanceOf(VibeyCliError);
    expect(error.kind).toBe('missing-command');
    expect(error.message).toContain('has no "vibey hub start" command');
  });

  it('reports a failure with what vibey said, or why it could not run', async () => {
    const said = new FakeProcessRunner().on(['hub', 'start'], { code: 1, stderr: 'the hub exited before it was ready' });
    await expect(engine(said).run('start')).rejects.toThrow('vibey hub start failed: the hub exited before it was ready');
    const gone = new FakeProcessRunner().on(['hub', 'stop'], { code: null, error: 'spawn ENOENT' });
    await expect(engine(gone).run('stop')).rejects.toThrow('vibey hub stop failed: spawn ENOENT');
    const bare = new FakeProcessRunner().on(['hub', 'stop'], { code: 4 });
    await expect(engine(bare).run('stop')).rejects.toThrow('vibey hub stop failed: exit 4');
  });

  it('ensure starts the hub only when none runs', async () => {
    const down = new FakeProcessRunner().on(['hub', 'status'], { code: 3, stdout: 'hub is not running' }).on(['hub', 'start'], { stdout: 'hub started: x' });
    expect((await engine(down).ensure()).message).toBe('hub started: x');
    expect(down.calls.map((call) => call.args[1])).toEqual(['status', 'start']);
    const up = new FakeProcessRunner().on(['hub', 'status'], { stdout: 'x (pid 7)' });
    expect((await engine(up).ensure()).running).toBe(true);
    expect(up.calls.map((call) => call.args[1])).toEqual(['status']);
  });
});
