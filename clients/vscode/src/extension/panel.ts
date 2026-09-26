// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The task panel: one task's transcript as it happens, a box to type a task, a follow-up or a
 * `/` command in, and its buttons. A lane started elsewhere opens read-only in the same page.
 *
 * Everything shown came from a model, a tool, or vibey, so it is data: the page renders it
 * with `textContent` only (media/panel.js), and the one string placed into its HTML, the
 * title, is escaped. The content security policy allows no inline script and nothing from
 * the network: only this page's own script, by nonce, and its own stylesheets.
 *
 * Its look is the design system's (ADR-0066, the Beauty Law's bar): `media/tokens.css` is the
 * generated token sheet, and `media/panel.css` builds on it. In System mode the page sits on
 * the editor's own surfaces and follows its colour theme live; Light and Dark keep krypton's
 * own palette. Declared by `interfaces/panel-interface.ts`.
 */
import { randomBytes } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { SlashCommands } from '@vibey/core';
import type { RunStatus, TaskRunInterface } from '@vibey/core';
import { HtmlText } from '../core/support';
import type { VibeyController } from './controller';
import type { CommandActionsInterface } from './interfaces/actions-interface';
import type { PanelHtmlInterface, PanelLook, PanelRequest, PanelUpdate, TaskPanelInterface } from './interfaces/panel-interface';

export class PanelHtml implements PanelHtmlInterface {
  private readonly html = new HtmlText();

  page(title: string, script: string, style: string, nonce: string, cspSource: string, tokens = '', look: PanelLook = PanelHtml.LOOK): string {
    const safe = this.html.escape(title);
    return `<!DOCTYPE html>
<html lang="en" data-theme="${look.theme}" data-surface="${look.surface}">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${cspSource} data:; style-src ${cspSource}; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
${tokens === '' ? '' : `<link rel="stylesheet" href="${tokens}">\n`}<link rel="stylesheet" href="${style}">
<title>${safe}</title>
</head>
<body>
<div id="banner" role="alert" hidden><span class="banner-text"><strong>UNLIMITED SPEND</strong> paidloop is declared with no dollar cap.</span><button id="endNoCap" type="button" class="quiet">End unlimited spend</button></div>
<header>
  <span class="mark" aria-hidden="true"><span class="nucleus"></span><span class="orbit one"></span><span class="orbit two"></span></span>
  <h1 id="title">${safe}</h1>
  <span id="effort" class="pill ultra" hidden title="ULTRA: effort without a ceiling. It stops only at Stop or a declared budget cap.">ULTRA</span>
  <span id="status" class="pill state" data-state="idle" role="status"></span>
</header>
<main id="items" aria-live="polite"></main>
<footer id="composer">
  <ul id="completions" role="listbox" aria-label="Commands" hidden></ul>
  <textarea id="input" rows="3" aria-label="Task, follow-up or command" placeholder="Describe a task, or type / for commands. Enter sends; Shift+Enter starts a new line."></textarea>
  <div id="buttons">
    <button id="start" type="button">Start</button>
    <button id="stop" type="button" hidden>Stop</button>
    <button id="force" type="button" class="danger" hidden>Force stop</button>
    <button id="review" type="button" hidden>Review</button>
    <button id="apply" type="button" hidden>Apply</button>
    <button id="discard" type="button" hidden>Discard</button>
  </div>
</footer>
<script nonce="${nonce}" src="${script}"></script>
</body>
</html>`;
  }

  /** Before the editor says otherwise: dark, on the editor's own surfaces. */
  static readonly LOOK: PanelLook = { theme: 'dark', surface: 'editor', ultra: false, unlimited: false };

  nonce(): string {
    return randomBytes(18).toString('base64').replace(/[^A-Za-z0-9]/g, '');
  }
}

export class TaskPanel implements TaskPanelInterface {
  static readonly VIEW_TYPE = 'vibey.task';
  private readonly panel: vscode.WebviewPanel;
  private readonly watching: vscode.Disposable[] = [];
  private readonly watchingLook: vscode.Disposable[] = [];
  private readonly slash = new SlashCommands();
  private runId: string | undefined;
  private laneTimer: NodeJS.Timeout | undefined;
  private disposed = false;
  private readonly closed = new vscode.EventEmitter<void>();
  readonly onDidClose = this.closed.event;

  constructor(
    private readonly controller: VibeyController,
    private readonly actions: CommandActionsInterface,
    extensionUri: vscode.Uri,
    private readonly mode: 'task' | 'lane',
    private readonly lane?: { readonly eventsPath: string; readonly label: string },
  ) {
    const media = vscode.Uri.joinPath(extensionUri, 'media');
    this.panel = vscode.window.createWebviewPanel(TaskPanel.VIEW_TYPE, lane?.label ?? 'krypton task', vscode.ViewColumn.Beside, {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [media],
    });
    this.panel.iconPath = vscode.Uri.joinPath(media, 'vibey.svg');
    const html = new PanelHtml();
    const webview = this.panel.webview;
    webview.html = html.page(
      lane?.label ?? 'krypton task',
      webview.asWebviewUri(vscode.Uri.joinPath(media, 'panel.js')).toString(),
      webview.asWebviewUri(vscode.Uri.joinPath(media, 'panel.css')).toString(),
      html.nonce(),
      webview.cspSource,
      webview.asWebviewUri(vscode.Uri.joinPath(media, 'tokens.css')).toString(),
      this.look(),
    );
    // The look follows the editor's theme live in System mode, and the settings in every mode.
    this.watchingLook.push(
      vscode.window.onDidChangeActiveColorTheme(() => this.post({ type: 'look', ...this.look() })),
      controller.onDidChange(() => this.post({ type: 'look', ...this.look() })),
    );
    webview.onDidReceiveMessage((message: PanelRequest) => void this.receive(message));
    this.panel.onDidDispose(() => {
      this.disposed = true;
      for (const subscription of this.watchingLook.splice(0)) {
        subscription.dispose();
      }
      this.unwatch();
      this.closed.fire();
    });
    if (mode === 'lane') {
      this.laneTimer = setInterval(() => void this.refreshLane(), controller.services.settings.pollMs);
    }
  }

  get shownRunId(): string | undefined {
    return this.runId;
  }

  show(runId: string): void {
    this.unwatch();
    this.runId = runId;
    const run = this.controller.runs.get(runId);
    this.panel.title = run?.request.title ?? 'krypton task';
    if (run !== undefined) {
      this.watching.push(
        run.onPatch((patch) => this.post({ type: 'patch', patch })),
        run.onStatus((status) => this.post(this.status(run, status))),
      );
    }
    void this.sendInit();
    this.reveal();
  }

  note(level: 'info' | 'warn' | 'error', text: string): void {
    this.post({ type: 'note', level, text });
  }

  reveal(): void {
    this.panel.reveal(vscode.ViewColumn.Beside, true);
  }

  dispose(): void {
    this.panel.dispose();
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
    }
  }

  /** A `/` command runs from the one command table; text is a follow-up while the task runs, else a new task. */
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
    await this.actions.run('vibey.ask', { ...this.invocation(), args: parsed.text });
  }

  private invocation(): { say: (text: string) => void; panel: TaskPanelInterface; runId?: string } {
    return { say: (text) => this.note('info', text), panel: this, ...(this.runId === undefined ? {} : { runId: this.runId }) };
  }

  /** A pasted image is written where the run records live and attached to the next task. */
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
    const status = this.mode === 'lane' ? 'lane' : run === undefined ? (this.runId === undefined ? 'idle' : 'finished') : run.status;
    const update: PanelUpdate = {
      type: 'init',
      title: this.lane?.label ?? run?.request.title ?? 'krypton task',
      mode: this.mode,
      items: run?.items() ?? [],
      status,
      slash: this.slash.complete('').map((spec) => ({ name: spec.slash ?? '', usage: spec.usage ?? '', description: spec.description })),
      canPasteImage: menu.pasteImage,
      ...(run === undefined ? {} : TaskPanel.force(run, this.controller.services.settings.forceStopAfterMs)),
      finishedActions: run?.status === 'finished' && run.workspace?.mode === 'worktree',
      takesFollowUps: run?.takesFollowUps ?? false,
    };
    this.post(update);
    this.post({ type: 'look', ...this.look() });
    if (this.mode === 'lane') {
      void this.refreshLane();
    }
  }

  /**
   * Light, Dark or System (the Beauty Bar, item 2). System takes the editor's own theme kind
   * and its surfaces; Light and Dark take krypton's palette and surfaces whatever the editor uses.
   */
  private look(): PanelLook {
    const services = this.controller.services;
    let unlimited = false;
    try {
      unlimited = services.budgets.paid()?.no_cap_confirmed === true;
    } catch {
      unlimited = false;
    }
    const chosen = services.settings.theme;
    const kind = vscode.window.activeColorTheme.kind;
    const editorIsLight = kind === vscode.ColorThemeKind.Light || kind === vscode.ColorThemeKind.HighContrastLight;
    return {
      theme: chosen === 'system' ? (editorIsLight ? 'light' : 'dark') : chosen,
      surface: chosen === 'system' ? 'editor' : 'krypton',
      ultra: services.settings.effort === 'ULTRA',
      unlimited,
    };
  }

  private status(run: TaskRunInterface, status: RunStatus): PanelUpdate {
    return {
      type: 'status',
      status,
      ...TaskPanel.force(run, this.controller.services.settings.forceStopAfterMs),
      finishedActions: status === 'finished' && run.workspace?.mode === 'worktree',
      takesFollowUps: run.takesFollowUps,
    };
  }

  /** When Force stop opens: a stop's fair time after it was asked. */
  private static force(run: TaskRunInterface, fairMs: number): { forceAfterMs?: number } {
    const asked = run.stopRequestedAt;
    return asked === undefined ? {} : { forceAfterMs: Math.max(0, asked + fairMs - performance.now()) };
  }

  private async refreshLane(): Promise<void> {
    if (this.lane === undefined || this.disposed) {
      return;
    }
    this.post({ type: 'items', items: await this.controller.laneItems(this.lane.eventsPath) });
  }

  private post(update: PanelUpdate): void {
    if (!this.disposed) {
      void this.panel.webview.postMessage(update);
    }
  }

  private unwatch(): void {
    for (const subscription of this.watching.splice(0)) {
      subscription.dispose();
    }
    if (this.disposed && this.laneTimer !== undefined) {
      clearInterval(this.laneTimer);
    }
  }
}
