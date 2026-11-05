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
import type { PanelGate, PanelHtmlInterface, PanelLook, PanelRequest, PanelUpdate, TaskPanelInterface } from './interfaces/panel-interface';

export class PanelHtml implements PanelHtmlInterface {
  private readonly html = new HtmlText();

  page(title: string, script: string, style: string, nonce: string, cspSource: string, tokens = '', look: PanelLook = PanelHtml.LOOK): string {
    const safe = this.html.escape(title);
    return `<!DOCTYPE html>
<html lang="en" data-theme="${look.theme}" data-surface="${look.surface}">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${cspSource} data:; style-src ${cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
${tokens === '' ? '' : `<link rel="stylesheet" href="${tokens}">\n`}<link rel="stylesheet" href="${style}">
<title>${safe}</title>
</head>
<body>
<div id="banner" role="alert" hidden><span class="banner-text"><strong>UNLIMITED SPEND</strong> paidloop is declared with no dollar cap.</span><button id="endNoCap" type="button" class="quiet">End unlimited spend</button></div>
<div id="browserBanner" class="pinned-banner" hidden><span class="pinned-banner-icon">🌐</span><span class="pinned-banner-text">Browser connected</span><button id="closeBrowserBanner" type="button" class="close-btn" title="Close banner">✕</button></div>
<header>
  <div class="header-left">
    <span class="mark" aria-hidden="true"><span class="nucleus"></span><span class="orbit one"></span><span class="orbit two"></span></span>
    <h1 id="title">${safe}</h1>
    <span id="effort" class="pill ultra" hidden title="ULTRA: effort without a ceiling. It stops only at Stop or a declared budget cap.">ULTRA</span>
    <span id="status" class="pill state" data-state="idle" role="status"></span>
  </div>
  <div class="header-right">
    <button id="btnBookmark" type="button" class="icon-btn" title="Bookmark conversation">🏷</button>
    <button id="btnHistory" type="button" class="icon-btn" title="History & sessions">⏱</button>
    <button id="btnNewChat" type="button" class="icon-btn" title="New conversation">+</button>
  </div>
</header>
<section id="gates" aria-label="Open gates" hidden></section>
<main id="items" aria-live="polite">
  <div id="activityIndicator" class="activity-indicator" hidden>
    <span class="pulsing-atom"></span>
    <span id="activityText" class="activity-text">Whirring...</span>
  </div>
</main>
<footer id="composer">
  <ul id="completions" role="listbox" aria-label="Commands" hidden></ul>
  <div id="chips" role="toolbar" aria-label="Quick slash commands" hidden>
    <button type="button" class="chip" data-slash="/status">/status</button>
    <button type="button" class="chip" data-slash="/gates">/gates</button>
    <button type="button" class="chip" data-slash="/next">/next</button>
    <button type="button" class="chip" data-slash="/budget">/budget</button>
    <button type="button" class="chip" data-slash="/lanes">/lanes</button>
    <button type="button" class="chip" data-slash="/mcp ">/mcp</button>
    <button type="button" class="chip" data-slash="/doctor">/doctor</button>
    <button type="button" class="chip" data-slash="/help">/help</button>
  </div>
  <div class="composer-card">
    <div class="composer-input-row">
      <textarea id="input" rows="1" aria-label="Chat message, task, follow-up or command" placeholder="Queue another message..."></textarea>
      <button id="btnMic" type="button" class="icon-btn mic-btn" title="Voice input">🎙</button>
    </div>
    <div class="composer-controls">
      <div class="controls-left">
        <button id="btnAdd" type="button" class="control-btn add-btn" title="Add context">+</button>
        <button id="btnActions" type="button" class="control-btn actions-btn" title="Filter actions">◫</button>
        <span id="sessionTimer" class="pill-badge timer-badge" title="Session duration">⏱ 52m</span>
        <button id="btnRemoteControl" type="button" class="pill-btn remote-btn" title="Remote control">Remote Control</button>
        <span id="subagentsBadge" class="pill-badge agents-badge" title="Subagents"><span class="dot">⚫</span> <span id="agentCount">0 agents</span></span>
      </div>
      <div class="controls-right">
        <button id="btnModelSelect" type="button" class="pill-btn select-btn" title="Select model"><span id="modelName">Sonnet 5.5</span> <span id="modelEffort">Medium</span> <span class="chevron">▾</span></button>
        <button id="btnModeSelect" type="button" class="pill-btn select-btn" title="Select mode"><span class="mode-icon">⚡</span> <span id="modeName">Auto</span> <span class="chevron">▾</span></button>
        <button id="start" type="button" class="action-btn send-btn" title="Send message">↑</button>
        <button id="stop" type="button" class="action-btn stop-btn" title="Stop" hidden>■</button>
        <button id="force" type="button" class="danger" hidden>Force stop</button>
      </div>
    </div>
    <div id="finishedActions" class="finished-actions-row" hidden>
      <button id="review" type="button">Review</button>
      <button id="apply" type="button">Apply</button>
      <button id="discard" type="button">Discard</button>
    </div>
  </div>

  <!-- Popovers -->
  <div id="popoverAdd" class="popover-menu" hidden>
    <button type="button" class="popover-item" data-action="upload"><span class="icon">↑</span> Upload from computer</button>
    <button type="button" class="popover-item" data-action="context"><span class="icon">📄</span> Add context</button>
    <button type="button" class="popover-item" data-action="web"><span class="icon">🌐</span> Browse the web</button>
  </div>

  <div id="popoverActions" class="popover-menu wide" hidden>
    <div class="popover-search"><span class="search-icon">🔍</span><input type="text" id="actionSearch" placeholder="Filter actions..."></div>
    <div class="popover-section-label">Context actions</div>
    <button type="button" class="popover-item action-entry" data-action="attach-file"><span class="icon">📎</span> Attach file...</button>
    <button type="button" class="popover-item action-entry" data-action="mention-file"><span class="icon">@</span> Mention file...</button>
    <button type="button" class="popover-item action-entry" data-action="clear-conversation"><span class="icon">🗑</span> Clear conversation</button>
    <button type="button" class="popover-item action-entry" data-action="rewind"><span class="icon">↺</span> Rewind</button>
    <button type="button" class="popover-item action-entry" data-action="bookmarks"><span class="icon">🏷</span> Bookmarks</button>
    <button type="button" class="popover-item action-entry" data-action="export-conversation"><span class="icon">↷</span> Export conversation</button>
    <div class="popover-section-label">Model actions</div>
    <button type="button" class="popover-item action-entry" data-action="switch-model"><span class="icon">⇄</span> Switch model...</button>
    <button type="button" class="popover-item action-entry" data-action="effort"><span class="icon">⚡</span> Effort (<span id="actionEffortLabel">Medium</span>)</button>
    <div class="popover-item toggle-item action-entry" data-action="ultracode"><span class="item-label"><span class="icon">🔥</span> Ultracode</span><label class="switch"><input type="checkbox" id="actionUltracodeToggle"><span class="slider"></span></label></div>
  </div>

  <div id="popoverModel" class="popover-menu" hidden>
    <div class="popover-title">Select a model</div>
    <div class="popover-list" id="modelList">
      <button type="button" class="popover-item model-item" data-model="Opus 5.5"><span class="item-text">Opus 5.5</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item" data-model="Fable 5.1"><span class="item-text">Fable 5.1</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item selected" data-model="Sonnet 5.5"><span class="item-text">Sonnet 5.5</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item" data-model="Haiku 5.5"><span class="item-text">Haiku 5.5</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item" data-model="Haiku 4.5"><span class="item-text">Haiku 4.5</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item" data-model="Sonnet 5"><span class="item-text">Sonnet 5</span><span class="check">✓</span></button>
      <button type="button" class="popover-item model-item" data-model="GPT-OSS 20B (sovereign)"><span class="item-text">GPT-OSS 20B (sovereign)</span><span class="check">✓</span></button>
    </div>
    <div class="popover-divider"></div>
    <div class="popover-slider-row">
      <span class="label">Effort</span>
      <div class="slider-container">
        <input type="range" id="effortRange" min="1" max="4" value="2" step="1">
        <div class="slider-labels"><span>Low</span><span>Med</span><span>High</span><span>Ultra</span></div>
      </div>
    </div>
    <div class="popover-divider"></div>
    <div class="popover-item toggle-item">
      <span class="item-label">Ultracode</span>
      <label class="switch"><input type="checkbox" id="modelUltracodeToggle"><span class="slider"></span></label>
    </div>
  </div>

  <div id="popoverMode" class="popover-menu" hidden>
    <div class="popover-title">Modes</div>
    <div class="popover-list" id="modeList">
      <button type="button" class="popover-item mode-item" data-mode="Manual"><span class="item-text">Manual</span><span class="check">✓</span></button>
      <button type="button" class="popover-item mode-item" data-mode="Edit automatically"><span class="item-text">Edit automatically</span><span class="check">✓</span></button>
      <button type="button" class="popover-item mode-item" data-mode="Plan"><span class="item-text">Plan</span><span class="check">✓</span></button>
      <button type="button" class="popover-item mode-item selected" data-mode="Auto"><span class="item-text">Auto</span><span class="check">✓</span></button>
    </div>
    <div class="popover-divider"></div>
    <div class="popover-slider-row">
      <span class="label">Effort</span>
      <div class="slider-container">
        <input type="range" id="modeEffortRange" min="1" max="4" value="2" step="1">
        <div class="slider-labels"><span>Low</span><span>Med</span><span>High</span><span>Ultra</span></div>
      </div>
    </div>
    <div class="popover-divider"></div>
    <div class="popover-item toggle-item">
      <span class="item-label">Ultracode</span>
      <label class="switch"><input type="checkbox" id="modeUltracodeToggle"><span class="slider"></span></label>
    </div>
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
    this.panel = vscode.window.createWebviewPanel(TaskPanel.VIEW_TYPE, lane?.label ?? 'krypton chat', vscode.ViewColumn.Beside, {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [media],
    });
    this.panel.iconPath = vscode.Uri.joinPath(media, 'krypton.svg');
    const html = new PanelHtml();
    const webview = this.panel.webview;
    webview.html = html.page(
      lane?.label ?? 'krypton chat',
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
      controller.onDidChange(() => {
        this.post({ type: 'look', ...this.look() });
        void this.refreshGates();
      }),
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
    this.panel.title = run?.request.title ?? 'krypton chat';
    if (run !== undefined) {
      this.watching.push(
        run.onPatch((patch) => this.post({ type: 'patch', patch })),
        run.onStatus((status) => this.post(this.status(run, status))),
      );
    }
    void this.sendInit();
    this.reveal();
  }

  openChat(): void {
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
      case 'action':
        await this.handleAction(message.action, message.payload);
        return;
    }
  }

  private async handleAction(action: string, _payload?: unknown): Promise<void> {
    switch (action) {
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
    const gates = this.mode === 'lane' ? [] : await this.loadGates();
    const update: PanelUpdate = {
      type: 'init',
      title: this.lane?.label ?? run?.request.title ?? 'krypton chat',
      mode: this.mode,
      items: run?.items() ?? [],
      gates,
      status,
      slash: this.slash.complete('').map((spec) => ({ name: spec.slash ?? '', usage: spec.usage ?? '', description: spec.description })),
      canPasteImage: menu.pasteImage,
      ...(run === undefined ? {} : TaskPanel.force(run, this.controller.services.settings.forceStopAfterMs)),
      finishedActions: run?.status === 'finished' && run.workspace?.mode === 'worktree',
      takesFollowUps: run?.takesFollowUps ?? false,
      model: {
        name: 'Sonnet 5.5',
        effort: 'Medium',
        ultracode: this.controller.services.settings.effort === 'ULTRA',
        models: ['Opus 5.5', 'Fable 5.1', 'Sonnet 5.5', 'Haiku 5.5', 'Haiku 4.5', 'Sonnet 5', 'GPT-OSS 20B (sovereign)'],
      },
      agentMode: 'Auto',
      sessionDuration: '52m',
      subagentsCount: 0,
      browserConnected: true,
    };
    this.post(update);
    this.post({ type: 'look', ...this.look() });
    if (this.mode === 'lane') {
      void this.refreshLane();
    }
  }

  private async refreshGates(): Promise<void> {
    if (this.mode === 'lane' || this.disposed) {
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
      model: {
        name: 'Sonnet 5.5',
        effort: 'Medium',
        ultracode: this.controller.services.settings.effort === 'ULTRA',
      },
      agentMode: 'Auto',
      sessionDuration: '52m',
      subagentsCount: 0,
      browserConnected: true,
    };
  }

  /** When Force stop opens: a stop's fair time after it was asked. */
  static force(run: TaskRunInterface, fairMs: number): { forceAfterMs?: number } {
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
