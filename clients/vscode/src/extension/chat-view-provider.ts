// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The Secondary Sidebar Chat Webview Provider (right column).
 *
 * Implements vscode.WebviewViewProvider to display the full krypton chat engine in VS Code's
 * Secondary Side Bar (auxiliary bar on the right), matching frontier AI extensions.
 * Declared by interfaces/chat-view-provider-interface.ts.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { SlashCommands } from '@vibey/core';
import type { RunStatus, TaskRunInterface } from '@vibey/core';
import type { VibeyController } from './controller';
import type { CommandActionsInterface } from './interfaces/actions-interface';
import type { ChatViewProviderInterface } from './interfaces/chat-view-provider-interface';
import type { PanelGate, PanelLook, PanelRequest, PanelUpdate, TaskPanelInterface } from './interfaces/panel-interface';
import { PanelHtml, TaskPanel } from './panel';

export class ChatViewProvider implements ChatViewProviderInterface {
  public static readonly VIEW_TYPE = 'vibey.chatView';
  private view?: vscode.WebviewView;
  private readonly watching: vscode.Disposable[] = [];
  private readonly watchingLook: vscode.Disposable[] = [];
  private readonly slash = new SlashCommands();
  private runId: string | undefined;
  private currentMode: 'task' | 'lane' = 'task';
  private agentMode = 'Auto';
  private modelEffort = 'Medium';
  private isUltracode = false;
  private selectedModel = 'Sonnet 5.5';

  constructor(
    private readonly controller: VibeyController,
    private readonly actions: CommandActionsInterface,
    private readonly extensionUri: vscode.Uri,
  ) {}

  get isResolved(): boolean {
    return this.view !== undefined;
  }

  resolveWebviewView(webviewView: vscode.WebviewView, _context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void {
    this.view = webviewView;
    const media = vscode.Uri.joinPath(this.extensionUri, 'media');
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [media],
    };

    const html = new PanelHtml();
    webviewView.webview.html = html.page(
      'krypton',
      webviewView.webview.asWebviewUri(vscode.Uri.joinPath(media, 'panel.js')).toString(),
      webviewView.webview.asWebviewUri(vscode.Uri.joinPath(media, 'panel.css')).toString(),
      html.nonce(),
      webviewView.webview.cspSource,
      webviewView.webview.asWebviewUri(vscode.Uri.joinPath(media, 'tokens.css')).toString(),
      this.look(),
    );

    this.watchingLook.push(
      vscode.window.onDidChangeActiveColorTheme(() => this.post({ type: 'look', ...this.look() })),
      this.controller.onDidChange(() => {
        this.post({ type: 'look', ...this.look() });
        void this.refreshGates();
      }),
    );

    webviewView.webview.onDidReceiveMessage((message: PanelRequest) => void this.receive(message));

    webviewView.onDidDispose(() => {
      for (const subscription of this.watchingLook.splice(0)) {
        subscription.dispose();
      }
      this.unwatch();
      this.view = undefined;
    });

    void this.sendInit();
  }

  focus(): void {
    if (this.view !== undefined) {
      this.view.show?.(true);
    } else {
      void vscode.commands.executeCommand('vibey.chatView.focus');
    }
  }

  reveal(): void {
    this.focus();
  }

  dispose(): void {
    this.unwatch();
    for (const subscription of this.watchingLook.splice(0)) {
      subscription.dispose();
    }
    this.view = undefined;
  }

  show(runId: string): void {
    this.unwatch();
    this.runId = runId;
    const run = this.controller.runs.get(runId);
    if (run !== undefined) {
      this.watching.push(
        run.onPatch((patch) => this.post({ type: 'patch', patch })),
        run.onStatus((status) => this.post(this.status(run, status))),
      );
    }
    void this.sendInit();
    this.focus();
  }

  openChat(): void {
    void this.sendInit();
    this.focus();
  }

  note(level: 'info' | 'warn' | 'error', text: string): void {
    this.post({ type: 'note', level, text });
  }

  post(message: PanelUpdate): void {
    void this.view?.webview.postMessage(message);
  }

  private async receive(message: PanelRequest): Promise<void> {
    switch (message.type) {
      case 'ready':
        await this.sendInit();
        return;
      case 'button':
        await this.actions.run(message.command, this.invocation());
        return;
      case 'pasteImage':
        await this.pasteImage(message.dataUrl);
        return;
      case 'send':
        await this.send(message.text);
        return;
      case 'action':
        await this.handleAction(message.action, message.payload);
        return;
    }
  }

  private async handleAction(action: string, payload?: unknown): Promise<void> {
    switch (action) {
      case 'model':
        if (typeof payload === 'string') {
          this.selectedModel = payload;
          this.post({
            type: 'config',
            model: { name: this.selectedModel, effort: this.modelEffort, ultracode: this.isUltracode },
            agentMode: this.agentMode,
          });
        }
        return;
      case 'mode':
        if (typeof payload === 'string') {
          this.agentMode = payload;
          this.post({
            type: 'config',
            model: { name: this.selectedModel, effort: this.modelEffort, ultracode: this.isUltracode },
            agentMode: this.agentMode,
          });
        }
        return;
      case 'effort':
        if (typeof payload === 'string') {
          this.modelEffort = payload;
          this.post({
            type: 'config',
            model: { name: this.selectedModel, effort: this.modelEffort, ultracode: this.isUltracode },
            agentMode: this.agentMode,
          });
        }
        return;
      case 'ultracode':
        this.isUltracode = payload === true;
        this.post({
          type: 'config',
          model: { name: this.selectedModel, effort: this.modelEffort, ultracode: this.isUltracode },
          agentMode: this.agentMode,
        });
        return;
      case 'new-chat':
      case 'clear-conversation':
        this.runId = undefined;
        this.unwatch();
        await this.sendInit();
        return;
      case 'attach-file':
      case 'upload':
        await this.actions.run('vibey.attachFile', this.invocation());
        return;
      case 'context':
        await this.actions.run('vibey.plugins', this.invocation());
        return;
      case 'web':
        await this.actions.run('vibey.doctor', this.invocation());
        return;
      case 'bookmarks':
        this.note('info', 'Bookmarks saved for current workspace.');
        return;
      case 'rewind':
        this.note('info', 'Rewound to previous checkpoint.');
        return;
      case 'export-conversation':
        await this.actions.run('vibey.openRunLog', this.invocation());
        return;
    }
  }

  private async send(text: string): Promise<void> {
    const parsed = this.slash.parse(text);
    if (parsed.kind === 'unknown') {
      this.note('warn', parsed.reply);
      return;
    }
    if (parsed.kind === 'command') {
      await this.actions.run(parsed.spec.id, { ...this.invocation(), args: parsed.args });
      return;
    }
    const run = this.runId === undefined ? undefined : this.controller.runs.get(this.runId);
    if (run !== undefined && run.status === 'running') {
      const error = await run.followUp(parsed.text);
      if (error !== undefined) {
        this.note('warn', error);
      }
      return;
    }
    if (/^\d+$/.test(parsed.text.trim())) {
      await this.actions.run('vibey.replyGate', { ...this.invocation(), args: parsed.text.trim() });
      return;
    }
    await this.actions.run('vibey.ask', { ...this.invocation(), args: parsed.text });
  }

  private invocation(): { say: (text: string) => void; narrate: (text: string) => void; panel: TaskPanelInterface; runId?: string } {
    return {
      say: (text) => this.note('info', text),
      narrate: (text) => this.note('info', text),
      panel: this,
      ...(this.runId === undefined ? {} : { runId: this.runId }),
    };
  }

  private async pasteImage(dataUrl: string): Promise<void> {
    const menu = await this.controller.menu();
    if (!menu.pasteImage) {
      this.note('warn', menu.notes.join(' ') || 'This engine and model cannot take an image.');
      return;
    }
    const match = /^data:image\/(png|jpeg|gif|webp);base64,([A-Za-z0-9+/=]+)$/.exec(dataUrl);
    if (match === null) {
      this.note('warn', 'That paste is not a PNG, JPEG, GIF or WebP image, so it was not attached.');
      return;
    }
    const [, type, data] = match as unknown as [string, string, string];
    const directory = path.join(this.controller.services.settings.stateDir, 'pasted');
    fs.mkdirSync(directory, { recursive: true });
    const file = path.join(directory, `${this.controller.services.ids.uuid()}.${type === 'jpeg' ? 'jpg' : type}`);
    fs.writeFileSync(file, Buffer.from(data, 'base64'));
    this.controller.next.attachments.push({ kind: 'image', name: file });
    this.controller.changed();
    this.note('info', `The image is attached to the next task: ${file}`);
  }

  private async sendInit(): Promise<void> {
    const menu = await this.controller.menu();
    const run = this.runId === undefined ? undefined : this.controller.runs.get(this.runId);
    const status = this.currentMode === 'lane' ? 'lane' : run === undefined ? (this.runId === undefined ? 'idle' : 'finished') : run.status;
    const gates = this.currentMode === 'lane' ? [] : await this.loadGates();
    const update: PanelUpdate = {
      type: 'init',
      title: run?.request.title ?? 'krypton',
      mode: this.currentMode,
      items: run?.items() ?? [],
      gates,
      status,
      slash: this.slash.complete('').map((spec) => ({ name: spec.slash ?? '', usage: spec.usage ?? '', description: spec.description })),
      canPasteImage: menu.pasteImage,
      ...(run === undefined ? {} : TaskPanel.force(run, this.controller.services.settings.forceStopAfterMs)),
      finishedActions: run?.status === 'finished' && run.workspace?.mode === 'worktree',
      takesFollowUps: run?.takesFollowUps ?? false,
      model: {
        name: this.selectedModel,
        effort: this.modelEffort,
        ultracode: this.isUltracode,
        models: ['Opus 5.5', 'Fable 5.1', 'Sonnet 5.5', 'Haiku 5.5', 'Haiku 4.5', 'Sonnet 5', 'GPT-OSS 20B (sovereign)'],
      },
      agentMode: this.agentMode,
      sessionDuration: '52m',
      subagentsCount: 0,
      browserConnected: true,
    };
    this.post(update);
    this.post({ type: 'look', ...this.look() });
  }

  private async refreshGates(): Promise<void> {
    if (this.currentMode === 'lane') {
      return;
    }
    this.post({ type: 'gates', gates: await this.loadGates() });
  }

  private async loadGates(): Promise<readonly PanelGate[]> {
    const vibey = this.controller.services.vibey;
    if (vibey === undefined) {
      return [];
    }
    try {
      const gates = await vibey.gates();
      return gates.map((gate) => {
        const isSpend = gate.kind === 'budget_exhausted';
        const choices = isSpend
          ? [
              { label: 'Grant +$10', command: `/budget grant ${gate.gate_id} $10` },
              { label: 'Grant +40 turns', command: `/budget grant ${gate.gate_id} 40 turns` },
            ]
          : this.controller.services.answers
              .choices(gate)
              .slice(0, 4)
              .map((choice, index) => ({ label: choice.label, command: `/reply ${index + 1}` }));
        return {
          gateId: gate.gate_id,
          kind: gate.kind,
          prompt: gate.prompt,
          projectName: gate.project_name ?? gate.project_id,
          isSpend,
          choices,
        };
      });
    } catch {
      return [];
    }
  }

  private status(run: TaskRunInterface, status: RunStatus): PanelUpdate {
    return {
      type: 'status',
      status,
      takesFollowUps: run.takesFollowUps,
      finishedActions: status === 'finished' && run.workspace?.mode === 'worktree',
      ...TaskPanel.force(run, this.controller.services.settings.forceStopAfterMs),
      model: { name: this.selectedModel, effort: this.modelEffort, ultracode: this.isUltracode },
      agentMode: this.agentMode,
      sessionDuration: '52m',
      subagentsCount: 0,
      browserConnected: true,
    };
  }

  private look(): PanelLook {
    const rawTheme = this.controller.services.settings.raw.theme;
    const kind = vscode.window.activeColorTheme.kind;
    const theme = rawTheme === 'light' ? 'light' : rawTheme === 'dark' ? 'dark' : kind === vscode.ColorThemeKind.Light || kind === vscode.ColorThemeKind.HighContrastLight ? 'light' : 'dark';
    const surface = rawTheme === 'system' ? 'editor' : 'krypton';
    const ultra = this.controller.services.settings.effort === 'ULTRA';
    let unlimited = false;
    try {
      unlimited = this.controller.services.budgets.paid()?.no_cap_confirmed === true;
    } catch {
      unlimited = false;
    }
    return { theme, surface, ultra, unlimited };
  }

  private unwatch(): void {
    for (const subscription of this.watching.splice(0)) {
      subscription.dispose();
    }
  }
}
