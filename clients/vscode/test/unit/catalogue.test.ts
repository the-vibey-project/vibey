// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import {
  CatalogueError,
  CatalogueParser,
  CatalogueSource,
  DegradedCatalogue,
  Efforts,
  LoopSelector,
  SelectionError,
} from '../../src/core/catalogue';
import type { Catalogue, SelectionRequest } from '../../src/core/interfaces/catalogue-interface';
import { fixture } from './helpers';

const raw = (): Record<string, unknown> => JSON.parse(fixture('vibey-loops.json')) as Record<string, unknown>;
const parse = (value: unknown = raw()): Catalogue => new CatalogueParser().parse(value);
const request = (overrides: Partial<SelectionRequest> = {}): SelectionRequest => ({
  loop: 'sovereignloop',
  effort: 'auto',
  engine: 'auto',
  baseEffort: 'LOW',
  attempt: 1,
  resident: [],
  paidDeclared: false,
  ...overrides,
});

/** A deep copy of the fixture changed by `change`. */
function variant(change: (value: Record<string, any>) => void): Record<string, unknown> {
  const copy = raw() as Record<string, any>;
  change(copy);
  return copy;
}

describe('Efforts', () => {
  it('knows the five levels in order', () => {
    expect(Efforts.is('HIGH')).toBe(true);
    expect(Efforts.is('high')).toBe(false);
    expect(Efforts.is(3)).toBe(false);
    expect(Efforts.rank('TRIVIAL')).toBe(0);
    expect(Efforts.max('LOW', 'HIGH')).toBe('HIGH');
    expect(Efforts.max('MAX', 'LOW')).toBe('MAX');
  });
});

describe('CatalogueParser', () => {
  it('reads the fixture of `vibey loops --json`', () => {
    const catalogue = parse();
    expect(catalogue.source).toBe('vibey');
    expect(catalogue.default_loop).toBe('sovereignloop');
    expect(catalogue.paid_default_engine).toBe('claudeloop');
    expect(catalogue.ladder.build_attempts).toEqual(['LOW', 'LOW', 'STANDARD', 'STANDARD', 'HIGH', 'HIGH']);
    const qwenloop = catalogue.loops[0]?.engines[0];
    expect(qwenloop?.engine_id).toBe('qwenloop');
    expect(qwenloop?.turns_flag).toBe('--max-turns');
    expect(qwenloop?.capabilities.images).toBe(false);
    expect(qwenloop?.capabilities.evidence.images).toContain('read_file');
    const codex = catalogue.loops[1]?.engines.find((engine) => engine.engine_id === 'codexloop');
    expect(codex?.turns_flag).toBeUndefined();
    expect(codex?.supports_cwd_flag).toBe(false);
    const opencode = catalogue.loops[0]?.engines.find((engine) => engine.engine_id === 'opencode');
    expect(opencode?.notes?.join(' ')).toContain('repeals');
    expect(opencode).toMatchObject({ repealed: true, events: { envelope: 'event_type' } });
    expect(catalogue.loops[0]?.engines.find((engine) => engine.engine_id === 'qwenloop')).toMatchObject({ repealed: false, controls: { prompt: null } });
  });

  it('accepts paid_default in place of paid_default_engine, and missing optional fields', () => {
    const catalogue = parse(
      variant((value) => {
        value.paid_default_engine = undefined;
        value.paid_default = 'codexloop';
        delete value.loops[0].engines[0].capabilities.evidence;
        value.loops[0].engines[0].notes = '';
        value.loops[0].engines[0].efforts[0].notes = null;
      }),
    );
    expect(catalogue.paid_default_engine).toBe('codexloop');
    expect(catalogue.loops[0]?.engines[0]?.capabilities.evidence).toEqual({});
    expect(catalogue.loops[0]?.engines[0]?.notes).toBeUndefined();
    expect(catalogue.loops[0]?.engines[0]?.efforts[0]?.notes).toBe('');
  });

  it.each([
    ['the answer', () => [1], 'is not an object'],
    ['loops', (value: Record<string, any>) => (value.loops = {}), 'is not a list'],
    ['default_loop', (value: Record<string, any>) => (value.default_loop = 'thirdloop'), 'not among the loops'],
    ['default_loop', (value: Record<string, any>) => (value.default_loop = 7), 'is not a string'],
    ['loops[0].loop', (value: Record<string, any>) => (value.loops[0].loop = 'fastloop'), 'exactly two loops'],
    ['loops[0].tier', (value: Record<string, any>) => (value.loops[0].tier = 'cloud'), 'neither local nor paid'],
    ['loops[0].default', (value: Record<string, any>) => (value.loops[0].default = 'yes'), 'is not true or false'],
    ['efforts[0]', (value: Record<string, any>) => (value.efforts[0] = 'EXTREME'), 'is not one of'],
    ['ladder.exhausted_after', (value: Record<string, any>) => (value.ladder.exhausted_after = 'six'), 'is not a number'],
    [
      'events.envelope',
      (value: Record<string, any>) => (value.loops[0].engines[0].events.envelope = 'xml'),
      'is none of "type", "event_type+payload" and "event_type"',
    ],
    ['notes', (value: Record<string, any>) => (value.loops[0].engines[0].notes = 5), 'is not a list'],
    ['repealed', (value: Record<string, any>) => (value.loops[0].engines[0].repealed = 'yes'), 'is not true or false'],
    ['capabilities.images', (value: Record<string, any>) => (value.loops[0].engines[0].capabilities.images = 'maybe'), 'is not true or false'],
    ['controls.stop', (value: Record<string, any>) => (value.loops[0].engines[0].controls.stop = [1]), 'is not a string'],
    ['env.auth', (value: Record<string, any>) => (value.loops[0].engines[0].env.auth = 'KEY'), 'is not a list'],
    ['by_effort', (value: Record<string, any>) => (value.loops[0].by_effort.HUGE = []), 'is not one of'],
    ['by_effort', (value: Record<string, any>) => (value.loops[0].by_effort.LOW[0].model = 3), 'is not a string'],
    [
      'evidence',
      (value: Record<string, any>) => (value.loops[0].engines[0].capabilities.evidence = { images: 4 }),
      'is not a string',
    ],
  ])('refuses a wrong %s, naming it', (_label, change, message) => {
    const value = typeof change === 'function' && change.length === 0 ? (change as () => unknown)() : variant(change as (value: Record<string, any>) => void);
    expect(() => parse(value)).toThrow(CatalogueError);
    expect(() => parse(value)).toThrow(message);
  });
});

describe('the #1131 review amendments', () => {
  it("reads an engine's notes as lines, from a list or an older producer's single string", () => {
    const catalogue = parse(
      variant((value) => {
        value.loops[0].engines[0].notes = ['first', '  ', 'second'];
        value.loops[0].engines[1].notes = 'one line';
        value.loops[0].engines[2].notes = null;
      }),
    );
    expect(catalogue.loops[0]?.engines.map((engine) => engine.notes)).toEqual([['first', 'second'], ['one line'], undefined]);
  });

  it('reads an engine a producer from before the repeals lists as not repealed', () => {
    const catalogue = parse(
      variant((value) => {
        for (const engine of value.loops[0].engines) {
          delete engine.repealed;
        }
      }),
    );
    expect(catalogue.loops[0]?.engines.every((engine) => !engine.repealed)).toBe(true);
  });

  it('never chooses a repealed engine in auto mode, even where by_effort lists it', () => {
    const catalogue = parse(
      variant((value) => {
        const opencode = value.loops[0].engines.find((engine: Record<string, any>) => engine.engine_id === 'opencode');
        opencode.enabled = true;
        opencode.base_weight = 100;
        opencode.efforts[1].achieved = 'LOW';
        value.loops[0].by_effort.LOW = [
          { engine_id: 'opencode', model: null, achieved: 'LOW' },
          { engine_id: 'qwenloop', model: 'gpt-oss:20b', achieved: 'LOW' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const picks = [1, 2, 3, 4].map(() => selector.select(request()).engine.engine_id);
    expect(picks).toEqual(['qwenloop', 'qwenloop', 'qwenloop', 'qwenloop']);
  });

  it("still works with a vibey that has no `vibey loops`: sovereignloop, qwenloop, and no prompt box", async () => {
    const older = await new CatalogueSource(
      async () => {
        throw new Error('vibey 2.1.0 (/usr/local/bin/vibey) has no "vibey loops" command. It ships in vibey 3.0.0.');
      },
      new CatalogueParser(),
      'gpt-oss:20b',
    ).load();
    expect(older).toMatchObject({ source: 'degraded', default_loop: 'sovereignloop' });
    expect(older.notice).toContain('has no "vibey loops" command');
    const selection = new LoopSelector(older).select(request({ effort: 'auto', attempt: 1 }));
    expect(selection).toMatchObject({ loop: 'sovereignloop', tier: 'local', model: 'gpt-oss:20b' });
    expect(selection.engine).toMatchObject({ engine_id: 'qwenloop', repealed: false, controls: { prompt: null } });
    expect(selection.engine.notes).toHaveLength(1);
  });
});

describe('DegradedCatalogue', () => {
  it('is sovereignloop with qwenloop on the configured model, a notice, and no ladder', () => {
    const catalogue = DegradedCatalogue.sovereign('gpt-oss:20b', 'vibey is too old');
    expect(catalogue.source).toBe('degraded');
    expect(catalogue.notice).toBe('vibey is too old');
    expect(catalogue.loops).toHaveLength(1);
    const engine = catalogue.loops[0]?.engines[0];
    expect(engine?.default_model).toBe('gpt-oss:20b');
    expect(engine?.capabilities.plugins).toBeNull();
    expect(engine?.turns_flag).toBe('--max-turns');
    expect(catalogue.loops[0]?.by_effort.HIGH?.[0]?.engine_id).toBe('qwenloop');
  });
});

describe('CatalogueSource', () => {
  it('parses what vibey prints', async () => {
    const source = new CatalogueSource(async () => raw(), new CatalogueParser(), 'gpt-oss:20b');
    expect((await source.load()).source).toBe('vibey');
  });

  it('degrades, saying why, when vibey is missing or cannot answer', async () => {
    const missing = await new CatalogueSource(undefined, new CatalogueParser(), 'gpt-oss:20b').load();
    expect(missing.source).toBe('degraded');
    expect(missing.notice).toContain('vibey was not found');
    const failing = await new CatalogueSource(
      async () => {
        throw new Error('vibey 2.0.0 has no "vibey loops" command.');
      },
      new CatalogueParser(),
      'gpt-oss:20b',
    ).load();
    expect(failing.notice).toBe('vibey 2.0.0 has no "vibey loops" command. The extension runs sovereignloop with gpt-oss:20b and effort auto.');
  });
});

describe('LoopSelector', () => {
  it('climbs the ladder from the base, never below it, and is exhausted after the last rung', () => {
    const selector = new LoopSelector(parse());
    expect(selector.effortForAttempt('LOW', 1)).toBe('LOW');
    expect(selector.effortForAttempt('LOW', 3)).toBe('STANDARD');
    expect(selector.effortForAttempt('HIGH', 1)).toBe('HIGH');
    expect(() => selector.effortForAttempt('LOW', 0)).toThrow('counted from 1');
    expect(() => selector.effortForAttempt('LOW', 1.5)).toThrow('counted from 1');
    expect(() => selector.effortForAttempt('LOW', 7)).toThrow('exhausted after 6');
  });

  it('uses the base itself when the ladder has no rung for the attempt', () => {
    expect(new LoopSelector(DegradedCatalogue.sovereign('m', 'n')).effortForAttempt('HIGH', 1)).toBe('HIGH');
  });

  it('on auto picks qwenloop for sovereignloop, with the effort projection as the turn limit', () => {
    const selection = new LoopSelector(parse()).select(request());
    expect(selection.engine.engine_id).toBe('qwenloop');
    expect(selection.effort).toBe('LOW');
    expect(selection.effortSource).toBe('auto');
    expect(selection.model).toBe('gpt-oss:20b');
    expect(selection.argv).toEqual(['--max-turns', '16']);
    expect(selection.maxTurns).toBe(16);
    expect(selection.maxTurnsSource).toBe('effort');
    expect(selection.reason).toContain('auto, attempt 1');
  });

  it("lets a task's own turn limit win, and passes --max-turns once", () => {
    const selection = new LoopSelector(parse()).select(request({ effort: 'HIGH', taskMaxTurns: 70, settingMaxTurns: 5 }));
    expect(selection.argv).toEqual(['--max-turns', '70']);
    expect(selection.maxTurnsSource).toBe('task');
    expect(selection.effortSource).toBe('chosen');
    expect(selection.reason).toContain('as you chose');
  });

  it('falls back to the setting only when the effort projects no limit, and says when an engine takes none', () => {
    const degraded = new LoopSelector(DegradedCatalogue.sovereign('gpt-oss:20b', 'old vibey'));
    expect(degraded.select(request({ settingMaxTurns: 30 })).argv).toEqual(['--max-turns', '30']);
    expect(degraded.select(request({ settingMaxTurns: 30 })).maxTurnsSource).toBe('setting');
    expect(degraded.select(request()).maxTurnsSource).toBe('none');
    const paid = new LoopSelector(parse()).select(
      request({ loop: 'paidloop', paidDeclared: true, engine: 'codexloop', taskMaxTurns: 9 }),
    );
    expect(paid.argv).toEqual([]);
    expect(paid.maxTurnsSource).toBe('not supported by this engine');
  });

  it('refuses the paid loop until it is declared, and on auto picks Claude through claudeloop (8.b)', () => {
    const selector = new LoopSelector(parse());
    expect(() => selector.select(request({ loop: 'paidloop' }))).toThrow('declared-only');
    const paid = selector.select(request({ loop: 'paidloop', paidDeclared: true, effort: 'MAX' }));
    expect(paid.engine.engine_id).toBe('claudeloop');
    expect(paid.argv).toEqual(['--preset', 'high', '--effort', 'max']);
    expect(paid.reason).toContain('declared paid default');
  });

  it('turns to the next paid adapter only when claudeloop is not available', () => {
    const catalogue = parse(
      variant((value) => {
        value.loops[1].engines[0].enabled = false;
      }),
    );
    const paid = new LoopSelector(catalogue).select(request({ loop: 'paidloop', paidDeclared: true, effort: 'LOW' }));
    expect(paid.engine.engine_id).toBe('cursorloop');
    expect(paid.reason).toContain('achieves LOW');
  });

  it('takes the nearest engine when none achieves the effort exactly', () => {
    const catalogue = parse(
      variant((value) => {
        value.loops[1].engines[0].enabled = false;
        value.loops[1].engines[2].enabled = false;
        value.loops[1].engines[3].enabled = false;
      }),
    );
    const paid = new LoopSelector(catalogue).select(request({ loop: 'paidloop', paidDeclared: true, effort: 'MAX' }));
    expect(paid.engine.engine_id).toBe('codexloop');
    expect(paid.reason).toContain('nothing achieves MAX exactly');
  });

  it('prefers the engine whose model Ollama already holds, and round-robins by weight otherwise', () => {
    const catalogue = parse(
      variant((value) => {
        const local = value.loops[0];
        local.engines[1].enabled = true;
        local.engines[1].base_weight = 2;
        local.engines[1].efforts[1].achieved = 'LOW';
        local.engines[1].efforts[1].model = 'qwen3:14b';
        local.by_effort.LOW = [
          { engine_id: 'qwenloop', model: 'gpt-oss:20b', achieved: 'LOW' },
          { engine_id: 'claudeloop-local', model: 'qwen3:14b', achieved: 'LOW' },
          { engine_id: 'missing-engine', model: null, achieved: 'LOW' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const resident = selector.select(request({ resident: ['gpt-oss:20b'] }));
    expect(resident.engine.engine_id).toBe('qwenloop');
    expect(resident.reason).toContain('already loaded');
    const picks = [1, 2, 3].map(() => selector.select(request()).engine.engine_id);
    expect(picks).toEqual(['claudeloop-local', 'qwenloop', 'claudeloop-local']);
  });

  it('skips an engine with no model when it looks for a resident one', () => {
    const catalogue = parse(
      variant((value) => {
        value.loops[0].engines[0].default_model = null;
        for (const entry of value.loops[0].engines[0].efforts) {
          entry.model = null;
        }
        value.loops[0].by_effort.LOW = [{ engine_id: 'qwenloop', model: null, achieved: 'LOW' }];
      }),
    );
    const selection = new LoopSelector(catalogue).select(request({ resident: ['gpt-oss:20b'] }));
    expect(selection.engine.engine_id).toBe('qwenloop');
    expect(selection.model).toBeNull();
  });

  it('rotates away from the previous engine when auto effort rises', () => {
    const catalogue = parse(
      variant((value) => {
        const local = value.loops[0];
        local.engines[1].enabled = true;
        local.by_effort.STANDARD = [
          { engine_id: 'qwenloop', model: 'gpt-oss:20b', achieved: 'STANDARD' },
          { engine_id: 'claudeloop-local', model: null, achieved: 'STANDARD' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const rose = selector.select(request({ attempt: 3, previousEngine: 'qwenloop' }));
    expect(rose.engine.engine_id).toBe('claudeloop-local');
    expect(rose.reason).toContain('rotates away from qwenloop');
    const steady = selector.select(request({ attempt: 4, previousEngine: 'claudeloop-local' }));
    expect(steady.reason).not.toContain('rotates');
  });

  it('names an engine, or an engine and model, and refuses what it cannot run', () => {
    const selector = new LoopSelector(parse());
    const local = selector.select(request({ engine: 'qwenloop/qwen3:14b', effort: 'STANDARD' }));
    expect(local.model).toBe('qwen3:14b');
    expect(local.reason).toContain('on qwen3:14b as you chose');
    expect(selector.select(request({ engine: 'qwenloop/' })).model).toBe('gpt-oss:20b');
    const cursor = selector.select(request({ loop: 'paidloop', paidDeclared: true, engine: 'cursorloop/grok', effort: 'LOW' }));
    expect(cursor.effort).toBe('HIGH');
    expect(cursor.effortSource).toBe('model');
    expect(cursor.reason).toContain('set by the model');
    expect(() => selector.select(request({ loop: 'paidloop', paidDeclared: true, engine: 'cursorloop/gpt-9' }))).toThrow(
      'its models are composer-fast, composer, grok-4.5, grok, grok-xhigh',
    );
    expect(() => selector.select(request({ loop: 'paidloop', paidDeclared: true, engine: 'claudeloop/opus' }))).toThrow(
      'does not take a model by name',
    );
    expect(() => selector.select(request({ engine: 'nosuch' }))).toThrow('its engines are qwenloop, claudeloop-local, opencode');
    expect(() => selector.select(request({ engine: 'claudeloop-local' }))).toThrow('switch it on with VIBEY_FEATURE_CLAUDELOOP_LOCAL');
    expect(() => selector.select(request({ engine: 'opencode' }))).toThrow('opencode is repealed by the canon (8.b): it is listed, but it never runs');
    expect(() => selector.select(request({ engine: 'claudeloop-local' }))).toThrow(/switched off; switch it on with /);
    const noSwitch = new LoopSelector(
      parse(
        variant((value) => {
          value.loops[0].engines[1].switch = null;
        }),
      ),
    );
    expect(() => noSwitch.select(request({ engine: 'claudeloop-local' }))).toThrow(/^claudeloop-local is switched off$/);
  });

  it('says when a loop is missing, and why, and when nothing can run an effort', () => {
    const degraded = new LoopSelector(DegradedCatalogue.sovereign('m', 'vibey is 2.0.0'));
    expect(() => degraded.select(request({ loop: 'paidloop', paidDeclared: true }))).toThrow('paidloop is not available: vibey is 2.0.0');
    const trimmed = parse(variant((value) => value.loops.pop()));
    expect(() => new LoopSelector(trimmed).select(request({ loop: 'paidloop', paidDeclared: true }))).toThrow(
      'paidloop is not one of the loops vibey lists',
    );
    const empty = parse(variant((value) => (value.loops[0].by_effort.LOW = [])));
    expect(() => new LoopSelector(empty).select(request())).toThrow(SelectionError);
    const gap = parse(variant((value) => delete value.loops[0].by_effort.LOW));
    expect(() => new LoopSelector(gap).select(request())).toThrow('can run at LOW');
    const noEntry = parse(variant((value) => value.loops[0].engines[0].efforts.splice(1, 1)));
    expect(() => new LoopSelector(noEntry).select(request())).toThrow('qwenloop lists no LOW effort');
  });
});
