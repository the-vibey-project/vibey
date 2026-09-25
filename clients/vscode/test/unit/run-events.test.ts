// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { JsonlParse } from '../../src/core/jsonl';
import { RunTranscript, VerdictReader } from '../../src/core/run-events';
import { fixture } from './helpers';

const events = (name: string): unknown[] => JsonlParse.lines(fixture(name)).records;

describe('RunTranscript with the local runner\'s events (gptossloop and qwenloop write the same)', () => {
  const transcript = new RunTranscript();
  const patches = events('qwenloop-events.jsonl').flatMap((event) => transcript.accept(event));

  it('turns a whole recorded run into items', () => {
    expect(transcript.items().map((item) => item.kind)).toEqual([
      'assistant',
      'tool-call',
      'tool-result',
      'turn',
      'tool-call',
      'tool-result',
      'tool-call',
      'tool-result',
      'turn',
      'assistant',
      'turn',
      'notice',
    ]);
    expect(patches.filter((patch) => patch.op === 'append')).toHaveLength(1);
  });

  it('summarises tool calls and their results', () => {
    const items = transcript.items();
    expect(items[1]).toMatchObject({ kind: 'tool-call', name: 'read_file', turn: 1, detail: 'path=README.md' });
    expect(items[2]).toMatchObject({ kind: 'tool-result', ok: true, detail: 'read 4 lines' });
    expect(items[4]).toMatchObject({ kind: 'tool-call', detail: 'content=(66 chars) path=README.md' });
    expect(items[5]).toMatchObject({ detail: 'wrote 66 characters' });
    expect(items[6]).toMatchObject({ detail: 'argv=["git","diff","--stat"]' });
    expect(items[7]).toMatchObject({ ok: true, detail: 'exit 0: 1 file changed, 2 insertions(+)' });
    expect(items[3]).toMatchObject({ kind: 'turn', detail: 'Turn 1 done in 16.5 s (the model took 16.0 s) · 2,310 tokens in, 412 out' });
  });

  it('counts turns and tokens, knows it completed, and reads the verdict', () => {
    expect(transcript.turns).toBe(3);
    expect(transcript.attemptTurns).toBe(3);
    expect(transcript.inputTokens).toBe(8341);
    expect(transcript.outputTokens).toBe(897);
    expect(transcript.reportedDollars).toBe(0);
    expect(transcript.completed).toBe(true);
    expect(transcript.failure).toBeUndefined();
    expect(transcript.verdict()).toEqual({ text: 'complete: yes\ntests: none needed for a README line', marker: true });
  });

  it("adds a new attempt's turns to the earlier attempts', though each engine run counts its own from 1", () => {
    const task = new RunTranscript();
    task.accept({ type: 'turn.completed', turn: 1 });
    task.accept({ type: 'turn.completed', turn: 2 });
    task.beginAttempt();
    task.accept({ type: 'turn.completed', turn: 1, input_tokens: 10 });
    expect(task.turns).toBe(3);
    expect(task.attemptTurns).toBe(1);
    expect(task.items().at(-1)).toMatchObject({ kind: 'turn', turn: 1, detail: 'Turn 1 done · 10 tokens in, 0 out' });
    task.accept({ type: 'turn.completed' });
    expect(task.turns).toBe(4);
    expect(task.items().at(-1)).toMatchObject({ turn: 2 });
    task.accept({ type: 'turn.failed' });
    expect(task.attemptTurns).toBe(3);
    expect(task.items().at(-1)).toMatchObject({ text: 'Turn 3 failed: no reason given' });
    task.accept({ type: 'completed' });
    expect(task.items().at(-1)).toMatchObject({ text: 'The engine reports the task complete at turn 3.' });
  });

  it('starts each attempt afresh while keeping the totals', () => {
    const again = new RunTranscript();
    again.accept({ type: 'failed', reason: 'turn_limit', turn: 1, max_turns: 16 });
    again.accept({ type: 'turn.completed', turn: 1 });
    again.beginAttempt();
    expect(again.failure).toBeUndefined();
    expect(again.completed).toBe(false);
    expect(again.attemptTurns).toBe(0);
    expect(again.turns).toBe(1);
  });
});

describe('RunTranscript with opencodeloop events (event_type, flat)', () => {
  it('reads the kind from event_type and the fields beside it', () => {
    const transcript = new RunTranscript();
    transcript.accept({ event_type: 'turn.completed', turn: 1, input_tokens: 7 }, 'event_type');
    transcript.accept({ kind: 'turn.completed' }, 'event_type');
    expect(transcript.turns).toBe(1);
    expect(transcript.inputTokens).toBe(7);
    expect(transcript.items().at(-1)).toMatchObject({ kind: 'notice', text: 'event "(no type)"' });
  });
});

describe('RunTranscript with claudeloop events (event_type + payload)', () => {
  it('reads the envelope, the text, the tool, the turn, the reported cost and the finish', () => {
    const transcript = new RunTranscript();
    for (const event of events('claudeloop-events.jsonl')) {
      transcript.accept(event, 'event_type+payload');
    }
    const items = transcript.items();
    expect(items.map((item) => item.kind)).toEqual(['notice', 'assistant', 'tool-call', 'turn', 'notice', 'notice']);
    expect(items[1]).toMatchObject({ text: 'Reading the file.\n' });
    expect(items[2]).toMatchObject({ name: 'Read', turn: 1, detail: 'file_path=README.md' });
    expect(transcript.reportedDollars).toBeCloseTo(0.048);
    expect(transcript.completed).toBe(true);
  });

  it('finds the type under event_type, kind or type, and the turn outside the payload', () => {
    expect(RunTranscript.normalize({ kind: 'x', payload: 'not an object' }, 'event_type+payload')).toEqual(['x', {}]);
    expect(RunTranscript.normalize({ type: 'y', turn: 4, payload: {} }, 'event_type+payload')).toEqual(['y', { turn: 4 }]);
    expect(RunTranscript.normalize({ event_type: 'z', payload: { turn: 2 } }, 'event_type+payload')).toEqual(['z', { turn: 2 }]);
    expect(RunTranscript.normalize({ payload: {} }, 'event_type+payload')).toEqual(['', {}]);
    expect(RunTranscript.normalize({ type: 3 }, 'type')).toEqual(['', { type: 3 }]);
  });
});

describe('RunTranscript, event by event', () => {
  const one = (event: unknown, envelope?: 'type' | 'event_type+payload'): RunTranscript => {
    const transcript = new RunTranscript();
    transcript.accept(event, envelope);
    return transcript;
  };
  const text = (transcript: RunTranscript): string => {
    const item = transcript.items()[0];
    return item?.kind === 'notice' ? item.text : '';
  };

  it('shows an event that is not an object, or of a type it does not know, rather than dropping it', () => {
    expect(text(one([1, 2]))).toBe('an event that is not a JSON object: [1,2]');
    expect(text(one(null))).toBe('an event that is not a JSON object: null');
    expect(text(one({ type: 'something.new' }))).toBe('event "something.new"');
    expect(text(one({}))).toBe('event "(no type)"');
  });

  it('keeps text arriving in pieces in one item, and starts a new one after anything else', () => {
    const transcript = new RunTranscript();
    const first = transcript.accept({ type: 'text_delta', text: 'Hel' });
    const second = transcript.accept({ type: 'text_delta', text: 'lo' });
    transcript.accept({ type: 'text_delta' });
    transcript.accept({ type: 'turn.starting' });
    transcript.accept({ type: 'text_delta', text: 'again' });
    expect(first[0]?.op).toBe('add');
    expect(second).toEqual([{ op: 'append', id: 1, text: 'lo' }]);
    expect(transcript.items()).toEqual([
      { id: 1, kind: 'assistant', text: 'Hello' },
      { id: 2, kind: 'assistant', text: 'again' },
    ]);
  });

  it('reads claudeloop chatter with or without a trailing newline, and ignores empty chatter', () => {
    expect(one({ event_type: 'chatter.assistant', payload: { content: 'a\n' } }, 'event_type+payload').items()[0]).toMatchObject({ text: 'a\n' });
    expect(one({ event_type: 'chatter.assistant', payload: { message: 'b' } }, 'event_type+payload').items()[0]).toMatchObject({ text: 'b\n' });
    expect(one({ event_type: 'chatter.assistant', payload: { text: '' } }, 'event_type+payload').items()).toEqual([]);
  });

  it('reads the tool of each engine, named or not', () => {
    expect(one({ type: 'tool.call' }).items()[0]).toMatchObject({ name: '(unnamed tool)', detail: '' });
    expect(one({ type: 'item.started', item_type: 'command_execution', args: { cmd: 'ls' } }).items()[0]).toMatchObject({
      name: 'command_execution',
      detail: 'cmd=ls',
    });
    expect(one({ type: 'tool_call', name: 'edit', arguments: ['x'] }).items()[0]).toMatchObject({ detail: '' });
    expect(one({ type: 'tool.call', name: 't', arguments: { text: 'a\nb' } }).items()[0]).toMatchObject({ detail: 'text=(3 chars)' });
  });

  it('summarises every kind of tool result', () => {
    const detail = (result: unknown): [boolean, string] => {
      const item = one({ type: 'tool_result', name: 't', result }).items()[0];
      return item?.kind === 'tool-result' ? [item.ok, item.detail] : [false, 'none'];
    };
    expect(detail({ error: 'no such file' })).toEqual([false, 'error: no such file']);
    expect(detail({ exit_code: 2, output: '' })).toEqual([false, 'exit 2']);
    expect(detail({ exit_code: 0 })).toEqual([true, 'exit 0']);
    expect(detail({ replaced: 1, path: 'a.md' })).toEqual([true, 'edited a.md']);
    expect(detail({ replaced: 1 })).toEqual([true, 'edited the file']);
    expect(detail({ content: '' })).toEqual([true, 'read 0 lines']);
    expect(detail({ files: ['a', 'b'] })).toEqual([true, 'found 2 files']);
    expect(detail({ matches: [1] })).toEqual([true, 'found 1 matches']);
    expect(detail({ other: true })).toEqual([true, '{"other":true}']);
    expect(detail('plain')).toEqual([true, '"plain"']);
    expect(detail(undefined)).toEqual([true, '']);
    expect(detail({ error: 'x'.repeat(500) })[1]).toHaveLength(241);
    const codex = one({ type: 'item.completed', item_type: 'file_change', status: 'completed' }).items()[0];
    expect(codex).toMatchObject({ kind: 'tool-result', name: 'file_change', ok: true });
  });

  it('describes turns with what the event has', () => {
    const bare = one({ type: 'turn.completed' });
    expect(bare.items()[0]).toMatchObject({ turn: 1, detail: 'Turn 1 done · 0 tokens in, 0 out' });
    const failed = one({ type: 'turn.failed', error: 'rate limited' });
    expect(text(failed)).toBe('Turn 1 failed: rate limited');
    expect(text(one({ type: 'turn.failed', turn: 7 }))).toBe('Turn 7 failed: no reason given');
    expect(text(one({ type: 'turn.retried', turn: 2, retry: 1 }))).toContain('Turn 2');
    expect(text(one({ type: 'turn.retried' }))).toContain('retry ?');
    expect(text(one({ type: 'turn.empty', turn: 3, retrying: true }))).toContain('asked again');
    expect(one({ type: 'turn.empty' }).items()[0]).toMatchObject({ level: 'error' });
    expect(text(one({ type: 'turn.empty', retrying: true }))).toBe('Turn ?: the model sent an empty reply, so the runner asked again.');
    expect(text(one({ type: 'turn.empty', turn: 4, retrying: false }))).toBe('Turn 4: the model sent an empty reply again; the runner gave up.');
  });

  it('shows a follow-up the engine received', () => {
    expect(one({ type: 'prompt.received', text: 'shorter please' }).items()[0]).toMatchObject({ kind: 'follow-up', text: 'shorter please' });
    expect(one({ type: 'prompt.received' }).items()[0]).toMatchObject({ text: '' });
  });

  it('explains each way a run fails', () => {
    expect(one({ type: 'failed', reason: 'turn_limit', max_turns: 16, turn: 16 }).failure).toEqual({
      reason: 'turn_limit',
      turn: 16,
      explanation: expect.stringContaining('all 16 turns') as unknown as string,
    });
    expect(one({ type: 'failed', reason: 'turn_limit' }).failure?.explanation).toContain('all its turns');
    expect(one({ type: 'failed', reason: 'empty_response' }).failure?.explanation).toContain('empty replies');
    expect(one({ type: 'failed', reason: 'invalid_completion_claims' }).failure?.explanation).toContain('three times');
    expect(one({ type: 'failed', reason: 'odd' }).failure?.explanation).toBe('the engine gave the reason "odd".');
    expect(one({ type: 'failed' }).failure?.reason).toBe('unknown');
  });

  it("reads each engine's verdict event", () => {
    expect(one({ event_type: 'finished', payload: { success: true, turn: 2 } }, 'event_type+payload').completed).toBe(true);
    expect(one({ type: 'run.verdict', complete: true }).completed).toBe(true);
    expect(one({ type: 'run.verdict', complete: false, reason: 'tests fail' }).failure?.explanation).toBe('the engine gave the reason "tests fail".');
    expect(one({ event_type: 'finished', payload: {} }, 'event_type+payload').failure?.reason).toBe('the engine reported that the task is not complete');
    expect(text(one({ type: 'completed' }))).toBe('The engine reports the task complete at turn 0.');
  });

  it('adds notes of its own to the same stream', () => {
    const transcript = new RunTranscript();
    transcript.accept({ type: 'text_delta', text: 'x' });
    expect(transcript.note('warn', 'careful')).toEqual({ op: 'add', item: { id: 2, kind: 'notice', level: 'warn', text: 'careful' } });
    transcript.accept({ type: 'text_delta', text: 'y' });
    expect(transcript.items()).toHaveLength(3);
  });
});

describe('VerdictReader', () => {
  it('reads the last verdict fence and the marker', () => {
    expect(VerdictReader.read('```qwenloop-verdict\nfirst\n``` then ```qwenloop-verdict v2\nsecond\n```\nQWENLOOP_TASK_FULLY_COMPLETE')).toEqual({
      text: 'second',
      marker: true,
    });
    expect(VerdictReader.read('no verdict')).toEqual({ marker: false });
  });
});
