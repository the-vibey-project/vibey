// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Every command in the one command table, implemented once. The Command Palette, the views'
 * menus and buttons, the status-bar menu, the task panel's `/` commands and `@vibey` all call
 * `run`, so a command behaves the same wherever it was asked for; the constructor refuses to
 * start if a table command has no handler. Replies go where the command came from: a
 * notification, the panel, or the chat. Declared by `interfaces/actions-interface.ts`.
 */
import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { CommandTable, SlashArguments, SlashCommands } from '@vibey/core';
import { Doctor } from '@vibey/core';
import type { Budget, BudgetCaps, BudgetLoop, BudgetScope } from '@vibey/core';
import type { EffortSetting, LoopName } from '@vibey/core';
import type { Lane } from '@vibey/core';
import type { RunRecord, TaskRunInterface } from '@vibey/core';
import type { GateAnswer, VibeyBudget, VibeyGate, VibeyProject } from '@vibey/core';
import { ModelPuller } from '@vibey/core';
import type { VibeyController } from './controller';
import type { CommandActionsInterface, Invocation } from './interfaces/actions-interface';
import type { TreeElement } from './interfaces/trees-interface';
import { TaskPanel } from './panel';

type Handler = (invocation: Invocation) => Promise<void>;

export class CommandActions implements CommandActionsInterface {
  readonly ids: readonly string[];
  private readonly handlers: Readonly<Record<string, Handler>>;
  private readonly panels = new Map<string, TaskPanel>();
  private readonly slash = new SlashCommands();
  private readonly words = new SlashArguments();

  constructor(
    private readonly controller: VibeyController,
    private readonly extensionUri: vscode.Uri,
  ) {
    this.handlers = {
      'vibey.ask': (i) => this.ask(i),
      'vibey.followUp': (i) => this.followUp(i),
      'vibey.runBatch': (i) => this.runBatch(i),
      'vibey.stopRun': (i) => this.stopRun(i),
      'vibey.forceStopRun': (i) => this.forceStopRun(i),
      'vibey.openRunLog': (i) => this.openRunLog(i),
      'vibey.reviewRun': (i) => this.reviewRun(i),
      'vibey.applyRun': (i) => this.applyRun(i),
      'vibey.discardRun': (i) => this.discardRun(i),
      'vibey.attachFile': (i) => this.attach(i, 'file'),
      'vibey.attachImage': (i) => this.attach(i, 'image'),
      'vibey.pasteText': (i) => this.pasteText(i),
      'vibey.pasteImage': (i) => this.pasteImage(i),
      'vibey.plugins': (i) => this.plugins(i),
      'vibey.chooseLoop': (i) => this.chooseLoop(i),
      'vibey.chooseEffort': (i) => this.chooseEffort(i),
      'vibey.chooseModel': (i) => this.chooseModel(i),
      'vibey.showLoops': (i) => this.showLoops(i),
      'vibey.showLanes': () => this.focus('vibey.lanes'),
      'vibey.openLane': (i) => this.openLane(i),
      'vibey.startQueue': (i) => this.startQueue(i),
      'vibey.stopAll': (i) => this.stopAll(i),
      'vibey.refresh': (i) => this.refresh(i),
      'vibey.showProjects': () => this.focus('vibey.projects'),
      'vibey.showStatus': (i) => this.showStatus(i),
      'vibey.showGates': () => this.focus('vibey.gates'),
      'vibey.answerGate': (i) => this.answerGate(i),
      'vibey.bumpJob': (i) => this.bumpJob(i),
      'vibey.showBudgets': () => this.focus('vibey.budgets'),
      'vibey.addBudget': (i) => this.addBudget(i),
      'vibey.editBudget': (i) => this.editBudget(i),
      'vibey.removeBudget': (i) => this.removeBudget(i),
      'vibey.grantBudget': (i) => this.grantBudget(i),
      'vibey.startOllama': (i) => this.startOllama(i),
      'vibey.pullModel': (i) => this.pullModel(i),
      'vibey.doctor': (i) => this.doctor(i),
      'vibey.showMenu': (i) => this.showMenu(i),
    };
    const missing = CommandTable.ALL.map((spec) => spec.id).filter((id) => this.handlers[id] === undefined);
    if (missing.length > 0) {
      throw new Error(`The command table names commands with no handler: ${missing.join(', ')}`);
    }
    this.ids = Object.keys(this.handlers);
  }

  async run(id: string, invocation: Invocation): Promise<void> {
    const handler = this.handlers[id];
    if (handler === undefined) {
      invocation.say(`There is no command ${id}.`);
      return;
    }
    try {
      await handler(invocation);
    } catch (error) {
      invocation.say((error as Error).message);
    }
  }

  // --- Run -------------------------------------------------------------------------------

  private async ask(invocation: Invocation): Promise<void> {
    const task =
      invocation.args?.trim() ||
      (await vscode.window.showInputBox({
        title: 'Ask the model',
        prompt: 'What should it do? It works on a copy of this folder, so nothing changes until you Apply.',
        placeHolder: 'add a line to README.md that says how to run the tests',
        ignoreFocusOut: true,
      }));
    if (!task?.trim()) {
      return;
    }
    if (!(await this.paidReady())) {
      invocation.say('paidloop is not declared, so nothing was started. Choose sovereignloop, or declare paidloop with a cap.');
      return;
    }
    const run = await this.controller.ask(task.trim());
    if (run === undefined) {
      return;
    }
    (invocation.panel ?? this.panel(run.runId)).show(run.runId);
  }

  private async followUp(invocation: Invocation): Promise<void> {
    const run = await this.liveRun(invocation, (candidate) => candidate.status === 'running', 'Which running task?');
    if (run === undefined) {
      invocation.say('No task is running, so there is nothing to tell.');
      return;
    }
    const text = invocation.args?.trim() || (await vscode.window.showInputBox({ title: `Tell "${run.request.title}"`, prompt: 'The model reads it at the start of its next turn.', ignoreFocusOut: true }));
    if (!text?.trim()) {
      return;
    }
    invocation.say((await run.followUp(text)) ?? 'Sent. The model reads it at the start of its next turn.');
  }

  private async runBatch(invocation: Invocation): Promise<void> {
    const repository = this.controller.folder();
    if (repository === undefined) {
      invocation.say('Open the repository folder first: a batch works on copies of it.');
      return;
    }
    let directory = invocation.args?.trim() ? CommandActions.home(invocation.args.trim()) : undefined;
    if (directory === undefined) {
      const picked = await vscode.window.showOpenDialog({ canSelectFiles: false, canSelectFolders: true, canSelectMany: false, openLabel: 'Run these tasks' });
      directory = picked?.[0]?.fsPath;
    }
    if (directory === undefined) {
      return;
    }
    const folder = path.isAbsolute(directory) ? directory : path.join(repository, directory);
    if (!(await this.paidReady())) {
      invocation.say('paidloop is not declared, so the batch did not start.');
      return;
    }
    const services = this.controller.services;
    const { settings } = services;
    const output = this.controller.output;
    output.show(true);
    const journal = services.journalFor(folder, repository);
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `Vibey batch: ${path.basename(folder)}`, cancellable: true },
      async (progress, token) => {
        token.onCancellationRequested(() => void services.queue.stopAll());
        const summary = await services.batch().run(
          {
            directory: folder,
            repository,
            baseRef: settings.baseRef,
            journal,
            commitType: 'chore',
            contextWindow: settings.contextWindow,
            loop: settings.loop,
            effort: settings.effort,
            baseEffort: settings.baseEffort,
            engine: settings.engine,
          },
          {
            onPlanned: (tasks, skipped, pending) => output.appendLine(`${tasks.length} task(s): ${skipped.length} already finished, ${pending.length} to run.`),
            onNote: (text) => output.appendLine(`[note] ${text}`),
            onTaskStarted: (task, run, index, total) => {
              this.controller.track(run);
              progress.report({ message: `${index}/${total} ${task.name}` });
              output.appendLine(`=== ${index}/${total} ${task.name}: ${task.title}`);
            },
            onTaskFinished: (task, record) => output.appendLine(`--- ${task.name}: ${record.outcome}${record.branch === undefined ? '' : ` on ${record.branch}`}`),
          },
        );
        const counts = Object.entries(summary.outcomes).map(([outcome, count]) => `${count} ${outcome}`).join(', ');
        output.appendLine(`Batch ${summary.batchId}: ${summary.ran} ran (${counts || 'none'}), ${summary.skipped} already finished, ${summary.remaining} remain. Journal: ${summary.journal}`);
        invocation.say(
          summary.halted === undefined
            ? `The batch is done: ${counts || 'nothing left to run'}.`
            : `The batch stopped: ${summary.halted}. ${summary.remaining} task(s) remain; run it again to resume.`,
        );
      },
    );
  }

  private async stopRun(invocation: Invocation): Promise<void> {
    const run = await this.liveRun(invocation, (candidate) => candidate.status !== 'finished' && candidate.status !== 'finishing', 'Stop which task?');
    if (run === undefined) {
      invocation.say('No task is running or waiting.');
      return;
    }
    if (run.status === 'queued' && this.controller.services.queue.cancel(run)) {
      invocation.say(`"${run.request.title}" was taken out of the line; it never started.`);
      return;
    }
    invocation.say((await run.stop()) ?? 'Stopping. The model finishes the turn it is on; Force stop opens if it takes too long.');
  }

  private async forceStopRun(invocation: Invocation): Promise<void> {
    const run = await this.liveRun(invocation, (candidate) => candidate.status === 'stopping', 'Force-stop which task?');
    if (run === undefined) {
      invocation.say('Force stop is for a task that was asked to stop and has not: press Stop first.');
      return;
    }
    const sure = await vscode.window.showWarningMessage(
      `End "${run.request.title}" now?`,
      { modal: true, detail: 'The model is cut off mid-turn. What it wrote so far stays in its copy, not committed. This is recorded in the task journal.' },
      'Force stop',
    );
    if (sure !== 'Force stop') {
      return;
    }
    invocation.say(run.forceStop(this.controller.services.settings.forceStopAfterMs) ?? 'The process was ended. The task records it as stopped.');
  }

  private async openRunLog(invocation: Invocation): Promise<void> {
    const element = invocation.element;
    const runId = element?.kind === 'run' ? element.runId : invocation.runId;
    if (runId !== undefined && this.controller.runs.has(runId)) {
      this.panel(runId).show(runId);
      return;
    }
    const record = element?.kind === 'record' ? element.record : await this.pickRecord('Open which task?', () => true);
    if (record === undefined) {
      return;
    }
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(path.join(record.run_directory, 'result.json')));
    await vscode.window.showTextDocument(document, { preview: true });
    if (record.events_path !== undefined) {
      invocation.say(`Its events: ${record.events_path}`);
    }
  }

  private async reviewRun(invocation: Invocation): Promise<void> {
    const record = await this.finishedRecord(invocation, 'Review which task?');
    if (record === undefined) {
      return;
    }
    if (record.repository === undefined || record.base_sha === undefined || record.head_sha === undefined) {
      invocation.say('This task made no copy to review.');
      return;
    }
    const diff = await this.controller.services.git.diff(record.repository, record.base_sha, record.head_sha);
    const header = [
      `# ${record.title}`,
      `# ${record.outcome} on ${record.branch ?? record.cwd ?? ''}, ${record.base_sha.slice(0, 12)}..${record.head_sha.slice(0, 12)}`,
      ...(record.uncommitted.length === 0 ? [] : [`# Not committed, so not part of Apply: ${record.uncommitted.join(', ')}`]),
      '',
    ].join('\n');
    const document = await vscode.workspace.openTextDocument({ content: `${header}${diff || '(no committed change)\n'}`, language: 'diff' });
    await vscode.window.showTextDocument(document, { preview: true });
  }

  private async applyRun(invocation: Invocation): Promise<void> {
    const record = await this.finishedRecord(invocation, 'Apply which task?');
    if (record === undefined) {
      return;
    }
    if (record.mode !== 'worktree' || record.branch === undefined || record.repository === undefined) {
      invocation.say('This task ran in place, so its work is already in your folder: review and undo it with git.');
      return;
    }
    const git = this.controller.services.git;
    const into = (await git.currentBranch(record.repository)) ?? 'the checked-out commit';
    const sure = await vscode.window.showInformationMessage(
      `Merge "${record.title}" (${record.branch}) into ${into}?`,
      { modal: true, detail: `${record.diff_stat || 'No committed change.'}${record.uncommitted.length === 0 ? '' : `\n\nNot committed, so not applied: ${record.uncommitted.join(', ')}`}\n\nYour repository's hooks run; if one refuses, nothing is forced.` },
      'Apply',
    );
    if (sure !== 'Apply') {
      return;
    }
    const merged = await git.merge(record.repository, record.branch, `chore(vibey): apply the task "${record.title}"`);
    if (merged.ok) {
      this.controller.services.history.applied(record.run_id, merged.output || `merged ${record.branch}`);
      this.controller.changed();
      invocation.say(`Applied: ${record.branch} is merged into ${into}.`);
      return;
    }
    invocation.say(
      merged.reason === 'conflict'
        ? `Not applied: ${merged.conflicts.join(', ')} changed on both sides, so the merge was undone. Resolve it by hand with git merge ${record.branch}.`
        : `Not applied: ${merged.detail}`,
    );
  }

  private async discardRun(invocation: Invocation): Promise<void> {
    const record = await this.finishedRecord(invocation, 'Discard which task?');
    if (record === undefined) {
      return;
    }
    if (record.mode !== 'worktree' || record.branch === undefined || record.repository === undefined || record.cwd === undefined) {
      invocation.say('This task ran in place: there is no copy to discard. Undo its changes with git.');
      return;
    }
    const sure = await vscode.window.showWarningMessage(
      `Discard "${record.title}"?`,
      { modal: true, detail: `Its copy (${record.cwd}) and its branch ${record.branch} are deleted. The task's journal and result stay.` },
      'Discard',
    );
    if (sure !== 'Discard') {
      return;
    }
    const git = this.controller.services.git;
    try {
      await git.removeWorktree(record.repository, record.cwd);
    } catch (error) {
      this.controller.output.appendLine(`The copy was not removed (it may be gone already): ${(error as Error).message}`);
    }
    await git.deleteBranch(record.repository, record.branch);
    this.controller.services.history.discarded(record.run_id);
    this.controller.changed();
    invocation.say(`Discarded: ${record.branch} and its copy are gone.`);
  }

  private async attach(invocation: Invocation, kind: 'file' | 'image'): Promise<void> {
    const menu = await this.controller.menu();
    if (kind === 'image' && !menu.attachImage) {
      invocation.say(menu.notes.join(' ') || 'This engine and model cannot take an image.');
      return;
    }
    if (kind === 'file' && !menu.attachFile) {
      invocation.say('This engine does not say it takes files. Paste the text instead with /paste.');
      return;
    }
    let files = invocation.args?.trim() ? this.words.words(invocation.args).map((word) => CommandActions.home(word)) : [];
    if (files.length === 0) {
      const picked = await vscode.window.showOpenDialog({
        canSelectMany: true,
        openLabel: 'Attach to the next task',
        ...(kind === 'image' ? { filters: { Images: ['png', 'jpg', 'jpeg', 'gif', 'webp'] } } : {}),
      });
      files = (picked ?? []).map((uri) => uri.fsPath);
    }
    for (const file of files) {
      this.controller.next.attachments.push({ kind, name: file });
    }
    this.controller.changed();
    if (files.length > 0) {
      invocation.say(`${files.length} ${kind === 'image' ? 'image' : 'file'}(s) will go with the next task, copied into its folder and never committed.`);
    }
  }

  private async pasteText(invocation: Invocation): Promise<void> {
    let text = invocation.args?.trim() ?? '';
    if (!text) {
      text = (await vscode.env.clipboard.readText()).trim();
    }
    if (!text) {
      text = (await vscode.window.showInputBox({ title: 'Paste text for the next task', ignoreFocusOut: true }))?.trim() ?? '';
    }
    if (!text) {
      return;
    }
    const label = `pasted text ${this.controller.next.attachments.filter((attachment) => attachment.kind === 'text').length + 1}`;
    this.controller.next.attachments.push({ kind: 'text', name: label, text });
    this.controller.changed();
    invocation.say(`The next task will read ${text.length.toLocaleString('en-US')} pasted characters as "${label}".`);
  }

  private async pasteImage(invocation: Invocation): Promise<void> {
    const menu = await this.controller.menu();
    invocation.say(
      menu.pasteImage
        ? 'Paste the image into the task panel (Cmd+V or Ctrl+V): it goes with the next task.'
        : menu.notes.join(' ') || 'This engine and model cannot take an image.',
    );
  }

  private async plugins(invocation: Invocation): Promise<void> {
    const repository = this.controller.folder();
    if (repository === undefined) {
      invocation.say('Open a folder first: plugins come from its .claude-plugin/marketplace.json.');
      return;
    }
    const menu = await this.controller.menu();
    if (menu.plugins === undefined) {
      invocation.say('This engine has no verified plugin support, so no plugin context is added.');
      return;
    }
    const available = this.controller.services.marketplace.plugins(repository);
    if (available.length === 0) {
      invocation.say(`${path.join(repository, '.claude-plugin', 'marketplace.json')} lists no plugins.`);
      return;
    }
    let chosen = invocation.args?.trim() ? this.words.words(invocation.args) : undefined;
    if (chosen === undefined) {
      const picked = await vscode.window.showQuickPick(
        available.map((plugin) => ({ label: plugin.name, description: plugin.category ?? '', detail: plugin.description, picked: this.controller.next.plugins.includes(plugin.name) })),
        { canPickMany: true, title: 'vibey-skills context for the next task', placeHolder: 'Each plugin adds ranked context from its skills' },
      );
      if (picked === undefined) {
        return;
      }
      chosen = picked.map((item) => item.label);
    }
    const unknown = chosen.filter((name) => !available.some((plugin) => plugin.name === name));
    if (unknown.length > 0) {
      invocation.say(`Not in the marketplace: ${unknown.join(', ')}.`);
      return;
    }
    this.controller.next.plugins = [...chosen];
    this.controller.changed();
    invocation.say(chosen.length === 0 ? 'The next task gets no plugin context.' : `The next task gets vibey-skills context from ${chosen.join(', ')}.`);
  }

  // --- Loop & model ----------------------------------------------------------------------

  private async chooseLoop(invocation: Invocation): Promise<void> {
    let loop: LoopName | undefined;
    if (invocation.args?.trim()) {
      const read = this.words.loop(invocation.args);
      if (read !== 'sovereignloop' && read !== 'paidloop') {
        invocation.say(read);
        return;
      }
      loop = read;
    } else {
      const picked = await vscode.window.showQuickPick(
        [
          { label: 'sovereignloop', description: 'default', detail: 'Everything runs on this computer: gptossloop on your local model.', loop: 'sovereignloop' as const },
          { label: 'paidloop', description: 'declared only', detail: "Claude and other vendors' engines; they bill your own accounts, within your budgets.", loop: 'paidloop' as const },
        ],
        { title: 'Choose the loop' },
      );
      loop = picked?.loop;
    }
    if (loop === undefined) {
      return;
    }
    if (loop === 'paidloop' && !this.controller.services.paidDeclared() && !(await this.declarePaid())) {
      invocation.say('paidloop was not declared, so the loop stays as it was.');
      return;
    }
    await this.controller.editorSettings.set('loop', loop);
    invocation.say(`Tasks now run in ${loop}.`);
  }

  private async chooseEffort(invocation: Invocation): Promise<void> {
    let effort: EffortSetting | undefined;
    if (invocation.args?.trim()) {
      const read = this.words.effort(invocation.args);
      if (read !== 'auto' && !(await this.controller.services.catalogue()).efforts.includes(read as never)) {
        invocation.say(read);
        return;
      }
      effort = read as EffortSetting;
    } else {
      const catalogue = await this.controller.services.catalogue();
      const picked = await vscode.window.showQuickPick(
        [
          { label: 'auto', detail: "Start at the base effort; a failed attempt climbs vibey's ladder, in the same copy." },
          ...catalogue.efforts.map((level) => ({ label: level, detail: `Every attempt at ${level}.` })),
        ],
        { title: 'Choose the effort' },
      );
      effort = picked?.label as EffortSetting | undefined;
    }
    if (effort === undefined) {
      return;
    }
    await this.controller.editorSettings.set('effort', effort);
    invocation.say(`Effort: ${effort}.`);
  }

  private async chooseModel(invocation: Invocation): Promise<void> {
    const services = this.controller.services;
    const catalogue = await services.catalogue();
    const loop = catalogue.loops.find((candidate) => candidate.loop === services.settings.loop);
    let engine = invocation.args?.trim();
    if (!engine) {
      const choices: (vscode.QuickPickItem & { repealed?: boolean })[] = [{ label: 'auto', detail: 'vibey chooses: the model already loaded, by weighted round robin within the loop.' }];
      for (const candidate of loop?.engines.filter((each) => each.enabled && !each.repealed) ?? []) {
        choices.push({ label: candidate.engine_id, detail: candidate.notes?.join(' ') ?? `its effort chooses the model (${candidate.default_model ?? 'the engine default'})` });
        const models =
          loop?.tier === 'local'
            ? await services.probe.models().then((listing) => listing.names, () => [] as readonly string[])
            : [...new Set(candidate.efforts.map((entry) => entry.model).filter((name): name is string => name !== null))];
        for (const model of models) {
          choices.push({ label: `${candidate.engine_id}/${model}`, description: loop?.tier === 'local' ? 'on this computer' : '' });
        }
      }
      // Listed for transparency, as vibey lists them, and never run.
      const repealed = loop?.engines.filter((each) => each.repealed) ?? [];
      if (repealed.length > 0) {
        choices.push({ label: 'Repealed by the canon', kind: vscode.QuickPickItemKind.Separator });
        for (const candidate of repealed) {
          choices.push({ label: `$(circle-slash) ${candidate.engine_id}`, description: 'repealed by 8.b', detail: 'Listed so you can see it; it never runs.', repealed: true });
        }
      }
      const picked = await vscode.window.showQuickPick(choices, { title: `Choose the engine and model for ${services.settings.loop}` });
      if (picked?.repealed === true) {
        invocation.say(`${picked.label.replace(/^\$\(circle-slash\) /, '')} is repealed by the canon (8.b): it never runs.`);
        return;
      }
      engine = picked?.label;
    }
    if (!engine) {
      return;
    }
    await this.controller.editorSettings.set('engine', engine);
    invocation.say(`Engine: ${engine}.`);
  }

  private async showLoops(invocation: Invocation): Promise<void> {
    const catalogue = await this.controller.services.catalogue();
    const output = this.controller.output;
    output.appendLine(`vibey loops (${catalogue.source === 'vibey' ? 'from vibey loops --json' : 'degraded: vibey loops is not available'})`);
    if (catalogue.notice !== undefined) {
      output.appendLine(`  ${catalogue.notice}`);
    }
    for (const loop of catalogue.loops) {
      output.appendLine(`${loop.loop} (${loop.tier}${loop.default ? ', default' : ''}${loop.declared_only ? ', declared only' : ''})`);
      for (const engine of loop.engines) {
        const state = engine.repealed ? ' (repealed by 8.b: never runs)' : engine.enabled ? '' : ` (off${engine.switch === null ? '' : engine.on_by_default ? `: on by default, switched off by ${engine.switch}` : `: ${engine.switch}`})`;
        output.appendLine(`  ${engine.enabled && !engine.repealed ? '•' : '○'} ${engine.engine_id}${state}  ${engine.efforts.map((entry) => `${entry.effort}→${entry.achieved}${entry.model === null ? '' : ` ${entry.model}`}`).join(', ')}`);
      }
    }
    output.appendLine(`ladder: ${catalogue.ladder.build_attempts.join(' → ')}, exhausted after ${catalogue.ladder.exhausted_after}`);
    output.show(true);
    invocation.say(catalogue.loops.map((loop) => `${loop.loop}: ${loop.engines.filter((engine) => engine.enabled && !engine.repealed).map((engine) => engine.engine_id).join(', ') || 'no engine on'}`).join('; '));
  }

  // --- Lanes -----------------------------------------------------------------------------

  private async openLane(invocation: Invocation): Promise<void> {
    let lane: Lane | undefined = invocation.element?.kind === 'lane' ? invocation.element.lane : undefined;
    if (lane === undefined) {
      const lanes = await this.controller.lanes();
      const wanted = invocation.args?.trim();
      lane = wanted
        ? lanes.find((candidate) => candidate.id.startsWith(wanted))
        : (await vscode.window.showQuickPick(lanes.map((candidate) => ({ label: candidate.label, description: `${candidate.state} · turn ${candidate.turn}`, lane: candidate })), { title: 'Watch which lane?' }))?.lane;
    }
    if (lane === undefined) {
      invocation.say('No such lane in the last hour.');
      return;
    }
    const owned = this.controller.runs.get(lane.id);
    if (owned !== undefined) {
      this.panel(owned.runId).show(owned.runId);
      return;
    }
    new TaskPanel(this.controller, this, this.extensionUri, 'lane', { eventsPath: lane.eventsPath, label: lane.label }).reveal();
  }

  private async startQueue(invocation: Invocation): Promise<void> {
    const queue = this.controller.services.queue;
    const element = invocation.element;
    const run = element?.kind === 'run' ? this.controller.runs.get(element.runId) : undefined;
    if (run !== undefined && queue.bump(run)) {
      invocation.say(`"${run.request.title}" runs next.`);
      return;
    }
    queue.resume();
    this.controller.changed();
    invocation.say('The queue is running: waiting tasks start as the model frees.');
  }

  private async stopAll(invocation: Invocation): Promise<void> {
    const live = [...this.controller.runs.values()].filter((run) => run.status !== 'finished' && run.status !== 'finishing');
    if (live.length === 0) {
      invocation.say('Nothing is running.');
      return;
    }
    const sure = await vscode.window.showWarningMessage(`Stop all ${live.length} task(s)?`, { modal: true, detail: 'Waiting tasks do not start. Running ones finish the turn they are on, then end.' }, 'Stop all');
    if (sure !== 'Stop all') {
      return;
    }
    const errors = [...(await this.controller.services.queue.stopAll())];
    for (const run of live) {
      if (run.stopRequestedAt === undefined) {
        const error = await run.stop();
        if (error !== undefined) {
          errors.push(`${run.request.title}: ${error}`);
        }
      }
    }
    this.controller.changed();
    invocation.say(errors.length === 0 ? 'Stopping every task.' : `Stopping; some could not be asked: ${errors.join('; ')}`);
  }

  private async refresh(invocation: Invocation): Promise<void> {
    await this.controller.services.catalogue(true);
    this.controller.changed();
    if (invocation.args !== undefined) {
      invocation.say('Refreshed.');
    }
  }

  // --- Projects & gates ------------------------------------------------------------------

  private async showStatus(invocation: Invocation): Promise<void> {
    const vibey = this.vibey(invocation);
    if (vibey === undefined) {
      return;
    }
    const project = invocation.element?.kind === 'project' ? invocation.element.project : await this.pickProject(invocation);
    const status = await vibey.status(project?.project_id);
    const output = this.controller.output;
    output.appendLine(`${status.name} (${status.project_id}): ${status.phase}${status.cycle === undefined ? '' : `, cycle ${status.cycle}${status.max_cycles === undefined ? '' : ` of ${status.max_cycles}`}`}`);
    output.appendLine(`  queue: ${Object.entries(status.queue_depth).map(([kind, depth]) => `${kind} ${depth}`).join(', ') || 'empty'}`);
    for (const circuit of status.circuits) {
      output.appendLine(`  ${circuit.engine_id}: ${circuit.circuit ?? 'unknown'}${circuit.version ? ` (${circuit.version})` : ''}`);
    }
    for (const worktree of status.active_worktrees) {
      output.appendLine(`  worktree: ${worktree}`);
    }
    output.show(true);
    invocation.say(`${status.name}: ${status.phase}.`);
  }

  private async answerGate(invocation: Invocation): Promise<void> {
    const vibey = this.vibey(invocation);
    if (vibey === undefined) {
      return;
    }
    const gate = await this.gate(invocation);
    if (gate === undefined) {
      return;
    }
    const planner = this.controller.services.answers;
    const rest = invocation.args?.trim().split(/\s+/).slice(1).join(' ');
    let answer: GateAnswer | undefined;
    if (rest) {
      answer = rest.startsWith('{') ? { mode: 'raw', json: rest } : rest.startsWith('--verdict') ? { mode: 'verdict', value: rest.replace(/^--verdict\s*/, '') } : { mode: 'choice', value: rest };
    } else {
      const picked = await vscode.window.showQuickPick(
        planner.choices(gate).map((choice) => ({ label: choice.label, description: choice.description ?? '', choice })),
        { title: gate.prompt.split('\n')[0] ?? gate.kind, placeHolder: `${gate.kind} for ${gate.project_name ?? gate.project_id}` },
      );
      if (picked === undefined) {
        return;
      }
      answer = picked.choice.answer ?? (await this.moreAnswer(gate, picked.choice.needs));
    }
    if (answer === undefined) {
      return;
    }
    if (answer.mode === 'raw') {
      const problem = planner.checkRaw(answer.json);
      if (problem !== undefined) {
        invocation.say(problem);
        return;
      }
    }
    invocation.say(await vibey.answer(gate.gate_id, answer) || 'Answered.');
    this.controller.changed();
  }

  private async bumpJob(invocation: Invocation): Promise<void> {
    const vibey = this.vibey(invocation);
    if (vibey === undefined) {
      return;
    }
    const job = invocation.args?.trim() || (await vscode.window.showInputBox({ title: 'Run which queued job next?', prompt: 'The job id, as vibey status shows it.', ignoreFocusOut: true }));
    if (!job?.trim()) {
      return;
    }
    invocation.say(await vibey.bump(job.trim()) || 'Bumped.');
  }

  // --- Budgets ---------------------------------------------------------------------------

  private async addBudget(invocation: Invocation): Promise<void> {
    const store = this.controller.services.budgets;
    if (invocation.args?.trim()) {
      const fields = CommandActions.fields(invocation.args);
      const added = store.add({
        scope: (fields.scope ?? 'day') as BudgetScope,
        loop: (fields.loop ?? 'any') as BudgetLoop,
        ...(fields.engine === undefined ? {} : { engine_id: fields.engine }),
        caps: CommandActions.caps(fields),
        ...(fields.label === undefined ? {} : { label: fields.label }),
      });
      this.controller.changed();
      invocation.say(`Added budget ${added.id}.`);
      return;
    }
    const target = await vscode.window.showQuickPick(
      [
        { label: "This computer's lanes", detail: 'Caps for the tasks and batches this computer runs: per run, per day or per month.', project: false },
        { label: 'A vibey project', detail: "A project's cycle caps, through vibey budget.", project: true },
      ],
      { title: 'Add a budget for' },
    );
    if (target === undefined) {
      return;
    }
    if (target.project) {
      await this.projectCaps(invocation, undefined);
      return;
    }
    const scope = (await vscode.window.showQuickPick(['day', 'month', 'run'], { title: 'Per day, per month, or per run?' })) as BudgetScope | undefined;
    const loop = scope === undefined ? undefined : ((await vscode.window.showQuickPick(['any', 'sovereignloop', 'paidloop'], { title: 'For which loop?' })) as BudgetLoop | undefined);
    if (scope === undefined || loop === undefined) {
      return;
    }
    const caps = await this.capsInput('dollars=5 turns=200 minutes=120');
    if (caps === undefined) {
      return;
    }
    const added = store.add({ scope, loop, caps });
    this.controller.changed();
    invocation.say(`Added budget ${added.id}.`);
  }

  private async editBudget(invocation: Invocation): Promise<void> {
    const element = invocation.element;
    if (element?.kind === 'project-budget') {
      await this.projectCaps(invocation, element.budget);
      return;
    }
    const budget = element?.kind === 'lane-budget' ? element.budget : await this.laneBudget(invocation, 'Edit which budget?');
    if (budget === undefined) {
      return;
    }
    const given = invocation.args?.trim().split(/\s+/).slice(1).join(' ');
    const caps = given ? CommandActions.caps(CommandActions.fields(given)) : await this.capsInput(CommandActions.capsText(budget.caps));
    if (caps === undefined) {
      return;
    }
    this.controller.services.budgets.edit(budget.id, { caps });
    this.controller.changed();
    invocation.say(`Budget ${budget.id} now allows ${CommandActions.capsText(caps)}.`);
  }

  private async removeBudget(invocation: Invocation): Promise<void> {
    const element = invocation.element;
    if (element?.kind === 'project-budget') {
      const vibey = this.vibey(invocation);
      if (vibey !== undefined && (await this.confirm(`Clear ${element.budget.name}'s cycle caps?`, 'Clear'))) {
        invocation.say(await vibey.clearBudget(element.budget.project_id, 'all') || 'Cleared.');
        this.controller.changed();
      }
      return;
    }
    const budget = element?.kind === 'lane-budget' ? element.budget : await this.laneBudget(invocation, 'Remove which budget?');
    if (budget === undefined || !(await this.confirm(`Remove budget ${budget.label ?? budget.id}?`, 'Remove'))) {
      return;
    }
    this.controller.services.budgets.remove(budget.id);
    this.controller.changed();
    invocation.say(`Removed budget ${budget.id}.`);
  }

  /** More room under a used-up cap: a parked budget_exhausted gate, a project's caps, or a lane budget. */
  private async grantBudget(invocation: Invocation): Promise<void> {
    const element = invocation.element;
    if (element?.kind === 'gate' || (element === undefined && invocation.args?.trim())) {
      const vibey = this.vibey(invocation);
      const gate = vibey === undefined ? undefined : await this.gate(invocation);
      if (vibey === undefined || gate === undefined) {
        return;
      }
      const amount = await this.amount(invocation.args?.trim().split(/\s+/).slice(1).join(' '));
      if (amount === undefined) {
        return;
      }
      const json = JSON.stringify(amount.cap === 'dollars' ? { max_dollars: amount.value } : { max_turns: amount.value });
      invocation.say(await vibey.answer(gate.gate_id, { mode: 'raw', json }) || 'Granted.');
      this.controller.changed();
      return;
    }
    if (element?.kind === 'project-budget') {
      const amount = await this.amount(undefined);
      const vibey = this.vibey(invocation);
      if (amount === undefined || vibey === undefined) {
        return;
      }
      const current = amount.cap === 'dollars' ? element.budget.caps.max_cycle_dollars ?? element.budget.spend.dollars : element.budget.caps.max_cycle_turns ?? element.budget.spend.turns;
      invocation.say(await vibey.setBudget(element.budget.project_id, { [amount.cap]: current + amount.value }) || 'Raised.');
      this.controller.changed();
      return;
    }
    const budget = element?.kind === 'lane-budget' ? element.budget : await this.laneBudget(invocation, 'Raise which budget?');
    if (budget === undefined) {
      return;
    }
    const amount = await this.amount(undefined);
    if (amount === undefined) {
      return;
    }
    const current = budget.caps[amount.cap] ?? 0;
    this.controller.services.budgets.edit(budget.id, { caps: { ...budget.caps, [amount.cap]: current + amount.value } });
    this.controller.changed();
    invocation.say(`Budget ${budget.id} now allows ${CommandActions.capsText({ ...budget.caps, [amount.cap]: current + amount.value })}.`);
  }

  // --- Ollama and the doctor ---------------------------------------------------------------

  private async startOllama(invocation: Invocation): Promise<void> {
    const services = this.controller.services;
    const status = await services.probe.status(services.settings.model, services.settings.contextWindow);
    const ollama = services.locator.locate('ollama', services.settings.raw.ollamaPath).path;
    const facts = await services.startFacts.read(services.settings.raw.ollamaAppPath, ollama);
    const plan = services.startPlanner.plan(facts, status.reachable);
    if (plan.kind === 'launch') {
      const launched = await services.processes.launchDetached(plan.command, plan.args, { env: services.toolEnvironment });
      invocation.say(launched.error === undefined ? plan.explanation : `${plan.explanation} It did not start: ${launched.error}`);
      this.controller.changed();
      return;
    }
    invocation.say(plan.kind === 'terminal' ? `${plan.explanation} Run: ${plan.commandLine}` : plan.explanation);
  }

  private async pullModel(invocation: Invocation): Promise<void> {
    const services = this.controller.services;
    const model = invocation.args?.trim() || services.settings.model;
    const size = ModelPuller.sizeHint(model);
    const sure = await vscode.window.showInformationMessage(
      `Download ${model}${size === undefined ? '' : ` (${size})`}?`,
      { modal: true, detail: `Ollama keeps it on this computer. ${size === undefined ? 'Check its size on ollama.com first.' : 'Make sure there is room for it.'}` },
      'Download',
    );
    if (sure !== 'Download') {
      return;
    }
    const outcome = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `Downloading ${model}`, cancellable: true },
      async (progress, token) => {
        const stop = new AbortController();
        token.onCancellationRequested(() => stop.abort());
        let shown = 0;
        return services.puller.pull(
          model,
          (update) => {
            const percent = update.percent ?? shown;
            progress.report({ message: `${update.status}${update.percent === undefined ? '' : ` ${update.percent}%`}`, increment: Math.max(0, percent - shown) });
            shown = percent;
          },
          stop.signal,
        );
      },
    );
    this.controller.changed();
    invocation.say(outcome.ok ? `${model} is downloaded.` : `The download stopped: ${outcome.error ?? 'unknown'}. In a terminal, this does the same: ${outcome.fallbackCommand}`);
  }

  private async doctor(invocation: Invocation): Promise<void> {
    const checks = await this.controller.services.doctor().run();
    const output = this.controller.output;
    output.appendLine(Doctor.render(checks));
    output.show(true);
    const failing = checks.filter((check) => check.status === 'fail').length;
    const warning = checks.filter((check) => check.status === 'warn').length;
    invocation.say(failing === 0 && warning === 0 ? 'Everything checks out.' : `${failing} problem(s) and ${warning} warning(s): see the Vibey output for what to do.`);
  }

  private async showMenu(invocation: Invocation): Promise<void> {
    if (invocation.args !== undefined) {
      invocation.say(this.slash.help());
      return;
    }
    const items: (vscode.QuickPickItem & { id?: string })[] = [];
    for (const [group, specs] of CommandTable.grouped()) {
      items.push({ label: group, kind: vscode.QuickPickItemKind.Separator });
      for (const spec of specs) {
        items.push({ label: `$(${spec.icon}) ${spec.title}`, description: spec.slash === undefined ? '' : `/${spec.slash}`, detail: spec.description, id: spec.id });
      }
    }
    const picked = await vscode.window.showQuickPick(items, { title: 'Vibey', matchOnDescription: true, matchOnDetail: true });
    if (picked?.id !== undefined) {
      await this.run(picked.id, { say: invocation.say });
    }
  }

  // --- Helpers ---------------------------------------------------------------------------

  private panel(runId: string): TaskPanel {
    let panel = this.panels.get(runId);
    if (panel === undefined) {
      panel = new TaskPanel(this.controller, this, this.extensionUri, 'task');
      const created = panel;
      created.onDidClose(() => {
        for (const [id, each] of this.panels) {
          if (each === created) {
            this.panels.delete(id);
          }
        }
      });
      this.panels.set(runId, created);
    }
    return panel;
  }

  private async focus(view: string): Promise<void> {
    await vscode.commands.executeCommand(`${view}.focus`);
  }

  /** paidloop runs only once declared, with a cap or a twice-confirmed "no cap". */
  private async paidReady(): Promise<boolean> {
    const services = this.controller.services;
    return services.settings.loop !== 'paidloop' || services.paidDeclared() || this.declarePaid();
  }

  private async declarePaid(): Promise<boolean> {
    const choice = await vscode.window.showWarningMessage(
      'Declare paidloop?',
      { modal: true, detail: "Paid engines (Claude through claudeloop by default) bill their vendors' accounts, not this computer. Declare it with a spending cap, which is recorded in the budget journal." },
      'With a daily cap',
      'With a monthly cap',
      'With no cap',
    );
    if (choice === undefined) {
      return false;
    }
    const budgets = this.controller.services.budgets;
    if (choice === 'With no cap') {
      const again = await vscode.window.showWarningMessage(
        'Really declare paidloop with no dollar cap?',
        { modal: true, detail: 'Nothing on this computer will stop paid engines from spending. You can add a budget later from the Budgets view.' },
        'Yes, no cap',
      );
      if (again !== 'Yes, no cap') {
        return false;
      }
      budgets.declarePaid({ noCap: true, confirmed: true });
    } else {
      const dollars = await this.dollars(choice === 'With a daily cap' ? 'Dollars per day' : 'Dollars per month');
      if (dollars === undefined) {
        return false;
      }
      budgets.declarePaid({ scope: choice === 'With a daily cap' ? 'day' : 'month', dollars });
    }
    this.controller.changed();
    return true;
  }

  private async dollars(title: string): Promise<number | undefined> {
    const text = await vscode.window.showInputBox({
      title,
      prompt: 'A positive number of dollars',
      ignoreFocusOut: true,
      validateInput: (value) => (Number(value.replace(/^\$/, '')) > 0 ? undefined : 'A positive number, like 5 or 12.50'),
    });
    return text === undefined ? undefined : Number(text.replace(/^\$/, ''));
  }

  /** `$10`, `10 dollars` or `40 turns`, typed after the command or asked for. */
  private async amount(given: string | undefined): Promise<{ cap: 'dollars' | 'turns'; value: number } | undefined> {
    const text =
      given ||
      (await vscode.window.showInputBox({
        title: 'Grant how much more?',
        prompt: '$10 for dollars, or 40 turns',
        ignoreFocusOut: true,
        validateInput: (value) => (CommandActions.readAmount(value) === undefined ? 'Like $10 or 40 turns' : undefined),
      }));
    return text === undefined ? undefined : CommandActions.readAmount(text);
  }

  static readAmount(text: string): { cap: 'dollars' | 'turns'; value: number } | undefined {
    const trimmed = text.trim().toLowerCase();
    const turns = /^(\d+)\s*turns?$/.exec(trimmed);
    if (turns !== null) {
      return { cap: 'turns', value: Number(turns[1]) };
    }
    const dollars = /^\$?(\d+(?:\.\d+)?)\s*(?:dollars?)?$/.exec(trimmed);
    return dollars === null || Number(dollars[1]) <= 0 ? undefined : { cap: 'dollars', value: Number(dollars[1]) };
  }

  private async capsInput(value: string): Promise<BudgetCaps | undefined> {
    const text = await vscode.window.showInputBox({
      title: 'Caps',
      prompt: 'Any of dollars=, turns= and minutes=, separated by spaces',
      value,
      ignoreFocusOut: true,
    });
    return text === undefined ? undefined : CommandActions.caps(CommandActions.fields(text));
  }

  static fields(text: string): Record<string, string> {
    const fields: Record<string, string> = {};
    for (const part of text.trim().split(/\s+/)) {
      const at = part.indexOf('=');
      if (at > 0) {
        fields[part.slice(0, at).toLowerCase()] = part.slice(at + 1).replace(/^\$/, '');
      }
    }
    return fields;
  }

  static caps(fields: Readonly<Record<string, string>>): BudgetCaps {
    return {
      ...(fields.dollars === undefined ? {} : { dollars: Number(fields.dollars) }),
      ...(fields.turns === undefined ? {} : { turns: Number(fields.turns) }),
      ...(fields.minutes === undefined ? {} : { minutes: Number(fields.minutes) }),
    };
  }

  static capsText(caps: BudgetCaps): string {
    return (['dollars', 'turns', 'minutes'] as const)
      .filter((cap) => caps[cap] !== undefined)
      .map((cap) => `${cap}=${caps[cap]}`)
      .join(' ');
  }

  private async projectCaps(invocation: Invocation, budget: VibeyBudget | undefined): Promise<void> {
    const vibey = this.vibey(invocation);
    if (vibey === undefined) {
      return;
    }
    const projectId = budget?.project_id ?? (await this.pickProject(invocation))?.project_id;
    if (projectId === undefined) {
      return;
    }
    const current = budget === undefined ? '' : [budget.caps.max_cycle_dollars === null ? '' : `dollars=${budget.caps.max_cycle_dollars}`, budget.caps.max_cycle_turns === null ? '' : `turns=${budget.caps.max_cycle_turns}`].filter((part) => part !== '').join(' ');
    const caps = await this.capsInput(current || 'dollars=15 turns=300');
    if (caps === undefined) {
      return;
    }
    invocation.say(await vibey.setBudget(projectId, { ...(caps.dollars === undefined ? {} : { dollars: caps.dollars }), ...(caps.turns === undefined ? {} : { turns: caps.turns }) }) || 'Set.');
    this.controller.changed();
  }

  private async laneBudget(invocation: Invocation, title: string): Promise<Budget | undefined> {
    const budgets = this.controller.services.budgets.list();
    const wanted = invocation.args?.trim().split(/\s+/)[0];
    if (wanted) {
      const found = budgets.find((budget) => budget.id === wanted);
      if (found === undefined) {
        invocation.say(`There is no budget ${wanted}.`);
      }
      return found;
    }
    return (await vscode.window.showQuickPick(budgets.map((budget) => ({ label: budget.label ?? budget.id, description: `${budget.scope} ${budget.loop} ${CommandActions.capsText(budget.caps)}`, budget })), { title }))?.budget;
  }

  private async gate(invocation: Invocation): Promise<VibeyGate | undefined> {
    if (invocation.element?.kind === 'gate') {
      return invocation.element.gate;
    }
    const vibey = this.controller.services.vibey;
    const gates = vibey === undefined ? [] : await vibey.gates();
    const wanted = invocation.args?.trim().split(/\s+/)[0];
    if (wanted) {
      const found = gates.find((gate) => gate.gate_id.startsWith(wanted));
      if (found === undefined) {
        invocation.say(`No open gate starts with ${wanted}.`);
      }
      return found;
    }
    if (gates.length === 0) {
      invocation.say('No gate is waiting for you.');
      return undefined;
    }
    return (await vscode.window.showQuickPick(gates.map((gate) => ({ label: `${gate.kind}: ${gate.prompt.split('\n')[0] ?? ''}`, description: gate.project_name ?? gate.project_id, gate })), { title: 'Answer which gate?' }))?.gate;
  }

  private async moreAnswer(gate: VibeyGate, needs: 'pairs' | 'raw' | undefined): Promise<GateAnswer | undefined> {
    const planner = this.controller.services.answers;
    if (needs === 'pairs') {
      const text = await vscode.window.showInputBox({ title: gate.prompt.split('\n')[0] ?? gate.kind, prompt: 'Answers as question=answer, separated by spaces', ignoreFocusOut: true });
      if (text === undefined) {
        return undefined;
      }
      const pairs = planner.parsePairs(text);
      if (typeof pairs === 'string') {
        void vscode.window.showWarningMessage(pairs);
        return undefined;
      }
      return { mode: 'pairs', pairs, defaults: true };
    }
    const json = await vscode.window.showInputBox({
      title: gate.prompt.split('\n')[0] ?? gate.kind,
      prompt: gate.kind === 'budget_exhausted' ? 'A JSON object, like {"max_dollars": 10} or {"max_turns": 40}' : 'A JSON object',
      ignoreFocusOut: true,
      validateInput: (value) => planner.checkRaw(value),
    });
    return json === undefined ? undefined : { mode: 'raw', json };
  }

  private async pickProject(invocation: Invocation): Promise<VibeyProject | undefined> {
    const vibey = this.controller.services.vibey;
    const projects = vibey === undefined ? [] : await vibey.projects();
    const wanted = invocation.args?.trim().split(/\s+/)[0];
    if (wanted) {
      return projects.find((project) => project.project_id.startsWith(wanted) || project.name === wanted);
    }
    if (projects.length <= 1) {
      return projects[0];
    }
    return (await vscode.window.showQuickPick(projects.map((project) => ({ label: project.name, description: project.phase, project })), { title: 'Which project?' }))?.project;
  }

  private vibey(invocation: Invocation): NonNullable<typeof this.controller.services.vibey> | undefined {
    const vibey = this.controller.services.vibey;
    if (vibey === undefined) {
      invocation.say('vibey was not found. Install it (pip install vibey), or point the vibey.cliPath setting at it.');
    }
    return vibey;
  }

  /** The task a command is about: the item it was run on, the panel it was typed in, or one picked. */
  private async liveRun(invocation: Invocation, fits: (run: TaskRunInterface) => boolean, title: string): Promise<TaskRunInterface | undefined> {
    const element = invocation.element;
    const id = element?.kind === 'run' ? element.runId : invocation.runId;
    if (id !== undefined) {
      const run = this.controller.runs.get(id);
      return run !== undefined && fits(run) ? run : undefined;
    }
    const candidates = [...this.controller.runs.values()].filter(fits);
    if (candidates.length <= 1) {
      return candidates[0];
    }
    return (await vscode.window.showQuickPick(candidates.map((run) => ({ label: run.request.title, description: run.status, run })), { title }))?.run;
  }

  private async finishedRecord(invocation: Invocation, title: string): Promise<RunRecord | undefined> {
    const element: TreeElement | undefined = invocation.element;
    if (element?.kind === 'record') {
      return element.record;
    }
    const id = element?.kind === 'run' ? element.runId : invocation.runId;
    const live = id === undefined ? undefined : this.controller.runs.get(id);
    if (live !== undefined) {
      if (live.status !== 'finished') {
        invocation.say('This task has not finished yet.');
        return undefined;
      }
      return live.result;
    }
    return this.pickRecord(title, (record) => record.mode === 'worktree');
  }

  private async pickRecord(title: string, fits: (record: RunRecord) => boolean): Promise<RunRecord | undefined> {
    const records = this.controller
      .finished()
      .filter((entry) => entry.applied === undefined && entry.discarded === undefined && fits(entry.record))
      .map((entry) => entry.record);
    return (await vscode.window.showQuickPick(records.map((record) => ({ label: record.title, description: `${record.outcome}${record.branch === undefined ? '' : ` · ${record.branch}`}`, record })), { title }))?.record;
  }

  private async confirm(question: string, action: string): Promise<boolean> {
    return (await vscode.window.showWarningMessage(question, { modal: true }, action)) === action;
  }

  /** `~/x` as the person means it. */
  private static home(file: string): string {
    return file === '~' ? os.homedir() : file.startsWith('~/') ? path.join(os.homedir(), file.slice(2)) : file;
  }
}
