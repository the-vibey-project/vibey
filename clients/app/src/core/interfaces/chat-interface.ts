// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The chat-first model for krypton on mobile and web (ADR-0100): the `/` slash-command table,
 * completion, turn and gate cards from `POST /api/v1/chat/messages`, and spend-gate badges.
 */

export interface ChatSlashSpec {
  readonly slash: string;
  readonly usage: string;
  readonly title: string;
  readonly description: string;
  readonly toolName: string | null;
}

export interface ChatToolCall {
  readonly name: string;
  readonly argumentsJson: string;
  readonly resultJson: string;
}

export interface ChatGateCard {
  readonly gateId: string;
  readonly projectId: string;
  readonly kind: string;
  readonly prompt: string;
  readonly options: readonly string[];
  readonly defaultAnswer: string | null;
  readonly grantKey: string | null;
  readonly isSpend: boolean;
  readonly requiresScope: 'spend' | 'answer';
}

export interface ChatTurn {
  readonly reply: string;
  readonly projectId: string | null;
  readonly toolCalls: readonly ChatToolCall[];
  readonly gates: readonly ChatGateCard[];
}

export interface ChatLedgerEvent {
  readonly seq: number;
  readonly kind: string;
  readonly actor: string;
  readonly summary: string;
}

export interface ChatLedgerPage {
  readonly projectId: string;
  readonly lastSeq: number;
  readonly events: readonly ChatLedgerEvent[];
}

export interface ChatModelInterface {
  readonly slashCommands: readonly ChatSlashSpec[];
  completeSlash(typed: string): readonly ChatSlashSpec[];
  gateBadge(card: Pick<ChatGateCard, 'isSpend'>): string;
  parseTurn(raw: unknown): ChatTurn;
  parseLedgerPage(raw: unknown): ChatLedgerPage;
}
