// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Command lines for any loop engine, expanded from the templates `vibey loops --json`
 * carries, the same shapes vibey's own argv.py builds. Nothing here knows an engine by name:
 * a placeholder this code does not know is refused rather than guessed at. Declared by
 * `interfaces/engine-command-interface.ts`.
 */
import type { CatalogueEngine } from './interfaces/catalogue-interface';
import type { EngineCommandInterface, RunArguments } from './interfaces/engine-command-interface';
import type { Invocation } from './interfaces/qwenloop-interface';

export class EngineCommand implements EngineCommandInterface {
  constructor(
    private readonly engine: CatalogueEngine,
    private readonly executable: string,
  ) {}

  run(args: RunArguments): Invocation {
    const template = [...this.engine.run];
    if (!this.engine.supports_cwd_flag) {
      const at = template.indexOf('--cwd');
      if (at >= 0) {
        template.splice(at, 2);
      }
    }
    const [first, ...rest] = template;
    if (first !== '{binary}') {
      throw new Error(`${this.engine.engine_id}'s run template must start with {binary}, not ${String(first)}`);
    }
    const expanded: string[] = [];
    for (const token of rest) {
      switch (token) {
        case '{plan_flag?}':
          if (this.engine.plan_flag !== null) {
            expanded.push(this.engine.plan_flag);
          }
          break;
        case '{effort_argv...}':
          expanded.push(...args.effortArgv);
          break;
        default:
          expanded.push(this.fill(token, { plan: args.plan, run_id: args.runId, cwd: args.cwd }));
      }
    }
    return { command: this.executable, args: expanded };
  }

  stop(runId: string, cwd: string): Invocation | undefined {
    const template = this.engine.controls.stop;
    return template === null
      ? undefined
      : { command: this.executable, args: template.map((token) => this.fill(token, { run_id: runId, cwd })) };
  }

  /**
   * The follow-up text goes after `--`, with the template's `--option value` pairs moved in
   * front of it, so a message that starts with a dash is read as text, never as an option.
   */
  prompt(runId: string, text: string, cwd: string): Invocation | undefined {
    const template = this.engine.controls.prompt;
    if (template === null) {
      return undefined;
    }
    const [verb, ...rest] = template;
    const options: string[] = [];
    const positionals: string[] = [];
    for (let index = 0; index < rest.length; index += 1) {
      const token = rest[index] as string;
      if (token.startsWith('--') && index + 1 < rest.length) {
        options.push(token, rest[index + 1] as string);
        index += 1;
      } else {
        positionals.push(token);
      }
    }
    const values = { run_id: runId, cwd, text };
    return {
      command: this.executable,
      args: [
        this.fill(verb as string, values),
        ...options.map((token) => this.fill(token, values)),
        '--',
        ...positionals.map((token) => this.fill(token, values)),
      ],
    };
  }

  eventsPath(cwd: string, runId: string): string {
    return this.fill(this.engine.events.path, { cwd, state_dir: this.engine.state_dir, run_id: runId });
  }

  version(): Invocation {
    return { command: this.executable, args: ['--version'] };
  }

  /** Every `{name}` in `token` from `values`; an unknown name is an error, never a guess. */
  private fill(token: string, values: Readonly<Record<string, string>>): string {
    return token.replace(/\{([a-z_]+)\}/g, (_match, name: string) => {
      const value = values[name];
      if (value === undefined) {
        throw new Error(`${this.engine.engine_id}: the template placeholder {${name}} is not one this extension fills`);
      }
      return value;
    });
  }
}
