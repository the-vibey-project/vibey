// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Every command the extension offers, declared once: palette, menu, slash commands and @vibey. */
import type { EffortSetting, LoopName } from './catalogue-interface';

export type CommandGroup = 'Run' | 'Loop & model' | 'Lanes' | 'Projects & gates' | 'Budgets' | 'Ollama' | 'Doctor';

export interface CommandSpec {
  /** The VS Code command id: `vibey.ask`. */
  readonly id: string;
  /** Its title in the Command Palette, under the "Vibey" category. */
  readonly title: string;
  readonly group: CommandGroup;
  /** A codicon name, shown as `$(name)`. */
  readonly icon: string;
  /** The slash command in the task panel and in @vibey: `ask` for `/ask`. */
  readonly slash?: string;
  /** What follows the slash command: `<task>`. */
  readonly usage?: string;
  /** One line in plain words. */
  readonly description: string;
  /** A worked example, as the README shows it (doctrine 3: an example for every command). */
  readonly example: string;
  /** The vibey, engine or Ollama command it wraps, when it wraps one. */
  readonly wraps?: string;
}

export type SlashParse =
  | { readonly kind: 'text'; readonly text: string }
  | { readonly kind: 'command'; readonly spec: CommandSpec; readonly args: string }
  | { readonly kind: 'unknown'; readonly name: string; readonly reply: string };

export interface SlashCommandsInterface {
  parse(input: string): SlashParse;
  /** Commands whose slash name starts with what follows the `/` typed so far. */
  complete(typed: string): readonly CommandSpec[];
  /** Every slash command, grouped, as `/help` shows them. */
  help(): string;
  /** The first word of every slash command, once each: what @vibey declares as its commands. */
  firstWords(): readonly string[];
}

export interface SlashArgumentsInterface {
  loop(args: string): LoopName | string;
  effort(args: string): EffortSetting | string;
  /** Shell-like words: quotes group, backslash escapes. */
  words(args: string): readonly string[];
}
