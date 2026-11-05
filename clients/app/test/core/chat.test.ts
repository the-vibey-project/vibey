// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { ChatModel } from '../../src/core/chat';

describe('ChatModel', () => {
  const model = new ChatModel();

  it('completes slash commands by prefix and returns empty when not a slash token', () => {
    expect(model.slashCommands.length).toBeGreaterThanOrEqual(15);
    expect(model.completeSlash('/').length).toBe(model.slashCommands.length);
    expect(model.completeSlash('  /st').map((s) => s.slash)).toEqual(['status', 'start']);
    expect(model.completeSlash('/unknown')).toEqual([]);
    expect(model.completeSlash('status')).toEqual([]);
    expect(model.completeSlash('/status p1')).toEqual([]);
  });

  it('badges spend gates vs non-spend gates', () => {
    expect(model.gateBadge({ isSpend: true })).toBe('SPEND GATE · requires spend scope');
    expect(model.gateBadge({ isSpend: false })).toBe('Gate · answer scope');
  });

  it('parses a chat turn with full and minimal fields, and refuses invalid shapes', () => {
    const full = model.parseTurn({
      reply: 'Hello',
      project_id: 'p1',
      tool_calls: [
        { name: 'vibey_status', arguments: { project_id: 'p1' }, result: { ok: true } },
        { arguments: 'not-record', result: undefined },
        'junk',
      ],
      gates: [
        {
          gate_id: 'g1',
          project_id: 'p1',
          kind: 'approval',
          prompt: 'Approve?',
          options: ['accept', 7, 'reject'],
          default_answer: 'accept',
          grant_key: null,
          is_spend: false,
          requires_scope: 'answer',
        },
        {
          gate_id: 'g2',
          kind: 'budget_exhausted',
          grant_key: 'max_dollars',
          is_spend: false,
          requires_scope: 'spend',
        },
        { gate_id: 'bad' },
      ],
    });
    expect(full.reply).toBe('Hello');
    expect(full.projectId).toBe('p1');
    expect(full.toolCalls).toEqual([
      { name: 'vibey_status', argumentsJson: '{"project_id":"p1"}', resultJson: '{"ok":true}' },
      { name: 'vibey_tool', argumentsJson: '{}', resultJson: '{}' },
    ]);
    expect(full.gates).toEqual([
      {
        gateId: 'g1',
        projectId: 'p1',
        kind: 'approval',
        prompt: 'Approve?',
        options: ['accept', 'reject'],
        defaultAnswer: 'accept',
        grantKey: null,
        isSpend: false,
        requiresScope: 'answer',
      },
      {
        gateId: 'g2',
        projectId: '',
        kind: 'budget_exhausted',
        prompt: '',
        options: [],
        defaultAnswer: null,
        grantKey: 'max_dollars',
        isSpend: false,
        requiresScope: 'spend',
      },
    ]);

    const minimal = model.parseTurn({ reply: 'Minimal' });
    expect(minimal).toEqual({ reply: 'Minimal', projectId: null, toolCalls: [], gates: [] });

    expect(() => model.parseTurn(null)).toThrow(/chat turn/);
    expect(() => model.parseTurn([])).toThrow(/chat turn/);
    expect(() => model.parseTurn({ project_id: 'p1' })).toThrow(/chat turn/);
  });

  it('parses a ledger narration page across all payload detail shapes and refuses non-pages', () => {
    const page = model.parseLedgerPage({
      project_id: 'p1',
      next_seq: 2,
      entries: [
        'not-an-object',
        { seq: 3, kind: 'job_completed', actor: 'claudeloop', payload: { summary: 'Built module' } },
        { seq: 4, kind: 'note', actor: 'operator', payload: { message: 'Paused lane' } },
        { seq: 5, kind: 'gate_opened', actor: 'vibey', payload: { prompt: 'Ship it?' } },
        { seq: 6, kind: 'phase_transition', actor: 'vibey', payload: { phase: 'REVIEW' } },
        { payload: 'none' },
      ],
    });
    expect(page).toEqual({
      projectId: 'p1',
      lastSeq: 6,
      events: [
        { seq: 3, kind: 'job_completed', actor: 'claudeloop', summary: '#3 job_completed (claudeloop) — Built module' },
        { seq: 4, kind: 'note', actor: 'operator', summary: '#4 note (operator) — Paused lane' },
        { seq: 5, kind: 'gate_opened', actor: 'vibey', summary: '#5 gate_opened (vibey) — Ship it?' },
        { seq: 6, kind: 'phase_transition', actor: 'vibey', summary: '#6 phase_transition (vibey) — REVIEW' },
        { seq: 0, kind: 'event', actor: 'vibey', summary: '#0 event (vibey)' },
      ],
    });

    const empty = model.parseLedgerPage({ entries: [] });
    expect(empty).toEqual({ projectId: '', lastSeq: 0, events: [] });

    expect(() => model.parseLedgerPage(null)).toThrow(/ledger page/);
    expect(() => model.parseLedgerPage({ project_id: 'p1' })).toThrow(/ledger page/);
  });
});
