// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { BudgetError, BudgetGuard, BudgetStore, SpendLedger } from '../../src/core/budgets';
import { Capabilities, SkillsContext, SkillsMarketplace } from '../../src/core/capabilities';
import type { EngineCapabilities } from '../../src/core/interfaces/catalogue-interface';
import type { HostFacts } from '../../src/core/interfaces/model-lock-interface';
import { JsonlJournal, JsonlTail } from '../../src/core/jsonl';
import { LocalHost, ModelSlotLock } from '../../src/core/model-lock';
import { FakeClock, FakeProcessRunner, SequentialIds, scratch } from './helpers';

class Host implements HostFacts {
  readonly pid: number = 100;
  readonly host: string = 'this-mac';
  boot = 1_000_000;
  living = new Set<number>([100]);

  bootAt(): number {
    return this.boot;
  }

  alive(pid: number): boolean {
    return this.living.has(pid);
  }
}

/** Another process on the same computer: same host and boot, its own PID. */
function sibling(host: Host, pid: number, alive: (pid: number) => boolean): HostFacts {
  return { pid, host: host.host, bootAt: () => host.boot, alive };
}

describe('ModelSlotLock', () => {
  const owner = (directory: string, value: unknown): void => {
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, 'owner.json'), JSON.stringify(value));
  };

  it('takes a free slot, refuses a held one naming its holder, and frees it', () => {
    const directory = path.join(scratch(), 'nested', '.ollama-lock');
    const clock = new FakeClock();
    const host = new Host();
    const lock = new ModelSlotLock(directory, clock, host);
    expect(lock.tryAcquire('first')).toEqual({ acquired: true });
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'owner.json'), 'utf8'))).toEqual({
      pid: 100,
      host: 'this-mac',
      bootAt: 1_000_000,
      startedAt: '2026-09-24T12:00:00.000Z',
      purpose: 'first',
    });
    const other = new ModelSlotLock(directory, clock, sibling(host, 200, (pid) => pid === 100));
    expect(other.tryAcquire('second')).toMatchObject({ acquired: false, holder: { pid: 100, host: 'this-mac', purpose: 'first' } });
    lock.release();
    lock.release();
    expect(fs.existsSync(directory)).toBe(false);
    expect(other.tryAcquire('second')).toEqual({ acquired: true });
  });

  it('breaks a lock whose holder is gone, or from an earlier boot, but never one from another host', () => {
    const root = scratch();
    const host = new Host();
    const clock = new FakeClock();
    owner(path.join(root, 'dead'), { pid: 9, host: 'this-mac', bootAt: host.boot, startedAt: 'x', purpose: 'crashed' });
    expect(new ModelSlotLock(path.join(root, 'dead'), clock, host).tryAcquire('me')).toEqual({ acquired: true });
    host.living.add(7);
    owner(path.join(root, 'rebooted'), { pid: 7, host: 'this-mac', bootAt: host.boot - 3_600_000, startedAt: 'x', purpose: 'old' });
    expect(new ModelSlotLock(path.join(root, 'rebooted'), clock, host).tryAcquire('me')).toEqual({ acquired: true });
    owner(path.join(root, 'foreign'), { pid: 9, host: 'another-mac', bootAt: 0, startedAt: 'x', purpose: 'theirs' });
    expect(new ModelSlotLock(path.join(root, 'foreign'), clock, host).tryAcquire('me')).toMatchObject({
      acquired: false,
      holder: { host: 'another-mac' },
    });
  });

  it("never breaks another tool's bare mkdir lock, or one whose owner it cannot read, however old", () => {
    const root = scratch();
    const clock = new FakeClock();
    // vibey-gh's DirectoryLock and storm shell tooling hold an empty directory while they run.
    fs.mkdirSync(path.join(root, 'bare'));
    clock.wall = Date.now() + 48 * 3_600_000;
    expect(new ModelSlotLock(path.join(root, 'bare'), clock, new Host()).tryAcquire('me')).toEqual({ acquired: false });
    expect(fs.existsSync(path.join(root, 'bare'))).toBe(true);
    fs.mkdirSync(path.join(root, 'unreadable'));
    fs.writeFileSync(path.join(root, 'unreadable', 'owner.json'), '{"pid": "not a number"}');
    expect(new ModelSlotLock(path.join(root, 'unreadable'), clock, new Host()).tryAcquire('me')).toEqual({ acquired: false });
  });

  it('waits its turn, saying who holds the slot, and can be stopped while it waits', async () => {
    const directory = path.join(scratch(), 'lock');
    const clock = new FakeClock();
    const host = new Host();
    const holder = new ModelSlotLock(directory, clock, host);
    holder.tryAcquire('holder');
    const waiter = new ModelSlotLock(directory, clock, sibling(host, 300, () => true));
    const heard: string[] = [];
    const slot = await waiter.acquire(
      'waiter',
      (who) => {
        heard.push(who?.purpose ?? 'nobody');
        if (heard.length === 2) {
          holder.release();
        }
      },
      10,
    );
    expect(heard).toEqual(['holder', 'holder']);
    expect(clock.monotonic()).toBe(20);
    slot.dispose();
    expect(fs.existsSync(directory)).toBe(false);
    holder.tryAcquire('holder again');
    const stop = new AbortController();
    await expect(waiter.acquire('waiter', () => stop.abort(), 10, stop.signal)).rejects.toThrow('stopped while waiting for the model');
  });

  it('reports a lock it cannot make rather than treating it as held', () => {
    const tooLong = path.join(scratch(), 'x'.repeat(300));
    expect(() => new ModelSlotLock(tooLong, new FakeClock(), new Host()).tryAcquire('me')).toThrow(/ENAMETOOLONG/);
  });

  it("knows this computer's own facts", () => {
    const local = new LocalHost();
    expect(local.pid).toBe(process.pid);
    expect(local.alive(process.pid)).toBe(true);
    expect(local.alive(2_147_483_646)).toBe(false);
    // PID 1 always exists, and belongs to the system: EPERM still means alive.
    expect(local.alive(1)).toBe(true);
    expect(local.bootAt()).toBeLessThan(Date.now());
  });
});

describe('Capabilities', () => {
  const capabilities = new Capabilities();
  const engine = (overrides: Partial<EngineCapabilities>): EngineCapabilities => ({
    images: false,
    files: true,
    paste_text: true,
    paste_images: false,
    plugins: 'skills-context',
    mcp: null,
    evidence: {},
    ...overrides,
  });

  it('shows no image menu for gpt-oss:20b, which reports no vision', () => {
    const menu = capabilities.menu(engine({ images: true, paste_images: true }), 'local', ['completion', 'tools', 'thinking']);
    expect(menu).toEqual({
      attachImage: false,
      pasteImage: false,
      attachFile: true,
      pasteText: true,
      plugins: 'skills-context',
      notes: ['No image menu: the model reports completion, tools, thinking, not vision.'],
    });
  });

  it('shows the image menu only when the engine takes images and the model sees', () => {
    expect(capabilities.menu(engine({ images: true, paste_images: true }), 'local', ['vision'])).toMatchObject({ attachImage: true, pasteImage: true, notes: [] });
    expect(capabilities.menu(engine({ images: true }), 'paid', undefined).attachImage).toBe(true);
    expect(capabilities.menu(engine({ images: true }), 'local', undefined).notes).toEqual(['No image menu: Ollama has not said whether the model can see images.']);
    expect(capabilities.menu(engine({ images: true }), 'local', []).notes).toEqual(['No image menu: the model reports no capabilities, not vision.']);
    expect(capabilities.menu(engine({ images: null }), 'paid', undefined).notes).toEqual(['No image menu: whether this engine takes images is not verified.']);
    expect(capabilities.menu(engine({}), 'paid', undefined).notes).toEqual(['No image menu: this engine does not take images.']);
  });

  it('offers a plugin menu only for a kind it knows, and files only when verified; pasting text always', () => {
    expect(capabilities.menu(engine({ plugins: 'claude-plugins' }), 'paid', undefined).plugins).toBe('claude-plugins');
    expect(capabilities.menu(engine({ plugins: null, files: null }), 'paid', undefined)).toMatchObject({ attachFile: false, pasteText: true });
    expect(capabilities.menu(engine({ plugins: 'mystery' }), 'paid', undefined)).not.toHaveProperty('plugins');
  });
});

describe('SkillsMarketplace', () => {
  it("reads the repository's own marketplace, and nothing when there is none", () => {
    const repository = scratch();
    const marketplace = new SkillsMarketplace();
    expect(marketplace.plugins(repository)).toEqual([]);
    fs.mkdirSync(path.join(repository, '.claude-plugin'));
    fs.writeFileSync(path.join(repository, '.claude-plugin', 'marketplace.json'), '{"plugins": "none"}');
    expect(marketplace.plugins(repository)).toEqual([]);
    fs.writeFileSync(
      path.join(repository, '.claude-plugin', 'marketplace.json'),
      JSON.stringify({ plugins: [{ name: 'frontend-design', description: 'Design', category: 'design' }, { name: 'bare' }, { description: 'nameless' }, 5] }),
    );
    expect(marketplace.plugins(repository)).toEqual([
      { name: 'frontend-design', description: 'Design', category: 'design' },
      { name: 'bare', description: '' },
    ]);
  });
});

describe('SkillsContext', () => {
  const request = { title: 't', objective: 'o', plugins: [] as string[] };
  const build = (runner: FakeProcessRunner, directory = scratch()): SkillsContext =>
    new SkillsContext(runner, '/bin/vibey-skills', { PATH: '/usr/bin' }, directory, 500, new SequentialIds());
  const errorOf = async (runner: FakeProcessRunner): Promise<string> => {
    const packet = await build(runner).packet(request);
    return packet.ok ? 'no error' : packet.error;
  };

  it("builds the index once, then asks vibey-skills for a packet the way vibey's skills_context does", async () => {
    const runner = new FakeProcessRunner()
      .on(['index', 'build'], (args) => {
        const index = args[args.indexOf('--output') + 1] as string;
        fs.mkdirSync(index, { recursive: true });
        fs.writeFileSync(path.join(index, 'manifest.json'), '{}');
        fs.writeFileSync(path.join(index, 'index.sqlite3'), '');
        return {};
      })
      .on(['packet'], (args) => {
        fs.writeFileSync(args[args.indexOf('--output') + 1] as string, '# Context\n');
        fs.writeFileSync(args[args.indexOf('--manifest') + 1] as string, '{"status": "complete"}');
        return { code: 2 };
      });
    const directory = scratch();
    const skills = build(runner, directory);
    const packet = await skills.packet({ title: 'Rewrite', objective: 'Rewrite the README', plugins: ['frontend-design'] });
    expect(packet).toMatchObject({ ok: true, markdown: '# Context\n', status: 'complete', plugins: ['frontend-design'] });
    const call = runner.calls.at(-1);
    expect(call?.options).toMatchObject({ cwd: directory, env: { PATH: '/usr/bin' }, timeoutMs: 120_000 });
    const sent = JSON.parse(fs.readFileSync(call?.args[2] as string, 'utf8')) as Record<string, unknown>;
    expect(sent).toEqual({
      schema_version: 1,
      title: 'Rewrite',
      objective: 'Rewrite the README',
      phase: 'build',
      job_kind: 'vscode.ask',
      commands: [],
      maximum_context_tokens: 1000,
      ranking_mode: 'deterministic',
      required_plugins: ['frontend-design'],
    });
    expect(call?.args.slice(5, 7)).toEqual(['--budget', '1000']);
    await skills.packet(request);
    expect(runner.calls.filter((each) => each.args.includes('build'))).toHaveLength(1);
    expect(runner.calls.some((each) => each.args.includes('inspect'))).toBe(true);
    expect(JSON.parse(fs.readFileSync(runner.calls.at(-1)?.args[2] as string, 'utf8'))).not.toHaveProperty('required_plugins');
  });

  it('rebuilds an index that no longer inspects, and reports what fails in its own words', async () => {
    const directory = scratch();
    const index = path.join(directory, 'index');
    fs.mkdirSync(index, { recursive: true });
    fs.writeFileSync(path.join(index, 'manifest.json'), '{}');
    fs.writeFileSync(path.join(index, 'index.sqlite3'), '');
    const broken = new FakeProcessRunner().on(['inspect'], { code: 1 }).on(['build'], { code: 1, stderr: 'no plugins\n' });
    expect(await build(broken, directory).packet(request)).toEqual({ ok: false, error: 'vibey-skills could not build its index: no plugins' });
    expect(await errorOf(new FakeProcessRunner().on(['build'], { code: null, error: 'spawn ENOENT' }))).toBe('vibey-skills could not build its index: spawn ENOENT');
    expect(await errorOf(new FakeProcessRunner().on(['build'], { code: 9 }))).toBe('vibey-skills could not build its index: exit 9');
    expect(await errorOf(new FakeProcessRunner().on(['packet'], { code: 1, stderr: 'bad request' }))).toBe('vibey-skills packet failed: bad request');
    expect(await errorOf(new FakeProcessRunner().on(['packet'], { code: null, error: 'killed' }))).toBe('vibey-skills packet failed: killed');
    expect(await errorOf(new FakeProcessRunner().on(['packet'], { code: 7 }))).toBe('vibey-skills packet failed: exit 7');
  });

  it('reads a packet with no manifest, or one that gives no status, as such', async () => {
    expect(await build(new FakeProcessRunner()).packet(request)).toMatchObject({ ok: true, markdown: '', status: 'no manifest' });
    const statusless = new FakeProcessRunner().on(['packet'], (args) => {
      fs.writeFileSync(args[args.indexOf('--manifest') + 1] as string, '{"status": 3}');
      return {};
    });
    expect(await build(statusless).packet(request)).toMatchObject({ ok: true, status: 'unknown' });
  });

  it("keeps a packet's budget within vibey's own bounds", async () => {
    const runner = new FakeProcessRunner();
    await new SkillsContext(runner, '/s', {}, scratch(), 1_000_000, new SequentialIds()).packet(request);
    expect(runner.calls.at(-1)?.args).toContain('32000');
  });
});

describe('budgets', () => {
  const setup = (): { store: BudgetStore; spend: SpendLedger; guard: BudgetGuard; clock: FakeClock; directory: string } => {
    const directory = scratch();
    const clock = new FakeClock();
    const store = new BudgetStore(directory, new JsonlJournal(path.join(directory, 'budget-journal.jsonl')), clock, new SequentialIds(), 'me');
    const spend = new SpendLedger(new JsonlJournal(path.join(directory, 'spend.jsonl')), new JsonlTail());
    return { store, spend, guard: new BudgetGuard(store, spend, clock), clock, directory };
  };
  const entry = (overrides: Record<string, unknown> = {}) =>
    ({
      run_id: 'r1',
      at: '2026-09-24T12:00:00.000Z',
      loop: 'paidloop',
      engine_id: 'claudeloop',
      turns: 1,
      input_tokens: 1000,
      output_tokens: 100,
      dollars: 1.5,
      minutes: 2,
      ...overrides,
    }) as Parameters<SpendLedger['record']>[0];

  it('adds, edits and removes budgets, journaling every change', () => {
    const { store, directory } = setup();
    expect(store.list()).toEqual([]);
    const added = store.add({ scope: 'day', loop: 'paidloop', caps: { dollars: 5 } });
    expect(added).toEqual({ id: '00000001', scope: 'day', loop: 'paidloop', caps: { dollars: 5 } });
    const edited = store.edit(added.id, { caps: { dollars: 10, turns: 30 }, label: 'daily paid' });
    expect(edited).toEqual({ id: added.id, scope: 'day', loop: 'paidloop', caps: { dollars: 10, turns: 30 }, label: 'daily paid' });
    expect(store.list()).toEqual([edited]);
    expect(store.remove(added.id)).toEqual(edited);
    expect(store.list()).toEqual([]);
    const journal = new JsonlJournal(path.join(directory, 'budget-journal.jsonl')).readAll().records;
    expect(journal.map((line) => line.action)).toEqual(['add', 'edit', 'remove']);
    expect(journal[0]).toMatchObject({ at: '2026-09-24T12:00:00.000Z', actor: 'me', old: null, new: added });
    expect(journal[1]).toMatchObject({ old: { caps: { dollars: 5 } }, new: { caps: { dollars: 10, turns: 30 } } });
    expect(journal[2]).toMatchObject({ old: edited, new: null });
    const kept = store.add({ scope: 'month', loop: 'any', caps: { minutes: 600 } });
    const changed = store.add({ scope: 'run', loop: 'sovereignloop', caps: { turns: 40 } });
    store.edit(changed.id, { caps: { turns: 80 } });
    expect(store.list()).toEqual([kept, { ...changed, caps: { turns: 80 } }]);
    store.remove(changed.id);
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'budgets.json'), 'utf8'))).toEqual({ version: 1, budgets: [kept] });
    expect(fs.existsSync(path.join(directory, 'budgets.json.writing'))).toBe(false);
  });

  it('refuses a budget that is not one, and an id that does not exist', () => {
    const { store } = setup();
    expect(() => store.add({ scope: 'week' as 'day', loop: 'any', caps: { dollars: 1 } })).toThrow("A budget's scope is run, day or month, not week.");
    expect(() => store.add({ scope: 'day', loop: 'cheap' as 'any', caps: { dollars: 1 } })).toThrow("A budget's loop is sovereignloop, paidloop or any, not cheap.");
    expect(() => store.add({ scope: 'day', loop: 'any', caps: {} })).toThrow('A budget needs at least one cap: dollars, turns or minutes.');
    expect(() => store.add({ scope: 'day', loop: 'any', caps: { dollars: -1 } })).toThrow('dollars must be a positive number, not -1.');
    expect(() => store.add({ scope: 'day', loop: 'any', caps: { dollars: Number.POSITIVE_INFINITY } })).toThrow('dollars must be a positive number');
    expect(() => store.add({ scope: 'day', loop: 'any', caps: { turns: 1.5 } })).toThrow('turns must be a positive whole number, not 1.5.');
    expect(() => store.add({ scope: 'day', loop: 'any', caps: { minutes: 'x' as unknown as number } })).toThrow(BudgetError);
    expect(() => store.edit('nope', {})).toThrow('There is no budget nope.');
    expect(() => store.remove('nope')).toThrow('There is no budget nope.');
    expect(store.add({ scope: 'run', loop: 'any', caps: { dollars: 0.25, minutes: 30 } }).caps).toEqual({ dollars: 0.25, minutes: 30 });
  });

  it('reads a damaged budgets file as an error, and a file with no list as none', () => {
    const { store, directory } = setup();
    fs.writeFileSync(path.join(directory, 'budgets.json'), '{"budgets": "x", "paid": null}');
    expect(store.list()).toEqual([]);
    expect(store.paid()).toBeUndefined();
    fs.writeFileSync(path.join(directory, 'budgets.json'), '{broken');
    expect(() => store.list()).toThrow(`${path.join(directory, 'budgets.json')} cannot be read`);
    expect(() => store.list()).toThrow(BudgetError);
  });

  it('declares the paid loop with a cap, or with none only after a second confirmation', () => {
    const { store, directory } = setup();
    expect(() => store.declarePaid({ noCap: true, confirmed: false })).toThrow('Declaring the paid loop with no dollar cap needs a second, explicit confirmation.');
    expect(store.paid()).toBeUndefined();
    const capped = store.declarePaid({ scope: 'month', dollars: 50 });
    expect(capped).toEqual({ declared_at: '2026-09-24T12:00:00.000Z', budget_id: '00000001' });
    expect(store.list()).toEqual([{ id: '00000001', scope: 'month', loop: 'paidloop', caps: { dollars: 50 }, label: 'paid month cap' }]);
    expect(store.paid()).toEqual(capped);
    const uncapped = store.declarePaid({ noCap: true, confirmed: true });
    expect(uncapped).toEqual({ declared_at: '2026-09-24T12:00:00.000Z', no_cap_confirmed: true });
    expect(store.paid()).toEqual(uncapped);
    const actions = new JsonlJournal(path.join(directory, 'budget-journal.jsonl')).readAll().records.map((line) => line.action);
    expect(actions).toEqual(['add', 'paid.declared', 'paid.declared']);
  });

  it('sums spend from a byte-offset watermark, and knows tokens per turn', () => {
    const { spend, directory } = setup();
    expect(spend.perTurn('claudeloop')).toBeUndefined();
    spend.record(entry());
    spend.record(entry({ run_id: 'r2', engine_id: 'codexloop', dollars: 0.5 }));
    expect(spend.totals({})).toEqual({ dollars: 2, turns: 2, minutes: 4, input_tokens: 2000, output_tokens: 200, runs: 2 });
    fs.appendFileSync(path.join(directory, 'spend.jsonl'), '{"no": "run"}\n{"run_id": "r5"}\n');
    spend.record(entry({ turns: 'x', input_tokens: null, output_tokens: 0, dollars: 'free', minutes: undefined, at: '2026-09-25T00:00:00.000Z' }));
    expect(spend.totals({ runId: 'r1' })).toEqual({ dollars: 1.5, turns: 1, minutes: 2, input_tokens: 1000, output_tokens: 100, runs: 1 });
    expect(spend.totals({ engineId: 'codexloop' }).dollars).toBe(0.5);
    expect(spend.totals({ loop: 'sovereignloop' }).runs).toBe(0);
    expect(spend.totals({ loop: 'any' }).runs).toBe(2);
    expect(spend.totals({ loop: 'paidloop', since: new Date('2026-09-24T18:00:00Z') })).toMatchObject({ runs: 1, turns: 0, dollars: 0 });
    expect(spend.perTurn('claudeloop')).toEqual({ input: 1000, output: 100 });
  });

  it('starts over when the spend file is replaced by a shorter one', () => {
    const { spend, directory } = setup();
    spend.record(entry({ dollars: 9 }));
    spend.record(entry({ run_id: 'r2', dollars: 9 }));
    expect(spend.totals({}).dollars).toBe(18);
    fs.writeFileSync(path.join(directory, 'spend.jsonl'), `${JSON.stringify(entry({ dollars: 1 }))}\n`);
    expect(spend.totals({})).toMatchObject({ dollars: 1, runs: 1 });
  });

  it("applies vibey's BudgetLedger rule: exhausted at the cap, refused when the projection passes it", () => {
    const { store, spend, guard } = setup();
    const run = store.add({ scope: 'run', loop: 'any', caps: { turns: 3 } });
    const day = store.add({ scope: 'day', loop: 'paidloop', engine_id: 'claudeloop', caps: { dollars: 2 }, label: 'claude day' });
    store.add({ scope: 'month', loop: 'sovereignloop', caps: { minutes: 1000 } });
    const context = { loop: 'paidloop', engineId: 'claudeloop', runId: 'r1' };
    expect(guard.exhausted(context)).toBeUndefined();
    expect(guard.wouldExceed({ ...context, projected: { dollars: 1.9 } })).toBeUndefined();
    expect(guard.wouldExceed({ ...context, projected: { dollars: 2.5, turns: 1 } })).toEqual({
      budget: day,
      cap: 'dollars',
      limit: 2,
      spent: 0,
      projected: 2.5,
      message: 'The daily budget claude day allows $2.00; $0.00 is spent and this run could take $2.50 more.',
    });
    spend.record(entry({ turns: 3 }));
    expect(guard.exhausted(context)).toEqual({
      budget: run,
      cap: 'turns',
      limit: 3,
      spent: 3,
      message: `The per-run budget ${run.id} is used up: 3 turns of 3 turns.`,
    });
    expect(guard.exhausted({ ...context, engineId: 'cursorloop', runId: 'r9' })).toBeUndefined();
    expect(guard.wouldExceed({ loop: 'sovereignloop', engineId: 'qwenloop', runId: 'r9', projected: { minutes: 2000 } })?.message).toMatch(
      /^The monthly budget \w+ allows 1000 minutes; 0 minutes is spent and this run could take 2000 minutes more\.$/,
    );
  });
});
