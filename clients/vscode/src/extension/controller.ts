// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One window's state: the core (built from the `vibey.*` settings, and built again when they
 * change), the tasks this window started, and what the next task takes with it. Views, the
 * task panel, the command menu and `@vibey` all read it, so they always agree. Declared by
 * `interfaces/controller-interface.ts`.
 */
import * as os from 'node:os';
import * as vscode from 'vscode';
import type { CapabilityMenu } from '@vibey/core';
import type { Lane } from '@vibey/core';
import type { RunItem } from '@vibey/core';
import type { RunRecord, TaskRunInterface } from '@vibey/core';
import type { LaneTracker } from '../core/lanes';
import { CoreServices } from '../core/services';
import type { EditorSettings } from './editor-settings';
import type { NextTask, VibeyControllerInterface } from './interfaces/controller-interface';

export class VibeyController implements VibeyControllerInterface {
  readonly runs = new Map<string, TaskRunInterface>();
  readonly next: NextTask = { attachments: [], plugins: [] };
  readonly output: vscode.OutputChannel;
  private readonly changes = new vscode.EventEmitter<void>();
  readonly onDidChange = this.changes.event;
  private core: CoreServices;
  private tracker: Promise<LaneTracker> | undefined;
  private timer: NodeJS.Timeout | undefined;

  constructor(
    context: vscode.ExtensionContext,
    private readonly settings: EditorSettings,
  ) {
    this.output = vscode.window.createOutputChannel('Vibey');
    this.core = this.build();
    context.subscriptions.push(
      this.output,
      this.changes,
      settings.onChange(() => {
        // Runs already going keep the core they started with; new ones get the new settings.
        this.core = this.build();
        this.tracker = undefined;
        this.schedule();
        this.changed();
      }),
      { dispose: () => this.timer !== undefined && clearInterval(this.timer) },
    );
    this.schedule();
  }

  /** The core as the settings are now. */
  get services(): CoreServices {
    return this.core;
  }

  get editorSettings(): EditorSettings {
    return this.settings;
  }

  changed(): void {
    this.changes.fire();
  }

  folder(): string | undefined {
    const active = vscode.window.activeTextEditor?.document.uri;
    const owner = active === undefined ? undefined : vscode.workspace.getWorkspaceFolder(active);
    return (owner ?? vscode.workspace.workspaceFolders?.[0])?.uri.fsPath;
  }

  async ask(task: string): Promise<TaskRunInterface | undefined> {
    const directory = this.folder();
    if (directory === undefined) {
      void vscode.window.showWarningMessage('Open a folder that is a git repository first: a task works on a copy of it.');
      return undefined;
    }
    const services = this.core;
    const { settings } = services;
    const title = services.naming.title(task);
    const contextPacket = await this.packet(title, task);
    const run = await services.start({
      task,
      title,
      directory,
      inPlace: settings.runInPlace,
      baseRef: settings.baseRef,
      loop: settings.loop,
      effort: settings.effort,
      baseEffort: settings.baseEffort,
      engine: settings.engine,
      contextWindow: settings.contextWindow,
      commitMessage: `chore(vibey): ${title}`,
      slugSource: title,
      origin: 'ask',
      attachments: [...this.next.attachments],
      ...(contextPacket === undefined ? {} : { contextPacket }),
    });
    this.next.attachments = [];
    this.next.plugins = [];
    this.track(run);
    return run;
  }

  track(run: TaskRunInterface): void {
    this.runs.set(run.runId, run);
    run.onStatus(() => this.changed());
    void run.result.then(() => this.changed());
    this.changed();
  }

  async menu(): Promise<CapabilityMenu> {
    const services = this.core;
    const { settings } = services;
    const catalogue = await services.catalogue();
    const loop = catalogue.loops.find((candidate) => candidate.loop === settings.loop) ?? catalogue.loops[0];
    const [wanted, named] = settings.engine.split('/');
    const runnable = loop?.engines.filter((candidate) => !candidate.repealed);
    const engine = runnable?.find((candidate) => candidate.engine_id === wanted) ?? runnable?.find((candidate) => candidate.enabled);
    if (loop === undefined || engine === undefined) {
      return { attachImage: false, pasteImage: false, attachFile: false, pasteText: true, notes: ['No engine of this loop is switched on.'] };
    }
    // Ollama says what a local model can do; a paid engine's own capabilities stand for its models.
    const abilities = loop.tier === 'local' ? await services.probe.capabilities(named ?? settings.model) : undefined;
    return services.capabilities.menu(engine.capabilities, loop.tier, abilities);
  }

  finished(): readonly { readonly record: RunRecord; readonly applied?: string; readonly discarded?: string }[] {
    try {
      return this.core.history.list();
    } catch {
      return [];
    }
  }

  async lanes(): Promise<readonly Lane[]> {
    return (await this.laneTracker()).refresh();
  }

  async laneItems(eventsPath: string): Promise<readonly RunItem[]> {
    const tracker = await this.laneTracker();
    tracker.refresh();
    return tracker.items(eventsPath);
  }

  /** The vibey-skills context the next task asked for, compiled for this task; none when it asked for none. */
  private async packet(title: string, task: string): Promise<{ markdown: string; plugins: readonly string[]; manifest: string } | undefined> {
    if (this.next.plugins.length === 0) {
      return undefined;
    }
    const skills = this.core.skills;
    if (skills === undefined) {
      void vscode.window.showWarningMessage('vibey-skills was not found, so this task runs without plugin context. It ships with vibey.');
      return undefined;
    }
    const packet = await skills.packet({ title, objective: task, plugins: this.next.plugins });
    if (!packet.ok) {
      void vscode.window.showWarningMessage(`The plugin context could not be made, so this task runs without it: ${packet.error}`);
      return undefined;
    }
    return { markdown: packet.markdown, plugins: packet.plugins, manifest: packet.manifest };
  }

  private laneTracker(): Promise<LaneTracker> {
    const core = this.core;
    this.tracker ??= core.catalogue().then((catalogue) => core.lanes(catalogue));
    return this.tracker;
  }

  private build(): CoreServices {
    return new CoreServices({
      raw: this.settings.raw(),
      environ: process.env,
      platform: process.platform,
      actor: `${os.userInfo().username} (VS Code)`,
      workspaceRoots: () => (vscode.workspace.workspaceFolders ?? []).map((folder) => folder.uri.fsPath),
    });
  }

  /** Views look again every `vibey.refreshSeconds`; a running task's panel follows it as it happens. */
  private schedule(): void {
    if (this.timer !== undefined) {
      clearInterval(this.timer);
    }
    this.timer = setInterval(() => this.changed(), this.core.settings.refreshMs);
  }
}
