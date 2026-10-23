// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Driving a project from a conversation: starting one, being asked its questions, replying,
 * and unwinding it. Everything here is wording and parsing; the editor asks the questions and
 * the command line (`VibeyCli`) does the work, so this is the same for the chat, the panel and
 * any future surface (one command core, many skins). Declared by
 * `interfaces/project-driver-interface.ts`.
 */
import type { AbandonConfirmation, GateReply, NewProjectRequest, ProjectDriverInterface } from './interfaces/project-driver-interface';
import type { GateAnswerPlannerInterface, VibeyAbandonReport, VibeyGate, VibeyNewProject } from './interfaces/vibey-cli-interface';

export class ProjectDriver implements ProjectDriverInterface {
  /** What `vibey new` accepts as a name without a fight with the shell: no leading dash, no spaces. */
  private static readonly NAME = /^[A-Za-z0-9_.#:][A-Za-z0-9_.#:/-]*$/;

  constructor(private readonly planner: GateAnswerPlannerInterface) {}

  parseNew(args: string, folderName: string): NewProjectRequest | undefined {
    const trimmed = args.trim();
    const fallback = ProjectDriver.slug(folderName);
    if (trimmed === '') {
      return fallback === '' ? undefined : { name: fallback, intake: '' };
    }
    const space = trimmed.search(/\s/);
    const name = space === -1 ? trimmed : trimmed.slice(0, space);
    return ProjectDriver.NAME.test(name) ? { name, intake: space === -1 ? '' : trimmed.slice(space).trim() } : undefined;
  }

  /** A folder's name as a project name: runs of anything the shell would object to become one dash. */
  private static slug(folderName: string): string {
    const slug = folderName.replace(/[^A-Za-z0-9_.#:/-]+/g, '-').replace(/^[-/]+|[-/]+$/g, '');
    return ProjectDriver.NAME.test(slug) ? slug : '';
  }

  newProjectRefusal(message: string): string | undefined {
    if (!/is held by live project/i.test(message)) {
      return undefined;
    }
    return 'This folder already has a live project, and a folder holds only one. /resume carries on with it, or /unwind ends it so you can start another.';
  }

  describeStarted(created: VibeyNewProject, workerLine: string): readonly string[] {
    return [
      `Started "${created.name}" (${created.project_id}). ${created.outcome}`.trim(),
      workerLine === '' ? 'Its worker is running.' : workerLine,
      'It will ask you what it needs to know. Questions appear here and under Gates; /next shows the oldest, and /reply answers it.',
      'You can /pause it at any time and /resume it later; /unwind ends it for good, after showing you what would be cancelled.',
    ];
  }

  abandonConfirmation(report: VibeyAbandonReport): AbandonConfirmation {
    if (report.already_abandoned) {
      return { title: `"${report.name}" is already abandoned.`, detail: 'Nothing was changed.', nothingToDo: true };
    }
    const jobs = ProjectDriver.count(report.cancelled_jobs, 'queued or running job');
    const gates = ProjectDriver.count(report.withdrawn_gates, 'waiting question');
    return {
      title: `Unwind "${report.name}"?`,
      detail: `It is in ${report.from || 'its current phase'}. Unwinding cancels ${jobs} and withdraws ${gates}, then records why on its ledger. This cannot be undone; the work already on disk is left as it is.`,
      nothingToDo: false,
    };
  }

  oldestGate(gates: readonly VibeyGate[], projectId?: string): VibeyGate | undefined {
    return gates.find((gate) => projectId === undefined || gate.project_id === projectId);
  }

  describeGate(gate: VibeyGate): string {
    const choices = this.planner.choices(gate);
    const lines = [`${gate.project_name ?? gate.project_id} is waiting on you (${gate.kind}):`, '', gate.prompt.trim(), ''];
    choices.forEach((choice, index) => {
      const marked = gate.default_answer !== null && choice.answer !== undefined && 'value' in choice.answer && choice.answer.value === gate.default_answer;
      lines.push(`${index + 1}. ${choice.label}${marked ? ' (the default)' : ''}${choice.description === undefined || marked ? '' : ` — ${choice.description}`}`);
    });
    lines.push('', `Reply with /reply 1 to /reply ${choices.length}, or say the answer in words.`);
    return lines.join('\n');
  }

  reply(gate: VibeyGate, text: string): GateReply {
    const said = text.trim();
    const choices = this.planner.choices(gate);
    if (said === '') {
      return { kind: 'invalid', message: 'Say which answer: /reply 1, or the answer in words.' };
    }
    if (/^\d+$/.test(said)) {
      const choice = choices[Number(said) - 1];
      if (choice === undefined) {
        return { kind: 'invalid', message: `There is no answer ${said}; the list runs from 1 to ${choices.length}.` };
      }
      if (choice.answer !== undefined) {
        return { kind: 'answer', answer: choice.answer, summary: choice.label };
      }
      return choice.needs === 'pairs'
        ? { kind: 'more', needs: 'pairs', message: 'Reply with QUESTION_ID=ANSWER pairs, for example: /reply q1=yes q2=no. Any you leave out take their defaults.' }
        : { kind: 'more', needs: 'raw', message: 'Reply with a JSON object, for example: /reply {"max_dollars": 25}.' };
    }
    const mode = this.planner.mode(gate);
    if (mode === 'verdict' || mode === 'choice') {
      const match = choices.find((choice) => choice.answer !== undefined && 'value' in choice.answer && choice.answer.value.toLowerCase() === said.toLowerCase());
      return match?.answer === undefined
        ? { kind: 'invalid', message: `"${said}" is not one of the answers: ${choices.filter((choice) => choice.answer !== undefined).map((choice) => choice.label).join(', ')}.` }
        : { kind: 'answer', answer: match.answer, summary: match.label };
    }
    if (mode === 'interview') {
      if (/^(defaults?|accept(\s+all)?)$/i.test(said)) {
        return { kind: 'answer', answer: { mode: 'defaults' }, summary: 'Accept every default' };
      }
      const pairs = this.planner.parsePairs(said);
      return typeof pairs === 'string'
        ? { kind: 'invalid', message: pairs }
        : { kind: 'answer', answer: { mode: 'pairs', pairs, defaults: true }, summary: `Answered ${Object.keys(pairs).join(', ')}; the rest take their defaults` };
    }
    if (said.startsWith('{')) {
      const problem = this.planner.checkRaw(said);
      return problem === undefined ? { kind: 'answer', answer: { mode: 'raw', json: said }, summary: 'Answered with JSON' } : { kind: 'invalid', message: problem };
    }
    return { kind: 'invalid', message: 'This question takes a JSON object, for example: /reply {"max_dollars": 25}.' };
  }

  private static count(n: number, noun: string): string {
    return `${n} ${noun}${n === 1 ? '' : 's'}`;
  }
}
