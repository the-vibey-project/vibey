// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * qwenloop's events, as `qwenloop/application/runner.py` writes them, turned into what a
 * person reads. Every event yields something: a type this version does not know is shown
 * as such rather than dropped, so a newer qwenloop can never make the view silently lose
 * part of a run. Everything here is data from a model or a tool and is only ever rendered
 * as text (the webview never treats it as HTML). Declared by
 * `interfaces/run-events-interface.ts`.
 */
import type { EventEnvelope } from './interfaces/catalogue-interface';
import type {
  NoticeLevel,
  RunFailure,
  RunItem,
  RunPatch,
  RunTranscriptInterface,
  Verdict,
} from './interfaces/run-events-interface';
import { QwenloopCommand } from './qwenloop';

type EventRecord = Readonly<Record<string, unknown>>;


export class RunTranscript implements RunTranscriptInterface {
  /** The longest detail line kept for one tool call or result. */
  static readonly DETAIL_CHARS = 240;

  private readonly shown: RunItem[] = [];
  private nextId = 1;
  /** The assistant item text is being added to, until any other event arrives. */
  private openText: { id: number; index: number } | undefined;
  private assistant = '';
  private turnCount = 0;
  private done = false;
  private failed: RunFailure | undefined;
  private tokensIn = 0;
  private tokensOut = 0;
  private dollars = 0;
  private attemptStart = 0;

  get turns(): number {
    return this.turnCount;
  }

  /** Turns since the current attempt began. */
  get attemptTurns(): number {
    return this.turnCount - this.attemptStart;
  }

  /** A new engine run inside the same task: its turns count afresh, and its verdict is its own. */
  beginAttempt(): void {
    this.attemptStart = this.turnCount;
    this.done = false;
    this.failed = undefined;
    this.openText = undefined;
  }

  get completed(): boolean {
    return this.done;
  }

  get failure(): RunFailure | undefined {
    return this.failed;
  }

  get inputTokens(): number {
    return this.tokensIn;
  }

  get outputTokens(): number {
    return this.tokensOut;
  }

  /** Dollars the engine itself reported for its turns (`cost_usd`), when it reports any. */
  get reportedDollars(): number {
    return this.dollars;
  }

  items(): readonly RunItem[] {
    return this.shown;
  }

  verdict(): Verdict {
    return VerdictReader.read(this.assistant);
  }

  accept(event: unknown, envelope: EventEnvelope = 'type'): readonly RunPatch[] {
    if (typeof event !== 'object' || event === null || Array.isArray(event)) {
      return [this.notice('warn', `an event that is not a JSON object: ${RunTranscript.clip(String(JSON.stringify(event)))}`)];
    }
    const [type, record] = RunTranscript.normalize(event as EventRecord, envelope);
    if (type === 'text_delta') {
      return this.text(typeof record.text === 'string' ? record.text : '');
    }
    if (type === 'chatter.assistant') {
      const said = RunTranscript.firstText(record, ['text', 'content', 'message']);
      return said === undefined ? [] : this.text(said.endsWith('\n') ? said : `${said}\n`);
    }
    this.openText = undefined;
    const turn = RunTranscript.integer(record.turn);
    switch (type) {
      case 'tool.call':
      case 'chatter.tool':
      case 'tool_call':
      case 'item.started':
      case 'sdk.event':
        return [
          this.add({
            kind: 'tool-call',
            ...(turn === undefined ? {} : { turn }),
            name: RunTranscript.name(record.name ?? record.tool ?? record.item_type),
            detail: RunTranscript.clip(RunTranscript.arguments(record.arguments ?? record.input ?? record.args)),
          }),
        ];
      case 'tool_result':
      case 'item.completed': {
        const [ok, detail] = RunTranscript.result(record.result ?? record.output ?? (type === 'item.completed' ? record : undefined));
        return [this.add({ kind: 'tool-result', name: RunTranscript.name(record.name ?? record.tool ?? record.item_type), ok, detail })];
      }
      case 'turn.completed':
        return this.turnCompleted(record, turn);
      case 'turn.failed':
        this.turnCount += 1;
        return [this.notice('warn', `Turn ${turn ?? this.attemptTurns} failed: ${RunTranscript.clip(RunTranscript.firstText(record, ['error', 'message', 'reason']) ?? 'no reason given')}`)];
      case 'turn.retried':
        return [
          this.notice(
            'warn',
            `Turn ${turn ?? '?'}: the model's tool call could not be read, so qwenloop asked again (retry ${RunTranscript.integer(record.retry) ?? '?'}).`,
          ),
        ];
      case 'turn.empty':
        return [
          record.retrying === true
            ? this.notice('warn', `Turn ${turn ?? '?'}: the model sent an empty reply, so qwenloop asked again.`)
            : this.notice('error', `Turn ${turn ?? '?'}: the model sent an empty reply again; qwenloop gave up.`),
        ];
      case 'prompt.received':
        return [this.add({ kind: 'follow-up', text: typeof record.text === 'string' ? record.text : '' })];
      case 'completed':
        this.done = true;
        return [this.notice('info', `The engine reports the task complete at turn ${turn ?? this.attemptTurns}.`)];
      case 'finished':
      case 'run.verdict':
        return [this.verdictEvent(record, turn)];
      case 'failed':
        return [this.failedEvent(record, turn)];
      case 'turn.starting':
      case 'turn.started':
      case 'chatter.prompt':
        return [];
      default:
        return [this.notice('info', `event "${RunTranscript.clip(type || '(no type)')}"`)];
    }
  }

  /** An event as (type, fields), whichever envelope the engine writes. */
  static normalize(event: EventRecord, envelope: EventEnvelope): [string, EventRecord] {
    if (envelope === 'type') {
      return [typeof event.type === 'string' ? event.type : '', event];
    }
    if (envelope === 'event_type') {
      // Flat records: the kind in `event_type`, its fields beside it.
      return [typeof event.event_type === 'string' ? event.event_type : '', event];
    }
    const type = [event.event_type, event.kind, event.type].find((value): value is string => typeof value === 'string') ?? '';
    const payload =
      typeof event.payload === 'object' && event.payload !== null && !Array.isArray(event.payload)
        ? (event.payload as EventRecord)
        : {};
    return [type, { ...payload, ...(payload.turn === undefined && event.turn !== undefined ? { turn: event.turn } : {}) }];
  }

  /** claudeloop and agyloop end with `finished` (payload.success); codexloop with `run.verdict` (complete). */
  private verdictEvent(record: EventRecord, turn: number | undefined): RunPatch {
    const success = record.success ?? record.complete;
    if (success === true) {
      this.done = true;
      return this.notice('info', `The engine reports the task complete${turn === undefined ? '' : ` at turn ${turn}`}.`);
    }
    return this.failedEvent({ reason: RunTranscript.firstText(record, ['reason', 'error', 'message']) ?? 'the engine reported that the task is not complete' }, turn);
  }

  private static firstText(record: EventRecord, keys: readonly string[]): string | undefined {
    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'string' && value !== '') {
        return value;
      }
    }
    return undefined;
  }

  private text(delta: string): readonly RunPatch[] {
    this.assistant += delta;
    if (this.openText !== undefined) {
      const current = this.shown[this.openText.index] as Extract<RunItem, { kind: 'assistant' }>;
      this.shown[this.openText.index] = { ...current, text: current.text + delta };
      return [{ op: 'append', id: this.openText.id, text: delta }];
    }
    const patch = this.add({ kind: 'assistant', text: delta });
    this.openText = { id: patch.item.id, index: this.shown.length - 1 };
    return [patch];
  }

  private turnCompleted(record: EventRecord, turn: number | undefined): readonly RunPatch[] {
    // An engine numbers its turns from 1 on every run, so an attempt's turn N is the task's
    // turn (the earlier attempts' turns) + N. The item shows the engine's own number.
    const number = turn ?? this.attemptTurns + 1;
    this.turnCount = Math.max(this.turnCount, this.attemptStart + number);
    const tokensIn = RunTranscript.integer(record.input_tokens) ?? 0;
    const tokensOut = RunTranscript.integer(record.output_tokens) ?? 0;
    this.tokensIn += tokensIn;
    this.tokensOut += tokensOut;
    this.dollars += typeof record.cost_usd === 'number' && Number.isFinite(record.cost_usd) ? record.cost_usd : 0;
    const duration = RunTranscript.integer(record.duration_ms);
    const model = RunTranscript.integer(record.model_ms);
    const parts = [`Turn ${number} done`];
    if (duration !== undefined) {
      parts.push(`in ${RunTranscript.seconds(duration)}`);
    }
    if (model !== undefined) {
      parts.push(`(the model took ${RunTranscript.seconds(model)})`);
    }
    parts.push(`· ${tokensIn.toLocaleString('en-US')} tokens in, ${tokensOut.toLocaleString('en-US')} out`);
    return [this.add({ kind: 'turn', turn: number, detail: parts.join(' ') })];
  }

  private failedEvent(record: EventRecord, turn: number | undefined): RunPatch {
    const reason = typeof record.reason === 'string' ? record.reason : 'unknown';
    const maxTurns = RunTranscript.integer(record.max_turns);
    const explanations: Record<string, string> = {
      turn_limit: `it used all ${maxTurns ?? 'its'} turns without finishing. Give it more turns (vibey.maxTurns, or max_turns in a task file) or a smaller task.`,
      empty_response: 'the model kept sending empty replies.',
      invalid_completion_claims: 'the model said it was finished three times without doing the work and tests.',
    };
    const explanation = explanations[reason] ?? `the engine gave the reason "${reason}".`;
    this.failed = { reason, ...(turn === undefined ? {} : { turn }), explanation };
    return this.notice('error', `qwenloop stopped without finishing: ${explanation}`);
  }

  note(level: NoticeLevel, text: string): RunPatch {
    return this.notice(level, text);
  }

  private notice(level: NoticeLevel, text: string): RunPatch {
    this.openText = undefined;
    return this.add({ kind: 'notice', level, text });
  }

  private add(item: DistributiveOmit<RunItem, 'id'>): { op: 'add'; item: RunItem } {
    const complete = { ...item, id: this.nextId } as RunItem;
    this.nextId += 1;
    this.shown.push(complete);
    return { op: 'add', item: complete };
  }

  private static name(value: unknown): string {
    return typeof value === 'string' && value ? value : '(unnamed tool)';
  }

  private static integer(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) ? Math.round(value) : undefined;
  }

  private static seconds(milliseconds: number): string {
    return `${(milliseconds / 1000).toFixed(1)} s`;
  }

  /** A tool call's arguments as one short line: `path=docs/a.md content=(1,234 chars)`. */
  private static arguments(value: unknown): string {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      return '';
    }
    return Object.entries(value as Record<string, unknown>)
      .map(([key, argument]) => {
        if (typeof argument === 'string') {
          return argument.length > 80 || argument.includes('\n')
            ? `${key}=(${argument.length.toLocaleString('en-US')} chars)`
            : `${key}=${argument}`;
        }
        return `${key}=${JSON.stringify(argument)}`;
      })
      .join(' ');
  }

  /** Whether a tool result reports success, and a line saying what it did. */
  private static result(value: unknown): [boolean, string] {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      return [true, RunTranscript.clip(JSON.stringify(value) ?? '')];
    }
    const result = value as Record<string, unknown>;
    if (typeof result.error === 'string') {
      return [false, RunTranscript.clip(`error: ${result.error}`)];
    }
    if (typeof result.exit_code === 'number') {
      const output = typeof result.output === 'string' ? result.output.trim() : '';
      const lastLine = output.slice(output.lastIndexOf('\n') + 1);
      return [
        result.exit_code === 0,
        RunTranscript.clip(`exit ${result.exit_code}${lastLine ? `: ${lastLine}` : ''}`),
      ];
    }
    if (typeof result.written === 'number') {
      return [true, `wrote ${result.written.toLocaleString('en-US')} characters`];
    }
    if (typeof result.replaced === 'number') {
      return [true, `edited ${typeof result.path === 'string' ? result.path : 'the file'}`];
    }
    if (typeof result.content === 'string') {
      const lines = result.content === '' ? 0 : result.content.split('\n').length;
      return [true, `read ${lines.toLocaleString('en-US')} lines`];
    }
    if (Array.isArray(result.files)) {
      return [true, `found ${result.files.length.toLocaleString('en-US')} files`];
    }
    if (Array.isArray(result.matches)) {
      return [true, `found ${result.matches.length.toLocaleString('en-US')} matches`];
    }
    return [true, RunTranscript.clip(JSON.stringify(result))];
  }

  private static clip(text: string): string {
    const flat = text.replace(/\s+/g, ' ').trim();
    return flat.length > RunTranscript.DETAIL_CHARS
      ? `${flat.slice(0, RunTranscript.DETAIL_CHARS)}…`
      : flat;
  }
}

/** `Omit` that keeps a union a union. */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;

/** The verdict qwenloop's contract asks for: a ```qwenloop-verdict fence, then the marker. */
export class VerdictReader {
  private static readonly FENCE = /```qwenloop-verdict[^\n]*\n([\s\S]*?)```/gi;

  static read(text: string): Verdict {
    let body: string | undefined;
    for (const match of text.matchAll(VerdictReader.FENCE)) {
      body = (match[1] as string).trim();
    }
    return {
      ...(body === undefined ? {} : { text: body }),
      marker: text.includes(QwenloopCommand.DONE_MARKER),
    };
  }
}
