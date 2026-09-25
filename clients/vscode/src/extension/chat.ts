// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * `@vibey` in the chat view: the same commands as the panel's `/` commands, from the same
 * table, run by the same handlers. `@vibey /ask ...` (or `@vibey` with no command) starts a
 * task and streams its transcript into the chat as it happens. Everything from the model is
 * appended as escaped text, never as markdown it could write links or images with. Only
 * where this editor has the chat API; nothing otherwise. Declared by
 * `interfaces/chat-interface.ts`.
 */
import * as vscode from 'vscode';
import { Presenter } from '../core/cli-support';
import { SlashCommands } from '../core/commands';
import type { VibeyController } from './controller';
import type { CommandActionsInterface } from './interfaces/actions-interface';
import type { VibeyChatInterface } from './interfaces/chat-interface';

export class VibeyChat implements VibeyChatInterface {
  static readonly ID = 'vibey.chat';
  private readonly slash = new SlashCommands();
  private readonly presenter = new Presenter();

  constructor(
    private readonly controller: VibeyController,
    private readonly actions: CommandActionsInterface,
    private readonly extensionUri: vscode.Uri,
  ) {}

  register(): vscode.Disposable | undefined {
    if (typeof vscode.chat?.createChatParticipant !== 'function') {
      return undefined;
    }
    const participant = vscode.chat.createChatParticipant(VibeyChat.ID, (request, _context, stream, token) => this.handle(request, stream, token));
    participant.iconPath = vscode.Uri.joinPath(this.extensionUri, 'media', 'vibey.svg');
    return participant;
  }

  private async handle(request: vscode.ChatRequest, stream: vscode.ChatResponseStream, token: vscode.CancellationToken): Promise<vscode.ChatResult> {
    const say = (text: string): void => {
      stream.markdown(new vscode.MarkdownString().appendText(text));
      stream.markdown('\n\n');
    };
    // VS Code hands over `@vibey /budget add x` as the command `budget` and the prompt `add x`.
    const typed = request.command === undefined ? `/ask ${request.prompt}` : `/${request.command} ${request.prompt}`;
    const parsed = this.slash.parse(typed);
    if (parsed.kind !== 'command') {
      say(parsed.kind === 'unknown' ? parsed.reply : this.slash.help());
      return {};
    }
    if (parsed.spec.id === 'vibey.ask') {
      await this.ask(parsed.args, stream, token, say);
      return {};
    }
    await this.actions.run(parsed.spec.id, { args: parsed.args, say });
    return {};
  }

  private async ask(task: string, stream: vscode.ChatResponseStream, token: vscode.CancellationToken, say: (text: string) => void): Promise<void> {
    if (!task.trim()) {
      say('Say what to do: @vibey add a line to README.md that says how to run the tests');
      return;
    }
    const services = this.controller.services;
    if (services.settings.loop === 'paidloop' && !services.paidDeclared()) {
      say('paidloop is not declared, so nothing was started. Declare it with a cap first: @vibey /loop paid');
      return;
    }
    const run = await this.controller.ask(task.trim());
    if (run === undefined) {
      say('Open a folder that is a git repository first: a task works on a copy of it.');
      return;
    }
    stream.progress('Waiting for the model…');
    const subscription = run.onPatch((patch) => {
      const text = this.presenter.patch(patch, run.items());
      if (text !== '') {
        stream.markdown(new vscode.MarkdownString().appendText(text));
      }
    });
    const cancelled = token.onCancellationRequested(() => void run.stop());
    try {
      const record = await run.result;
      stream.markdown('\n\n');
      say(this.presenter.record(record));
      stream.button({ command: 'vibey.openRunLog', title: 'Open the task', arguments: [{ kind: 'run', runId: run.runId }] });
    } finally {
      subscription.dispose();
      cancelled.dispose();
    }
  }
}
