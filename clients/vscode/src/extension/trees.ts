// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The six views in the krypton activity bar: Model, Tasks, Lanes, Projects, Gates and Budgets.
 * Each view is one `VibeyTree` over a source; every item's look, and the `contextValue` its
 * menu is chosen by, comes from `TreeItems`, so a view can never offer a command that its
 * item cannot take. Everything a model or vibey wrote is shown as a label, never as markup.
 * Declared by `interfaces/trees-interface.ts`.
 */
import * as vscode from 'vscode';
import type { BudgetCaps } from '@vibey/core';
import type { RunStatus } from '@vibey/core';
import { VibeyCliError } from '@vibey/core';
import type { VibeyController } from './controller';
import type { TreeElement, TreeItemsInterface, TreeSourceInterface, VibeyTreeInterface } from './interfaces/trees-interface';

export class VibeyTree implements VibeyTreeInterface {
  private readonly changes = new vscode.EventEmitter<TreeElement | undefined>();
  readonly onDidChangeTreeData = this.changes.event;

  constructor(
    private readonly source: TreeSourceInterface,
    private readonly items: TreeItemsInterface,
  ) {}

  refresh(): void {
    this.changes.fire(undefined);
  }

  getTreeItem(element: TreeElement): vscode.TreeItem {
    return this.items.item(element);
  }

  async getChildren(element?: TreeElement): Promise<TreeElement[]> {
    if (element === undefined) {
      try {
        return [...(await this.source.roots())];
      } catch (error) {
        return [{ kind: 'info', label: 'Could not be read', description: (error as Error).message, icon: 'warning' }];
      }
    }
    return element.kind === 'info' ? [...(element.children ?? [])] : [];
  }
}

/** The model this computer runs, whether it is ready, and the loop, effort and engine chosen. */
export class ModelSource implements TreeSourceInterface {
  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    const services = this.controller.services;
    const { settings } = services;
    const [status, catalogue] = await Promise.all([services.probe.status(settings.model, settings.contextWindow), services.catalogue()]);
    const advice = services.advice.advice(status, services.platform);
    const roots: TreeElement[] = [
      {
        kind: 'info',
        label: 'Ollama',
        description: status.reachable ? `${status.version ?? ''} at ${status.root}` : `not answering at ${status.root}`,
        tooltip: [services.advice.summary(status), ...advice].join('\n'),
        icon: status.reachable ? 'pass' : 'error',
        ...(status.reachable ? {} : { command: { command: 'vibey.startOllama', title: 'Start Ollama' } }),
      },
      {
        kind: 'info',
        label: settings.model,
        description: status.modelPresent === true ? 'downloaded' : status.modelPresent === false ? 'not downloaded: click to download' : 'unknown',
        tooltip: `The model tasks use (${settings.modelSource}).`,
        icon: status.modelPresent === true ? 'symbol-class' : 'cloud-download',
        ...(status.modelPresent === false ? { command: { command: 'vibey.pullModel', title: 'Download the model' } } : {}),
      },
      {
        kind: 'info',
        label: 'Context window',
        description:
          status.contextCheck === 'ok'
            ? `${status.loaded?.contextLength?.toLocaleString('en-US')} loaded; tasks plan for ${settings.contextWindow.toLocaleString('en-US')}`
            : status.contextCheck === 'too-small'
              ? `too small: ${status.loaded?.contextLength?.toLocaleString('en-US')} loaded, tasks plan for ${settings.contextWindow.toLocaleString('en-US')}`
              : `unknown until the model is loaded; tasks plan for ${settings.contextWindow.toLocaleString('en-US')}`,
        icon: status.contextCheck === 'too-small' ? 'warning' : 'symbol-ruler',
      },
      {
        kind: 'info',
        label: 'Loop',
        description: `${settings.loop} · effort ${settings.effort} · engine ${settings.engine}`,
        tooltip: 'Click to choose the loop. The effort and the engine have their own commands.',
        icon: 'server-environment',
        command: { command: 'vibey.chooseLoop', title: 'Choose the loop' },
      },
    ];
    if (catalogue.notice !== undefined) {
      roots.push({ kind: 'info', label: 'vibey loops', description: 'not available', tooltip: catalogue.notice, icon: 'warning' });
    }
    const next = this.controller.next;
    if (next.attachments.length > 0 || next.plugins.length > 0) {
      roots.push({
        kind: 'info',
        label: 'Next task takes',
        description: [
          next.attachments.length > 0 ? `${next.attachments.length} attachment(s)` : '',
          next.plugins.length > 0 ? `context from ${next.plugins.join(', ')}` : '',
        ]
          .filter((part) => part !== '')
          .join(' · '),
        icon: 'paperclip',
        children: next.attachments.map((attachment) => ({ kind: 'info', label: attachment.name, description: attachment.kind, icon: 'file' })),
      });
    }
    return roots;
  }
}

/** Tasks this window started, then the finished ones the journal keeps, newest first. */
export class TasksSource implements TreeSourceInterface {
  static readonly FINISHED_SHOWN = 30;

  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    const live = [...this.controller.runs.values()].reverse();
    const shown = new Set(live.map((run) => run.runId));
    const finished = this.controller
      .finished()
      .filter((entry) => !shown.has(entry.record.run_id))
      .slice(0, TasksSource.FINISHED_SHOWN);
    return [
      ...live.map((run): TreeElement => ({ kind: 'run', runId: run.runId })),
      ...finished.map(
        (entry): TreeElement => ({
          kind: 'record',
          record: entry.record,
          ...(entry.applied === undefined ? {} : { applied: entry.applied }),
          ...(entry.discarded === undefined ? {} : { discarded: entry.discarded }),
        }),
      ),
    ];
  }
}

export class LanesSource implements TreeSourceInterface {
  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    return (await this.controller.lanes()).map((lane): TreeElement => ({ kind: 'lane', lane }));
  }
}

/** Says plainly when vibey is missing, or too old for a command, instead of an empty view. */
class VibeyMissing {
  static element(error: unknown): TreeElement {
    const message = (error as Error).message;
    return {
      kind: 'info',
      label: error instanceof VibeyCliError && error.kind === 'missing-command' ? 'This vibey is too old' : 'vibey did not answer',
      description: message,
      tooltip: message,
      icon: 'warning',
      command: { command: 'vibey.doctor', title: 'Check my setup' },
    };
  }

  static absent(): TreeElement {
    return {
      kind: 'info',
      label: 'vibey was not found',
      description: 'install it (pip install vibey-engine) or set vibey.cliPath',
      icon: 'warning',
      command: { command: 'vibey.doctor', title: 'Check my setup' },
    };
  }
}

export class ProjectsSource implements TreeSourceInterface {
  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    const vibey = this.controller.services.vibey;
    if (vibey === undefined) {
      return [VibeyMissing.absent()];
    }
    try {
      const projects = await vibey.projects();
      return projects.length === 0
        ? [{ kind: 'info', label: 'No vibey projects yet', description: 'start one with vibey new', icon: 'info' }]
        : projects.map((project): TreeElement => ({ kind: 'project', project }));
    } catch (error) {
      return [VibeyMissing.element(error)];
    }
  }
}

export class GatesSource implements TreeSourceInterface {
  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    const vibey = this.controller.services.vibey;
    if (vibey === undefined) {
      return [VibeyMissing.absent()];
    }
    try {
      const gates = await vibey.gates();
      return gates.length === 0
        ? [{ kind: 'info', label: 'No gate is waiting for you', icon: 'check' }]
        : gates.map((gate): TreeElement => ({ kind: 'gate', gate }));
    } catch (error) {
      return [VibeyMissing.element(error)];
    }
  }
}

/** vibey projects' cycle caps, and this computer's own lane budgets, with what each has spent. */
export class BudgetsSource implements TreeSourceInterface {
  constructor(private readonly controller: VibeyController) {}

  async roots(): Promise<readonly TreeElement[]> {
    const services = this.controller.services;
    const lanes: TreeElement[] = services.budgets.list().map((budget): TreeElement => {
      const usage = services.guard.usage(budget);
      return {
        kind: 'lane-budget',
        budget,
        exhausted: usage?.exhausted !== undefined,
        spent: usage === undefined ? 'per run' : BudgetsSource.spent(usage.spent, budget.caps),
      };
    });
    const paid = services.budgets.paid();
    const machine: TreeElement = {
      kind: 'info',
      label: "This computer's lanes",
      description: paid === undefined ? 'paidloop not declared' : paid.no_cap_confirmed === true ? 'paidloop declared with no cap' : 'paidloop declared',
      icon: 'vm',
      children: lanes.length === 0 ? [{ kind: 'info', label: 'No budgets', description: 'add one with the + button', icon: 'info' }] : lanes,
    };
    const vibey = services.vibey;
    let projects: readonly TreeElement[];
    if (vibey === undefined) {
      projects = [VibeyMissing.absent()];
    } else {
      try {
        projects = (await vibey.budgets()).map((budget): TreeElement => ({ kind: 'project-budget', budget }));
      } catch (error) {
        projects = [VibeyMissing.element(error)];
      }
    }
    return [machine, { kind: 'info', label: 'vibey projects', icon: 'project', children: projects }];
  }

  static spent(spent: Readonly<Record<keyof BudgetCaps, number>>, caps: BudgetCaps): string {
    const parts: string[] = [];
    if (caps.dollars !== undefined) {
      parts.push(`$${spent.dollars.toFixed(2)} of $${caps.dollars.toFixed(2)}`);
    }
    if (caps.turns !== undefined) {
      parts.push(`${spent.turns} of ${caps.turns} turns`);
    }
    if (caps.minutes !== undefined) {
      parts.push(`${Math.round(spent.minutes)} of ${caps.minutes} minutes`);
    }
    return parts.join(' · ');
  }
}

/** How each kind of item looks, and which menu it gets. */
export class TreeItems implements TreeItemsInterface {
  constructor(private readonly controller: VibeyController) {}

  item(element: TreeElement): vscode.TreeItem {
    switch (element.kind) {
      case 'info':
        return this.info(element);
      case 'run':
        return this.run(element);
      case 'record':
        return this.record(element);
      case 'lane': {
        const lane = element.lane;
        const item = new vscode.TreeItem(lane.label, vscode.TreeItemCollapsibleState.None);
        const minutes = Math.round((Date.now() - lane.startedAt) / 60_000);
        item.description = [
          lane.outcome ?? lane.state,
          `turn ${lane.turn}`,
          ...(lane.tool === undefined ? [] : [`running ${lane.tool}`]),
          `${minutes} min`,
          `${(lane.inputTokens + lane.outputTokens).toLocaleString('en-US')} tokens`,
        ].join(' · ');
        item.tooltip = `${lane.cwd}\n${lane.eventsPath}`;
        item.contextValue = `vibey.lane.${lane.state}`;
        item.iconPath =
          lane.state === 'running'
            ? TreeItems.live('vibey.stateRunning')
            : new vscode.ThemeIcon(lane.state === 'quiet' ? 'watch' : 'pass', new vscode.ThemeColor(lane.state === 'quiet' ? 'vibey.stateQueued' : 'vibey.stateSucceeded'));
        item.command = { command: 'vibey.openLane', title: 'Watch this lane', arguments: [element] };
        return item;
      }
      case 'project': {
        const project = element.project;
        const item = new vscode.TreeItem(project.name, vscode.TreeItemCollapsibleState.None);
        item.description = [
          project.phase,
          ...(project.cycle === undefined ? [] : [`cycle ${project.cycle}${project.max_cycles === undefined ? '' : ` of ${project.max_cycles}`}`]),
          ...(project.open_gates ? [`${project.open_gates} open gate(s)`] : []),
        ].join(' · ');
        item.tooltip = `${project.project_id}${project.repo_path === undefined ? '' : `\n${project.repo_path}`}`;
        item.contextValue = 'vibey.project';
        item.iconPath = new vscode.ThemeIcon('project');
        item.command = { command: 'vibey.showStatus', title: "Show this project's status", arguments: [element] };
        return item;
      }
      case 'gate': {
        const gate = element.gate;
        const item = new vscode.TreeItem(`${gate.kind}: ${gate.prompt.split('\n')[0] ?? ''}`, vscode.TreeItemCollapsibleState.None);
        item.description = gate.project_name ?? gate.project_id;
        item.tooltip = `${gate.prompt}\n\n${gate.answer_with ?? `vibey answer ${gate.gate_id}`}`;
        item.contextValue = gate.kind === 'budget_exhausted' ? 'vibey.gate.budget' : 'vibey.gate';
        item.iconPath = new vscode.ThemeIcon(gate.kind === 'budget_exhausted' ? 'credit-card' : 'question');
        item.command = { command: 'vibey.answerGate', title: 'Answer this gate', arguments: [element] };
        return item;
      }
      case 'lane-budget': {
        const budget = element.budget;
        const label = budget.label ?? `${budget.scope === 'run' ? 'Per run' : budget.scope === 'day' ? 'Daily' : 'Monthly'} · ${budget.loop}${budget.engine_id === undefined ? '' : ` · ${budget.engine_id}`}`;
        const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
        item.description = `${element.spent}${element.exhausted ? ' · used up' : ''}`;
        item.tooltip = `Budget ${budget.id}: ${JSON.stringify(budget.caps)}`;
        item.contextValue = `vibey.budget.lane${element.exhausted ? '.exhausted' : ''}`;
        item.iconPath = new vscode.ThemeIcon(element.exhausted ? 'warning' : 'graph');
        return item;
      }
      case 'project-budget': {
        const budget = element.budget;
        const item = new vscode.TreeItem(budget.name, vscode.TreeItemCollapsibleState.None);
        const parts = [
          budget.caps.max_cycle_dollars === null ? `$${budget.spend.dollars.toFixed(2)}, no dollar cap` : `$${budget.spend.dollars.toFixed(2)} of $${budget.caps.max_cycle_dollars.toFixed(2)}`,
          budget.caps.max_cycle_turns === null ? `${budget.spend.turns} turns, no turn cap` : `${budget.spend.turns} of ${budget.caps.max_cycle_turns} turns`,
        ];
        item.description = `${parts.join(' · ')}${budget.exhausted ? ' · used up' : ''}`;
        item.tooltip = `${budget.project_id}${budget.cycle === undefined ? '' : `, cycle ${budget.cycle}`}`;
        item.contextValue = `vibey.budget.project${budget.exhausted ? '.exhausted' : ''}`;
        item.iconPath = new vscode.ThemeIcon(budget.exhausted ? 'warning' : 'graph');
        return item;
      }
    }
  }

  private info(element: Extract<TreeElement, { kind: 'info' }>): vscode.TreeItem {
    const item = new vscode.TreeItem(
      element.label,
      element.children === undefined ? vscode.TreeItemCollapsibleState.None : vscode.TreeItemCollapsibleState.Expanded,
    );
    if (element.description !== undefined) {
      item.description = element.description;
    }
    if (element.tooltip !== undefined) {
      item.tooltip = element.tooltip;
    }
    if (element.icon !== undefined) {
      item.iconPath = new vscode.ThemeIcon(element.icon);
    }
    if (element.command !== undefined) {
      item.command = element.command;
    }
    return item;
  }

  private run(element: Extract<TreeElement, { kind: 'run' }>): vscode.TreeItem {
    const run = this.controller.runs.get(element.runId);
    const item = new vscode.TreeItem(run?.request.title ?? element.runId, vscode.TreeItemCollapsibleState.None);
    if (run === undefined) {
      return item;
    }
    const current = run.current;
    item.description = [TreeItems.words(run.status), ...(current === undefined ? [] : [`${current.engine} on ${current.model ?? 'its model'}`])].join(' · ');
    item.tooltip = run.workspace === undefined ? run.request.title : `${run.request.title}\n${run.workspace.cwd}${run.workspace.branch === undefined ? '' : `\n${run.workspace.branch}`}`;
    item.contextValue = `vibey.run.${TreeItems.menu(run.status)}`;
    item.iconPath =
      run.status === 'finished'
        ? new vscode.ThemeIcon('pass', new vscode.ThemeColor('vibey.stateSucceeded'))
        : run.status === 'queued'
          ? new vscode.ThemeIcon('clock', new vscode.ThemeColor('vibey.stateQueued'))
          : run.status === 'stopping'
            ? new vscode.ThemeIcon('debug-stop', new vscode.ThemeColor('vibey.stateAwaitingHuman'))
            : TreeItems.live(this.controller.services.settings.effort === 'ULTRA' ? 'vibey.ultraEffort' : 'vibey.stateRunning');
    item.command = { command: 'vibey.openRunLog', title: 'Open this task', arguments: [element] };
    return item;
  }

  private record(element: Extract<TreeElement, { kind: 'record' }>): vscode.TreeItem {
    const record = element.record;
    const item = new vscode.TreeItem(record.title, vscode.TreeItemCollapsibleState.None);
    const done = element.applied !== undefined ? 'applied' : element.discarded !== undefined ? 'discarded' : undefined;
    item.description = [record.outcome, ...(record.engine === undefined ? [] : [record.engine]), ...(done === undefined ? [] : [done])].join(' · ');
    item.tooltip = [
      record.branch === undefined ? record.cwd ?? '' : `${record.branch} (${record.base_sha?.slice(0, 12) ?? ''}..${record.head_sha?.slice(0, 12) ?? ''})`,
      record.diff_stat,
      record.error ?? record.failure?.explanation ?? record.commit_error ?? '',
    ]
      .filter((line) => line !== '')
      .join('\n');
    item.contextValue = 'vibey.run.finished';
    item.iconPath = new vscode.ThemeIcon(
      record.outcome.startsWith('completed')
        ? record.outcome === 'completed-commit-refused' || record.outcome === 'completed-out-of-scope'
          ? 'warning'
          : 'pass'
        : record.outcome === 'wound-down'
          ? 'debug-stop'
          : 'error',
    );
    item.command = { command: 'vibey.openRunLog', title: 'Open this task', arguments: [element] };
    return item;
  }

  /**
   * A live lane or task moves: a spinning icon in the state's colour from the design tokens.
   * With the editor's reduced motion on (`workbench.reduceMotion`), it holds still.
   */
  static live(colour: string): vscode.ThemeIcon {
    const reduced = vscode.workspace.getConfiguration('workbench').get<string>('reduceMotion') === 'on';
    return new vscode.ThemeIcon(reduced ? 'circle-filled' : 'loading~spin', new vscode.ThemeColor(colour));
  }

  /** The menu a run's state earns: queued, running, stopping or finished. */
  static menu(status: RunStatus): 'queued' | 'running' | 'stopping' | 'finished' {
    switch (status) {
      case 'queued':
        return 'queued';
      case 'stopping':
        return 'stopping';
      case 'finishing':
      case 'finished':
        return 'finished';
      default:
        return 'running';
    }
  }

  static words(status: RunStatus): string {
    const words: Record<RunStatus, string> = {
      queued: 'waiting its turn',
      preparing: 'making its copy',
      waiting: 'waiting for the model',
      running: 'running',
      stopping: 'stopping',
      finishing: 'finishing',
      finished: 'finished',
    };
    return words[status];
  }
}
