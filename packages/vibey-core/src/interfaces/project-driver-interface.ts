// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What driving a project from a chat or a menu needs that is not the command line itself: wording, parsing, interpreting a reply. */
import type { GateAnswer, VibeyAbandonReport, VibeyGate, VibeyNewProject } from './vibey-cli-interface';

/** `/new <name> [what to build]`, understood. */
export interface NewProjectRequest {
  readonly name: string;
  readonly intake: string;
}

/** What to show before an unwind is allowed to go ahead. */
export interface AbandonConfirmation {
  readonly title: string;
  readonly detail: string;
  /** True when there is nothing to confirm: the project is already abandoned. */
  readonly nothingToDo: boolean;
}

/** What a reply to a waiting question turned out to be. */
export type GateReply =
  | { readonly kind: 'answer'; readonly answer: GateAnswer; readonly summary: string }
  | { readonly kind: 'more'; readonly needs: 'pairs' | 'raw'; readonly message: string }
  | { readonly kind: 'invalid'; readonly message: string };

export interface ProjectDriverInterface {
  /** `args` is what follows `/new`; with none, the folder's name is the project's name and nothing is yet said about what to build. */
  parseNew(args: string, folderName: string): NewProjectRequest | undefined;
  /** Plain words for the one refusal a newcomer is sure to meet (a folder holds one live project); undefined for any other error. */
  newProjectRefusal(message: string): string | undefined;
  /** The lines that tell a person what just started and what happens next. */
  describeStarted(created: VibeyNewProject, workerLine: string): readonly string[];
  /** The wording of the confirmation that comes between a dry run and the real thing. */
  abandonConfirmation(report: VibeyAbandonReport): AbandonConfirmation;
  /** The oldest open gate, optionally only one project's. */
  oldestGate(gates: readonly VibeyGate[], projectId?: string): VibeyGate | undefined;
  /** A waiting question as a conversation shows it: the prompt, then the answers, numbered. */
  describeGate(gate: VibeyGate): string;
  /** A person's reply to that question: a number picks an answer; words are matched to the answers the question takes. */
  reply(gate: VibeyGate, text: string): GateReply;
}
