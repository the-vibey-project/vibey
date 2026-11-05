// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Pure chat-first domain model for krypton mobile and web (ADR-0100): `/` command catalogue
 * and completion, `POST /api/v1/chat/messages` turn parser, spend-gate badge helper, and
 * `GET /api/v1/projects/{id}/ledger/after` narration parser. Declared by
 * `interfaces/chat-interface.ts`.
 */
import { HubError } from './hub-client';
import type {
  ChatGateCard,
  ChatLedgerEvent,
  ChatLedgerPage,
  ChatModelInterface,
  ChatSlashSpec,
  ChatToolCall,
  ChatTurn,
} from './interfaces/chat-interface';

type Json = Record<string, unknown>;

export class ChatModel implements ChatModelInterface {
  static readonly SLASH_COMMANDS: readonly ChatSlashSpec[] = [
    { slash: 'projects', usage: '/projects', title: 'List projects', description: 'List every project with phase, cycle and open gates.', toolName: 'vibey_projects' },
    { slash: 'status', usage: '/status [project-id]', title: 'Project status', description: 'Show phase, cycle, queue depth and engine circuits.', toolName: 'vibey_status' },
    { slash: 'gates', usage: '/gates [project-id]', title: 'Open gates', description: 'List every open human gate waiting on your answer.', toolName: 'vibey_gates' },
    { slash: 'answer', usage: '/answer <gate-id> <value>', title: 'Answer a gate', description: 'Answer an open gate by ID with a verdict, choice, number or JSON.', toolName: 'vibey_answer_gate' },
    { slash: 'budget', usage: '/budget [project-id]', title: 'Cycle budget', description: 'Show cycle dollar and turn caps and spend.', toolName: 'vibey_budget' },
    { slash: 'queue', usage: '/queue [project-id]', title: 'Job queue', description: 'Show queued, running and parked jobs.', toolName: 'vibey_queue' },
    { slash: 'ledger', usage: '/ledger [search-text]', title: 'Append-only ledger', description: 'Read or search recent events from the append-only ledger.', toolName: 'vibey_ledger' },
    { slash: 'loops', usage: '/loops', title: 'Loops and effort', description: 'Show sovereign and declared-only loops and the effort ladder.', toolName: 'vibey_loops' },
    { slash: 'lanes', usage: '/lanes', title: 'Running lanes', description: 'Show autonomous runner lanes on the hub computer.', toolName: 'vibey_lanes' },
    { slash: 'doctor', usage: '/doctor', title: 'Hub health checks', description: 'Run the hub health checks (database, sovereign model, tools).', toolName: 'vibey_doctor' },
    { slash: 'new', usage: '/new <name> [what to build]', title: 'Start a project', description: 'Create a new project and queue its design interview.', toolName: 'vibey_start_project' },
    { slash: 'start', usage: '/start [project-id]', title: 'Start worker', description: 'Start or resume the background worker for a project.', toolName: 'vibey_start_work' },
    { slash: 'pause', usage: '/pause [project-id]', title: 'Pause worker', description: 'Pause the background worker for a project.', toolName: 'vibey_pause_work' },
    { slash: 'abandon', usage: '/abandon [project-id] [reason]', title: 'Preview unwind (dry run)', description: 'Dry-run preview of jobs and gates that unwinding would cancel.', toolName: 'vibey_abandon_project' },
    { slash: 'help', usage: '/help', title: 'Chat commands', description: 'Show every slash command and what you can ask in plain words.', toolName: null },
  ];

  static readonly QUICK_COMMANDS: readonly { readonly label: string; readonly command: string }[] = [
    { label: 'Status', command: '/status' },
    { label: 'Gates', command: '/gates' },
    { label: 'Budget', command: '/budget' },
    { label: 'Queue', command: '/queue' },
    { label: 'Lanes', command: '/lanes' },
    { label: 'Doctor', command: '/doctor' },
    { label: 'Help', command: '/help' },
  ];

  readonly slashCommands: readonly ChatSlashSpec[] = ChatModel.SLASH_COMMANDS;

  completeSlash(typed: string): readonly ChatSlashSpec[] {
    const trimmed = typed.trimStart();
    if (!trimmed.startsWith('/') || trimmed.includes(' ')) {
      return [];
    }
    const needle = trimmed.slice(1).toLowerCase();
    return this.slashCommands.filter((spec) => spec.slash.startsWith(needle));
  }

  gateBadge(card: Pick<ChatGateCard, 'isSpend'>): string {
    return card.isSpend ? 'SPEND GATE · requires spend scope' : 'Gate · answer scope';
  }

  parseTurn(raw: unknown): ChatTurn {
    if (!ChatModel.isRecord(raw) || typeof raw.reply !== 'string') {
      throw new HubError('bad-answer', 'The hub did not send a chat turn.');
    }
    const toolCalls = Array.isArray(raw.tool_calls)
      ? raw.tool_calls.filter(ChatModel.isRecord).map(
          (call): ChatToolCall => ({
            name: typeof call.name === 'string' ? call.name : 'vibey_tool',
            argumentsJson: JSON.stringify(ChatModel.isRecord(call.arguments) ? call.arguments : {}),
            resultJson: JSON.stringify(call.result ?? {}),
          }),
        )
      : [];
    const gates = Array.isArray(raw.gates)
      ? raw.gates
          .filter((item): item is Json => ChatModel.isRecord(item) && typeof item.gate_id === 'string' && typeof item.kind === 'string')
          .map((item): ChatGateCard => {
            const isSpend = item.is_spend === true;
            return {
              gateId: item.gate_id as string,
              projectId: typeof item.project_id === 'string' ? item.project_id : '',
              kind: item.kind as string,
              prompt: typeof item.prompt === 'string' ? item.prompt : '',
              options: Array.isArray(item.options) ? item.options.filter((opt): opt is string => typeof opt === 'string') : [],
              defaultAnswer: typeof item.default_answer === 'string' ? item.default_answer : null,
              grantKey: typeof item.grant_key === 'string' ? item.grant_key : null,
              isSpend,
              requiresScope: item.requires_scope === 'spend' || isSpend ? 'spend' : 'answer',
            };
          })
      : [];
    return {
      reply: raw.reply,
      projectId: typeof raw.project_id === 'string' ? raw.project_id : null,
      toolCalls,
      gates,
    };
  }

  parseLedgerPage(raw: unknown): ChatLedgerPage {
    if (!ChatModel.isRecord(raw) || !Array.isArray(raw.entries)) {
      throw new HubError('bad-answer', 'The hub did not send a ledger page.');
    }
    const projectId = typeof raw.project_id === 'string' ? raw.project_id : '';
    let lastSeq = typeof raw.next_seq === 'number' ? raw.next_seq : 0;
    const events: ChatLedgerEvent[] = [];
    for (const item of raw.entries) {
      if (!ChatModel.isRecord(item)) continue;
      const seq = typeof item.seq === 'number' ? item.seq : 0;
      const kind = typeof item.kind === 'string' ? item.kind : 'event';
      const actor = typeof item.actor === 'string' ? item.actor : 'vibey';
      const payload = ChatModel.isRecord(item.payload) ? item.payload : {};
      const detail =
        typeof payload.summary === 'string'
          ? payload.summary
          : typeof payload.message === 'string'
            ? payload.message
            : typeof payload.prompt === 'string'
              ? payload.prompt
              : typeof payload.phase === 'string'
                ? payload.phase
                : '';
      if (seq > lastSeq) lastSeq = seq;
      events.push({
        seq,
        kind,
        actor,
        summary: detail !== '' ? `#${seq} ${kind} (${actor}) — ${detail}` : `#${seq} ${kind} (${actor})`,
      });
    }
    return { projectId, lastSeq, events };
  }

  private static isRecord(value: unknown): value is Json {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }
}
