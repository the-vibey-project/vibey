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
import * as fs from 'node:fs';
import * as path from 'node:path';
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

/** The fixture's engine `id` in loop `loop`, to change in a variant. */
function engineIn(value: Record<string, any>, id: string, loop = 0): Record<string, any> {
  return value.loops[loop].engines.find((engine: Record<string, any>) => engine.engine_id === id);
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
  it("is vibey's own golden `vibey loops --json`, byte for byte", () => {
    const golden = path.resolve(__dirname, '..', '..', '..', '..', 'tests', 'cli', 'golden', 'vibey-loops.json');
    expect(fixture('vibey-loops.json')).toBe(fs.readFileSync(golden, 'utf8'));
  });

  it('reads the fixture of `vibey loops --json`', () => {
    const catalogue = parse();
    expect(catalogue.source).toBe('vibey');
    expect(catalogue.default_loop).toBe('sovereignloop');
    expect(catalogue.paid_default_engine).toBe('claudeloop');
    expect(catalogue.ladder.build_attempts).toEqual(['LOW', 'LOW', 'STANDARD', 'STANDARD', 'HIGH', 'HIGH']);
    expect(catalogue.loops[0]?.engines.map((engine) => engine.engine_id)).toEqual(['gptossloop', 'qwenloop', 'claudeloop-local']);
    const gptossloop = catalogue.loops[0]?.engines.find((engine) => engine.engine_id === 'gptossloop');
    expect(gptossloop?.turns_flag).toBe('--max-turns');
    expect(gptossloop?.capabilities.images).toBe(false);
    expect(gptossloop?.capabilities.evidence.images).toContain('read_file');
    const codex = catalogue.loops[1]?.engines.find((engine) => engine.engine_id === 'codexloop');
    expect(codex?.turns_flag).toBeUndefined();
    expect(codex?.supports_cwd_flag).toBe(false);
    expect(catalogue.loops.flatMap((loop) => loop.engines).some((engine) => engine.repealed)).toBe(false);
    // ADR-0064: gptossloop is the sovereign default, on unless switched off; qwenloop is its
    // opt-in Qwen twin, same runner and protocol, its own settings, and no model from vibey.
    expect(gptossloop).toMatchObject({
      binary: 'gptossloop',
      state_dir: '.qwenloop',
      enabled: true,
      on_by_default: true,
      switch: 'VIBEY_FEATURE_GPTOSSLOOP',
      repealed: false,
      default_model: 'gpt-oss:20b',
      done_marker: 'QWENLOOP_TASK_FULLY_COMPLETE',
      controls: { prompt: ['prompt', '{run_id}', '{text}', '--cwd', '{cwd}'] },
      env: { passthrough: ['GPTOSSLOOP_*'] },
    });
    expect(catalogue.loops[0]?.engines.find((engine) => engine.engine_id === 'qwenloop')).toMatchObject({
      binary: 'qwenloop',
      state_dir: '.qwenloop',
      enabled: false,
      on_by_default: false,
      switch: 'VIBEY_FEATURE_QWENLOOP',
      default_model: null,
      done_marker: 'QWENLOOP_TASK_FULLY_COMPLETE',
      env: { passthrough: ['QWENLOOP_*'] },
      notes: [expect.stringContaining('the gpt-oss engine it used to be is gptossloop') as unknown as string],
    });
    expect(catalogue.loops[0]?.by_effort.LOW?.map((choice) => [choice.engine_id, choice.model])).toEqual([
      ['claudeloop-local', null],
      ['gptossloop', 'gpt-oss:20b'],
      ['qwenloop', null],
    ]);
  });

  it('reads on_by_default, and an engine a producer from before ADR-0064 lists as not on by default', () => {
    const older = parse(
      variant((value) => {
        for (const engine of value.loops[0].engines) {
          delete engine.on_by_default;
        }
      }),
    );
    expect(older.loops[0]?.engines.every((engine) => !engine.on_by_default)).toBe(true);
    expect(() => parse(variant((value) => (engineIn(value, 'gptossloop').on_by_default = 'yes')))).toThrow(
      'loops[0].engines[0].on_by_default: is not true or false',
    );
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
        value.loops[1].engines[0].notes = null;
      }),
    );
    expect(catalogue.loops[0]?.engines.map((engine) => engine.notes)).toEqual([['first', 'second'], ['one line'], undefined]);
    expect(catalogue.loops[1]?.engines[0]?.notes).toBeUndefined();
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
        const repealed = value.loops[0].engines.find((engine: Record<string, any>) => engine.engine_id === 'claudeloop-local');
        repealed.enabled = true;
        repealed.repealed = true;
        repealed.base_weight = 100;
        value.loops[0].by_effort.LOW = [
          { engine_id: 'claudeloop-local', model: null, achieved: 'LOW' },
          { engine_id: 'gptossloop', model: 'gpt-oss:20b', achieved: 'LOW' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const picks = [1, 2, 3, 4].map(() => selector.select(request()).engine.engine_id);
    expect(picks).toEqual(['gptossloop', 'gptossloop', 'gptossloop', 'gptossloop']);
  });

  it('still works with a vibey that has no `vibey loops`: sovereignloop, gptossloop, and its prompt box', async () => {
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
    expect(selection.engine).toMatchObject({ engine_id: 'gptossloop', repealed: false, controls: { prompt: ['prompt', '{run_id}', '{text}', '--cwd', '{cwd}'] } });
    expect(selection.engine.notes).toHaveLength(1);
  });
});

describe('DegradedCatalogue', () => {
  it('is sovereignloop with gptossloop, the default runner, on the configured model, a notice, and no ladder', () => {
    const catalogue = DegradedCatalogue.sovereign('gpt-oss:20b', 'vibey is too old');
    expect(catalogue.source).toBe('degraded');
    expect(catalogue.notice).toBe('vibey is too old');
    expect(catalogue.loops).toHaveLength(1);
    // Only gptossloop: qwenloop runs only once vibey switches it on, and there is no vibey here.
    expect(catalogue.loops[0]?.engines.map((engine) => engine.engine_id)).toEqual(['gptossloop']);
    const engine = catalogue.loops[0]?.engines[0];
    expect(engine).toMatchObject({
      binary: 'gptossloop',
      state_dir: '.qwenloop',
      enabled: true,
      on_by_default: true,
      switch: null,
      done_marker: 'QWENLOOP_TASK_FULLY_COMPLETE',
      env: { auth: [], passthrough: ['GPTOSSLOOP_*'] },
    });
    expect(engine?.default_model).toBe('gpt-oss:20b');
    expect(engine?.efforts.every((entry) => entry.model === 'gpt-oss:20b')).toBe(true);
    expect(engine?.notes?.[0]).toContain("else gptossloop's own");
    expect(engine?.capabilities.plugins).toBeNull();
    expect(engine?.turns_flag).toBe('--max-turns');
    expect(catalogue.loops[0]?.by_effort.HIGH).toEqual([{ engine_id: 'gptossloop', model: 'gpt-oss:20b', achieved: 'STANDARD' }]);
    expect(DegradedCatalogue.sovereign('qwen3:14b', 'n').loops[0]?.engines[0]?.default_model).toBe('qwen3:14b');
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
    expect(failing.notice).toBe('vibey 2.0.0 has no "vibey loops" command. The extension runs sovereignloop with gptossloop on gpt-oss:20b and effort auto.');
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

  it('on auto picks gptossloop for sovereignloop, with the effort projection as the turn limit', () => {
    const selection = new LoopSelector(parse()).select(request());
    expect(selection.engine.engine_id).toBe('gptossloop');
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

  it('runs ULTRA unbounded: no limit from its projection or the setting, only a task of its own', () => {
    const selector = new LoopSelector(parse());
    const ultra = selector.select(request({ effort: 'ULTRA', settingMaxTurns: 30 }));
    expect(ultra.effort).toBe('ULTRA');
    expect(ultra.argv).toEqual([]);
    expect(ultra.maxTurns).toBeUndefined();
    expect(ultra.maxTurnsSource).toBe('unbounded');
    const bounded = selector.select(request({ effort: 'ULTRA', taskMaxTurns: 12 }));
    expect(bounded.argv).toEqual(['--max-turns', '12']);
    expect(bounded.maxTurnsSource).toBe('task');
  });

  it('shows ULTRA distinctly in a picker, and reads its label back', () => {
    expect(Efforts.ALL.at(-1)).toBe('ULTRA');
    expect(Efforts.describe('ULTRA').label).toBe('$(flame) ULTRA');
    expect(Efforts.describe('ULTRA').detail).toContain('without a ceiling');
    expect(Efforts.describe('HIGH')).toEqual({ label: 'HIGH', detail: 'Every attempt at HIGH.' });
    expect(Efforts.fromLabel('$(flame) ULTRA')).toBe('ULTRA');
    expect(Efforts.fromLabel('auto')).toBe('auto');
    expect(Efforts.ULTRA_COLOUR).toEqual({ dark: '#ff6ad5', light: '#b0268f' });
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
        const claude = engineIn(value, 'claudeloop-local');
        claude.enabled = true;
        claude.base_weight = 2;
        claude.efforts[1].achieved = 'LOW';
        claude.efforts[1].model = 'qwen3:14b';
        local.by_effort.LOW = [
          { engine_id: 'gptossloop', model: 'gpt-oss:20b', achieved: 'LOW' },
          { engine_id: 'claudeloop-local', model: 'qwen3:14b', achieved: 'LOW' },
          { engine_id: 'missing-engine', model: null, achieved: 'LOW' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const resident = selector.select(request({ resident: ['gpt-oss:20b'] }));
    expect(resident.engine.engine_id).toBe('gptossloop');
    expect(resident.reason).toContain('already loaded');
    const picks = [1, 2, 3].map(() => selector.select(request()).engine.engine_id);
    expect(picks).toEqual(['claudeloop-local', 'gptossloop', 'claudeloop-local']);
  });

  it('skips an engine with no model when it looks for a resident one', () => {
    const catalogue = parse(
      variant((value) => {
        // qwenloop as vibey lists it, switched on: no model from vibey, its own config chooses.
        engineIn(value, 'qwenloop').enabled = true;
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
        engineIn(value, 'claudeloop-local').enabled = true;
        local.by_effort.STANDARD = [
          { engine_id: 'gptossloop', model: 'gpt-oss:20b', achieved: 'STANDARD' },
          { engine_id: 'claudeloop-local', model: null, achieved: 'STANDARD' },
        ];
      }),
    );
    const selector = new LoopSelector(catalogue);
    const rose = selector.select(request({ attempt: 3, previousEngine: 'gptossloop' }));
    expect(rose.engine.engine_id).toBe('claudeloop-local');
    expect(rose.reason).toContain('rotates away from gptossloop');
    const steady = selector.select(request({ attempt: 4, previousEngine: 'claudeloop-local' }));
    expect(steady.reason).not.toContain('rotates');
  });

  it('names an engine, or an engine and model, and refuses what it cannot run', () => {
    const selector = new LoopSelector(parse());
    const local = selector.select(request({ engine: 'gptossloop/gpt-oss:120b', effort: 'STANDARD' }));
    expect(local.model).toBe('gpt-oss:120b');
    expect(local.reason).toContain('on gpt-oss:120b as you chose');
    expect(selector.select(request({ engine: 'gptossloop/' })).model).toBe('gpt-oss:20b');
    expect(selector.select(request({ engine: 'gptossloop' })).engine.engine_id).toBe('gptossloop');
    // qwenloop is opt-in: named while vibey has it off, it says which switch turns it on.
    expect(() => selector.select(request({ engine: 'qwenloop' }))).toThrow(/^qwenloop is switched off; switch it on with VIBEY_FEATURE_QWENLOOP$/);
    const qwen = new LoopSelector(parse(variant((value) => (engineIn(value, 'qwenloop').enabled = true))));
    expect(qwen.select(request({ engine: 'qwenloop' })).model).toBeNull();
    expect(qwen.select(request({ engine: 'qwenloop/qwen3:14b' })).model).toBe('qwen3:14b');
    // gptossloop is on by default, so off means something switched it off.
    const gptossOff = new LoopSelector(parse(variant((value) => (engineIn(value, 'gptossloop').enabled = false))));
    expect(() => gptossOff.select(request({ engine: 'gptossloop' }))).toThrow(
      /^gptossloop is switched off; it is on by default, so VIBEY_FEATURE_GPTOSSLOOP or vibey's \[features\] table switched it off$/,
    );
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
    expect(() => selector.select(request({ engine: 'nosuch' }))).toThrow('its engines are gptossloop, qwenloop, claudeloop-local');
    expect(() => selector.select(request({ engine: 'claudeloop-local' }))).toThrow('switch it on with VIBEY_FEATURE_CLAUDELOOP_LOCAL');
    const repealed = new LoopSelector(
      parse(
        variant((value) => {
          engineIn(value, 'claudeloop-local').repealed = true;
        }),
      ),
    );
    expect(() => repealed.select(request({ engine: 'claudeloop-local' }))).toThrow(
      'claudeloop-local is repealed by the canon (8.b): it is listed, but it never runs',
    );
    expect(() => selector.select(request({ engine: 'claudeloop-local' }))).toThrow(/switched off; switch it on with /);
    const noSwitch = new LoopSelector(
      parse(
        variant((value) => {
          engineIn(value, 'claudeloop-local').switch = null;
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
    const noEntry = parse(variant((value) => engineIn(value, 'gptossloop').efforts.splice(1, 1)));
    expect(() => new LoopSelector(noEntry).select(request())).toThrow('gptossloop lists no LOW effort');
  });
});
